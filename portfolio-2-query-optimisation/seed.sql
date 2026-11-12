-- Run only after the P1 schema in a NEW EMPTY practice database.
-- Stable synthetic benchmark data; this is not a checkout simulation.
BEGIN;
SET LOCAL search_path TO markethub, public;
INSERT INTO customers(full_name,email)
SELECT 'Customer '||g,'customer'||g||'@example.test' FROM generate_series(1,5000) g;
INSERT INTO categories(category_name)
SELECT 'Category '||g FROM generate_series(1,10) g;
INSERT INTO products(category_id,sku,product_name,current_price)
SELECT 1+(g%10),'SKU-'||lpad(g::text,5,'0'),'Product '||g,100+(g%200)*50
FROM generate_series(1,1000) g;
INSERT INTO inventory(product_id,quantity_on_hand,reorder_level)
SELECT product_id,CASE WHEN product_id%100=0 THEN 2 ELSE 1000 END,5 FROM products;
INSERT INTO orders(customer_id,ordered_at,status,delivery_recipient,
                   delivery_address_line,delivery_city,delivery_state)
SELECT 1+((g*37)%5000),
       timestamptz '2026-01-01 00:00:00+00'+((g*7919)%25920000)*interval '1 second',
       CASE WHEN g%10=0 THEN 'cancelled' WHEN g%3=0 THEN 'placed' ELSE 'paid' END,
       'Customer '||(1+((g*37)%5000)),'1 Synthetic Street','Ikeja','Lagos'
FROM generate_series(1,100000) g;
INSERT INTO order_items(order_id,product_id,quantity,unit_price)
SELECT o.order_id,p.product_id,1+(o.order_id%3)::integer,p.current_price
FROM orders o CROSS JOIN generate_series(0,2) n
JOIN products p ON p.product_id=1+((o.order_id*13+n*17)%1000);
INSERT INTO payment_attempts(order_id,provider_reference,amount,status,attempted_at)
SELECT o.order_id,'BENCH-'||o.order_id,SUM(i.quantity*i.unit_price),'successful',o.ordered_at
FROM orders o JOIN order_items i USING(order_id)
WHERE o.status='paid' GROUP BY o.order_id;
COMMIT;
-- Refresh planner statistics and visibility maps equally for both phases.
VACUUM (ANALYZE) markethub.customers;
VACUUM (ANALYZE) markethub.products;
VACUUM (ANALYZE) markethub.inventory;
VACUUM (ANALYZE) markethub.orders;
VACUUM (ANALYZE) markethub.order_items;
VACUUM (ANALYZE) markethub.payment_attempts;
