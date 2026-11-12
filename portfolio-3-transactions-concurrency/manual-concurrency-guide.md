# Two-session walkthrough

Use the automated runner first to create the database and checkout function. For this manual exercise, use a repeat-run practice database if you want to preserve the final state of the recorded run. Substitute that database name below. Never use a production database.

Open two terminals, connecting each to the **same** lab database:

```powershell
docker exec -it markethub-p1-validation psql -X -U postgres -d markethub_p3
```

Run each section in order. The reset is lab-only and requires that neither terminal has an open transaction. Session 1 runs:

```sql
BEGIN;
DELETE FROM markethub.order_items;
DELETE FROM markethub.orders;
UPDATE markethub.inventory SET quantity_on_hand=1;
COMMIT;
```

## Unsafe: read, calculate in application, write stale value

In **both** sessions, run this before either proceeds:

```sql
BEGIN ISOLATION LEVEL READ COMMITTED;
SELECT quantity_on_hand FROM markethub.inventory WHERE product_id=1;
-- Both return 1. Each buyer calculates 1 - 1 = 0 outside the database.
```

Session 1:

```sql
UPDATE markethub.inventory SET quantity_on_hand=0 WHERE product_id=1;
WITH o AS (
  INSERT INTO markethub.orders(customer_id,status,delivery_recipient,
    delivery_address_line,delivery_city,delivery_state)
  VALUES(1,'placed','Ada','1 Synthetic Street','Ikeja','Lagos')
  RETURNING order_id
)
INSERT INTO markethub.order_items(order_id,product_id,quantity,unit_price)
SELECT order_id,1,1,15000 FROM o;
COMMIT;
```

Session 2 now runs the same block, changing customer ID `1` to `2` and recipient `Ada` to `Tunde`. Its stock write is also the literal `0`, calculated from its earlier stale read. Both transactions succeed. Check:

```sql
SELECT quantity_on_hand FROM markethub.inventory WHERE product_id=1;
SELECT count(*) AS orders FROM markethub.orders;
SELECT sum(quantity) AS units_sold FROM markethub.order_items;
-- 0 stock, 2 orders, 2 sold units despite only 1 initial unit.
```

## Protected: check and decrement atomically

After the previous transactions finish, run the reset block again. Session 1:

```sql
BEGIN ISOLATION LEVEL READ COMMITTED;
SELECT markethub.checkout_one(1,1,1);
-- Leave transaction open: do not COMMIT yet.
```

Session 2:

```sql
BEGIN ISOLATION LEVEL READ COMMITTED;
SET LOCAL lock_timeout='30s';
SELECT markethub.checkout_one(2,1,1);
-- This waits. Return to session 1 promptly.
```

Session 1 runs `COMMIT;`. Session 2 then reports `Insufficient stock`; run `ROLLBACK;` in session 2 to clear its failed transaction. Check the same three queries: stock zero, one order, one unit sold.

The automated runner additionally proves the blocking relationship with an observer session. If a timeout happens before you commit session 1 manually, roll back session 2 and reset/retry; that is a timeout outcome, not the intended insufficient-stock result.

## Isolation: when does the reader see changes?

With both previous transactions finished, set product 1 stock to ten. Session 1:

```sql
BEGIN ISOLATION LEVEL READ COMMITTED;
SELECT quantity_on_hand FROM markethub.inventory WHERE product_id=1;
-- 10
```

Session 2:

```sql
BEGIN;
UPDATE markethub.inventory SET quantity_on_hand=9 WHERE product_id=1;
COMMIT;
```

Session 1 repeats the SELECT: it returns nine. Run `COMMIT;`.

Set stock to ten again outside any open transaction. Repeat the same steps using `BEGIN ISOLATION LEVEL REPEATABLE READ;` in session 1. Its second SELECT returns ten. After COMMIT, a fresh SELECT returns nine. These are ordinary reads; they do not lock the stock row against updates.
