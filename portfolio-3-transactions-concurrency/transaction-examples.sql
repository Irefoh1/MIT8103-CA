-- Run after setup.sql and checkout.sql. These illustrative manual examples
-- are also exercised and asserted by run-lab.py in a fresh database.
-- Use psql ON_ERROR_STOP=1; do not run during the concurrent examples.

-- Successful purchase: stock reduction, order and item persist together.
BEGIN ISOLATION LEVEL READ COMMITTED;
SELECT markethub.checkout_one(1,1,2) AS committed_order_id;
COMMIT;
SELECT quantity_on_hand FROM markethub.inventory WHERE product_id=1;

-- Abandoned checkout: even a successfully executed function can be undone.
BEGIN;
SELECT markethub.checkout_one(2,2,3) AS temporary_order_id;
SELECT quantity_on_hand FROM markethub.inventory WHERE product_id=2;
ROLLBACK;
SELECT quantity_on_hand FROM markethub.inventory WHERE product_id=2;
-- Identity sequences may have gaps after rollback; that is expected.
