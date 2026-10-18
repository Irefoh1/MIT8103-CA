-- Run after the supplied seed. Each rejected write is rolled back by its
-- exception block; an unexpectedly accepted write makes this script fail.
BEGIN;
SET LOCAL search_path TO markethub, public;
DO $$
BEGIN
    BEGIN
        INSERT INTO customers(full_name,email) VALUES ('Duplicate','ada@example.test');
        RAISE EXCEPTION 'FAIL: duplicate email accepted';
    EXCEPTION WHEN unique_violation THEN
        RAISE NOTICE 'PASS: duplicate email rejected';
    END;
    BEGIN
        UPDATE order_items SET quantity=0;
        RAISE EXCEPTION 'FAIL: zero item quantity accepted';
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE 'PASS: zero item quantity rejected';
    END;
    BEGIN
        UPDATE inventory SET quantity_on_hand=-1;
        RAISE EXCEPTION 'FAIL: negative stock accepted';
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE 'PASS: negative stock rejected';
    END;
    BEGIN
        INSERT INTO inventory(product_id,quantity_on_hand) VALUES (-1,1);
        RAISE EXCEPTION 'FAIL: missing product accepted';
    EXCEPTION WHEN foreign_key_violation THEN
        RAISE NOTICE 'PASS: missing product reference rejected';
    END;
    BEGIN
        INSERT INTO payment_attempts(order_id,provider_reference,amount,status)
        SELECT order_id,'DEMO-SECOND-SUCCESS',35000,'successful' FROM orders;
        RAISE EXCEPTION 'FAIL: second successful payment accepted';
    EXCEPTION WHEN unique_violation THEN
        RAISE NOTICE 'PASS: second successful payment rejected';
    END;
END $$;
ROLLBACK;
