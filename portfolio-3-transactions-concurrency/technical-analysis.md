# MarketHub transaction and concurrency analysis

## Verified environment and scope

The successful run was executed on 12 November 2026 (Africa/Lagos), using PostgreSQL 18.3 in Docker and the new database `markethub_p3_verified`. See [environment](evidence/environment.txt) and the [17-check summary](evidence/verification.txt). The first development run used `markethub_p3`; the fully verified run used the separate database above. P1 and P2 databases were not changed. Raw UTC time is recorded in the environment file.

The checkout function implements a **single product per purchase** for this lab. The underlying P1 design still supports multi-item orders. The address is a synthetic fixed lab destination, and no external payment gateway is invoked. Payment success, refunds, shipping, order cancellation/restocking, and a complete production checkout service are outside this exercise.

## 1. Commit and rollback

A transaction groups changes into one unit. In the successful example, the buyer reduces keyboard stock from ten to eight, creates an order, inserts its item, and marks it placed. COMMIT makes all changes visible to a separate database connection. The saved purchase price is NGN 15,000 and quantity is two.

In the explicit rollback example, a second purchase temporarily reduces mouse stock from ten to seven and adds an order. The buyer sees its own changes, but an observer still sees stock ten and only the previous committed order. ROLLBACK removes that temporary order and item and restores the stock balance.

The error example first executes a valid mouse checkout, then deliberately attempts negative stock. PostgreSQL reports SQLSTATE `23514` (CHECK violation). psql is configured to stop on error and exits with an open failed transaction, so disconnect rolls the entire transaction back. Observer queries confirm no extra order and stock ten. This is a genuine SQL error, not an illustrative invented output. Applications keeping their connection open should explicitly issue ROLLBACK; an error does not mean it is safe to continue issuing ordinary statements in the failed transaction.

Identity sequence values are not rolled back with the rows. Gaps in order IDs after these tests are expected and do not mean an order was retained.

Evidence: [commit and explicit rollback session](evidence/p3-commit.txt), [SQL error](evidence/error-rollback.txt), and [observer checks](evidence/p3-observer.txt).

## 2. Isolation and visibility

| Schedule | Read Committed | Repeatable Read |
|---|---|---|
| Reader starts and reads stock | 10 | 10 |
| Writer commits stock change | 9 committed | 9 committed |
| Reader repeats ordinary SELECT inside its transaction | 9 | 10 |
| Reader ends transaction; fresh SELECT | 9 | 9 |

Read Committed takes a new snapshot for each statement. Seeing different committed values in repeated reads is allowed: this is a nonrepeatable read. Neither read observes the writer's uncommitted intermediate changes.

PostgreSQL Repeatable Read uses a stable transaction snapshot established by its first snapshot-taking statement. The writer can still update and commit; the reader's ordinary SELECT does not prevent it. Repeatable Read therefore changes what the reader sees, rather than locking inventory against every writer. It is not a general replacement for business-level checkout concurrency controls. If a Repeatable Read transaction tries to update a row changed since its snapshot, it can receive a serialization failure; that update case is discussed here but not exercised in this lab.

Evidence: [reader](evidence/p3-isolation-reader.txt) and [writer](evidence/p3-isolation-writer.txt).

## 3. Unsafe checkout: a lost stock update and overselling

The deliberately broken implementation separates reading stock, calculating the new value, and writing that value:

```text
Session A: reads stock = 1 and calculates new stock = 0
Session B: reads stock = 1 and calculates new stock = 0
Session A: writes 0, creates one-unit order, commits
Session B: writes its stale 0, creates another one-unit order, commits
Result: stock 0, two orders, two units sold from one initial unit
```

The transactions overlap: both read before either writes. The runner then schedules their writes explicitly. Session B overwrites the stock balance using its old calculation instead of decrementing the current balance; the second decrement is lost. PostgreSQL serialises the actual writes, but this does not fix the stale application calculation under Read Committed.

The `quantity_on_hand >= 0` CHECK passes because both write zero. A row constraint can reject negative values but cannot prove that the number of sold units agrees with available stock. Both transactions can be individually committed and still violate the business requirement.

Evidence: [unsafe buyer A](evidence/p3-unsafe-a.txt), [unsafe buyer B](evidence/p3-unsafe-b.txt), and final counts in the observer log.

## 4. Protected checkout: conditional decrement and row locking

The function uses this operation instead of a stale absolute assignment:

```sql
UPDATE markethub.inventory
SET quantity_on_hand = quantity_on_hand - p_quantity
WHERE product_id = p_product_id
  AND quantity_on_hand >= p_quantity;
```

The condition and decrement are part of the same SQL statement. The first buyer updates the inventory row and holds its row lock until the transaction ends. The second buyer attempts the same update and waits. The observer verifies `p3-safe-b|Lock|p3-safe-a` using PostgreSQL activity and blocking-PID information, rather than merely assuming blocking occurred.

After the first buyer commits, PostgreSQL under **Read Committed** rechecks the waiting update's predicate against the updated row. Stock is zero, so the update affects no row. The function checks `FOUND` and raises `P0001` for insufficient stock before creating an order. In the automated example, a PL/pgSQL exception block catches only that expected code and reports rejection; any unexpected success deliberately fails the test. The manual guide instead lets the error surface and requires an explicit ROLLBACK.

Final state: zero stock, exactly one order, and one sold unit. A separate test also confirms that zero quantity is rejected with `22023`.

The product row is read `FOR SHARE` to protect its checked active flag and price against concurrent product updates while recording the sale. The function uses an atomic conditional UPDATE as its **inventory** concurrency mechanism; it does not claim to use a separate inventory `SELECT FOR UPDATE`. All cooperating stock-changing workflows must follow an appropriate safe protocol. Direct arbitrary writes by privileged users can still break business invariants.

Evidence: [protected buyer A](evidence/p3-safe-a.txt), [protected buyer B](evidence/p3-safe-b.txt), and the observer's recorded blocker query.

## 5. ACID in this example

| Property | Connection to the lab |
|---|---|
| Atomicity | Stock, order, and item persist together or roll back together. Both explicit rollback and rollback after error are observed. |
| Consistency | Keys and CHECK constraints remain enforced; the checkout adds stock sufficiency and quantity checks. The unsafe example shows that declared constraints alone do not encode every business rule. |
| Isolation | Sessions do not see uncommitted writes; snapshots determine read visibility; row locks coordinate competing stock updates. |
| Durability | Committed changes are observed from another connection. PostgreSQL provides durability under its configured storage/WAL guarantees, but this lab does not perform a restart, power-loss, or disaster-recovery test. |

## 6. Practical limits and future work

- These are deterministic small-scale demonstrations, not a throughput benchmark, stress test, or proof of every possible interleaving.
- The protected race is tested at Read Committed. Higher isolation levels can report serialization failures; applications must roll back and retry the **whole transaction** when appropriate, using bounded retries. No retry implementation is claimed here.
- For multi-item checkout, acquire inventory locks in a consistent product-ID order and keep the whole basket in one transaction. Inconsistent lock ordering can cause deadlocks. A deadlock/retry example is not implemented here.
- A real service needs authentication, authorisation, genuine address validation, request idempotency, and coordinated payment handling. Do not hold inventory transactions open while waiting for a payment network call.
- The function models placement and stock deduction only. It does not make previously placed orders immutable or prevent privileged direct changes to order contents.
- Session timeouts prevent indefinite waits in the lab. The runner uses SQLSTATE checks, connection separation, explicit read/write scheduling, observed lock waits, and final-state assertions rather than timing-only sleeps.

## Individual reflection prompts

Write your own answers after reviewing the logs: What did the unsafe case teach you about constraints? Why did the waiting buyer need a stock predicate? Why did Repeatable Read show ten after the writer committed nine? How would you extend this checkout to two products without introducing inconsistent lock order?
