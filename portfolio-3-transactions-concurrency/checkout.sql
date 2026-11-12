-- Single-product checkout for the P3 lab, using P1's existing tables.
-- Run the caller in a transaction. This function does not commit for it.
CREATE FUNCTION markethub.checkout_one(
    p_customer_id bigint, p_product_id bigint, p_quantity integer
) RETURNS bigint LANGUAGE plpgsql AS $$
DECLARE
    v_price numeric(12,2);
    v_order_id bigint;
    v_name varchar(150);
BEGIN
    IF p_quantity IS NULL OR p_quantity <= 0 THEN
        RAISE EXCEPTION 'Quantity must be positive' USING ERRCODE='22023';
    END IF;
    SELECT full_name INTO STRICT v_name
      FROM markethub.customers WHERE customer_id=p_customer_id;
    -- Prevent a concurrent product update from changing the price/active flag
    -- between checking the product and inserting the purchase price.
    SELECT current_price INTO v_price FROM markethub.products
      WHERE product_id=p_product_id AND is_active FOR SHARE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Product unavailable' USING ERRCODE='P0002';
    END IF;
    -- Under READ COMMITTED, a competing updater waits for the row lock and
    -- rechecks this predicate against the committed version before updating.
    UPDATE markethub.inventory
       SET quantity_on_hand=quantity_on_hand-p_quantity
     WHERE product_id=p_product_id AND quantity_on_hand>=p_quantity;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Insufficient stock' USING ERRCODE='P0001';
    END IF;
    INSERT INTO markethub.orders(customer_id,status,delivery_recipient,
        delivery_address_line,delivery_city,delivery_state)
    VALUES(p_customer_id,'draft',v_name,'1 Synthetic Street','Ikeja','Lagos')
    RETURNING order_id INTO v_order_id;
    INSERT INTO markethub.order_items(order_id,product_id,quantity,unit_price)
    VALUES(v_order_id,p_product_id,p_quantity,v_price);
    UPDATE markethub.orders SET status='placed' WHERE order_id=v_order_id;
    RETURN v_order_id;
END $$;
