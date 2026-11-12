# Portfolio 3: Transactions and Concurrency

## Case study and objective

MarketHub is the same simulated e-commerce retailer used in Portfolios 1 and 2. Checkout must create an order and its items while reducing stock. Either all these changes succeed together, or none should remain. Two buyers must not both purchase the final unit.

This activity demonstrates commit, rollback, isolation, an unsafe lost-update/overselling scenario, and a tested concurrency control mechanism. It reuses the unchanged P1 schema in a separate lab database; it does not change the earlier portfolio databases.

## Files

| File | Purpose |
|---|---|
| [setup.sql](setup.sql) | Two fictional customers, two products, initial stock |
| [checkout.sql](checkout.sql) | Single-product checkout function using a conditional stock update |
| [transaction-examples.sql](transaction-examples.sql) | Simple manual COMMIT and ROLLBACK examples |
| [run-lab.py](run-lab.py) | Reproducible lab with real concurrent PostgreSQL connections and assertions |
| [manual-concurrency-guide.md](manual-concurrency-guide.md) | Two-terminal steps for understanding and reproducing the examples |
| [technical-analysis.md](technical-analysis.md) | Explanation, results, ACID properties, and limitations |
| [evidence/](evidence/) | Actual session SQL/output, database environment, error log, and check summary |

## Reproduce the verified lab

Requirements: Python 3, Docker CLI, a running PostgreSQL container, and permission to access Docker. No third-party Python packages are needed. From the repository root:

```powershell
python portfolio-3-transactions-concurrency/run-lab.py
```

Defaults: container `markethub-p1-validation`, new database `markethub_p3`. The runner creates the database, loads the P1 schema, then runs setup and the checkout function. It deliberately fails if the database already exists. It does not drop previous databases or overwrite P1/P2 data.

For a repeat, choose a new name:

```powershell
python portfolio-3-transactions-concurrency/run-lab.py --database markethub_p3_repeat
```

Use `--container NAME` for another PostgreSQL container. A repeated run replaces files in this activity's `evidence/` directory; preserve previous evidence if needed. Session logs include the SQL, outputs, and expected errors/notices. Test-case reset statements delete only the newly created P3 database's lab orders and restore its stock, keeping scenarios independent. Do not copy those resets into a live store database.

## What each demonstration establishes

1. **Commit:** Buy two keyboards. Another connection observes stock fall from ten to eight, one order, and an item with quantity two and purchase price NGN 15,000.
2. **Explicit rollback:** Start buying three mice. The buyer sees stock seven and a new order; another session still sees stock ten and no additional order. ROLLBACK removes the purchase and restores stock ten.
3. **Rollback after error:** Create the same temporary checkout, then attempt negative stock. PostgreSQL reports CHECK violation SQLSTATE `23514`. The script exits on error; closing that connection aborts its open transaction, leaving no purchase or stock change. A continuing application should explicitly roll back its failed transaction before reusing a connection.
4. **Read Committed:** Read stock ten; another session commits stock nine; rereading in the first transaction returns nine. Each statement uses a new snapshot, allowing a nonrepeatable read.
5. **Repeatable Read:** The same schedule returns ten twice inside the reader transaction, then nine after it commits and starts a new statement/transaction.
6. **Unsafe concurrent checkout:** Both transactions first read stock one. Each later writes the stale absolute value zero and creates an order. Both purchases commit: two units sold from one initial unit, stock zero. The nonnegative-stock constraint does not catch this business error.
7. **Protected concurrent checkout:** The first buyer's conditional decrement holds the inventory row lock. PostgreSQL confirms the second buyer is blocked by that transaction. When the first commits, the second rechecks the stock predicate, fails with insufficient stock, and creates no order. Final state: one order, one unit sold, stock zero.

The runner coordinates transaction boundaries explicitly rather than relying on arbitrary delays to create a race. It observes the actual blocker through `pg_blocking_pids`, enforces timeouts, and verifies final database state. The checkout quantity guard is also tested.

## Review before submission

Read [technical-analysis.md](technical-analysis.md), inspect the session logs, and reproduce the two-terminal guide if useful. Explain why a negative-stock CHECK is insufficient and why a conditional decrement works under Read Committed. Add your own reflection about decisions, challenges, and lessons; screenshots can supplement the text evidence. Commit the P3 directory and updated root README to your private repository when reviewed. Nothing is committed or pushed by the lab runner.

## Sources and AI-use declaration

Course source: MIT 8103 assignment brief, Portfolio 3: transaction examples showing commit, rollback, isolation, a concurrency issue or control mechanism, and screenshots/output evidence.

OpenAI Codex assisted with the initial SQL, lab runner, documentation, and execution. Student review, corrections, personal verification, and reflection must be documented honestly before submission. The supplied technical analysis is not a fabricated personal reflection.
