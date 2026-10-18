-- Synthetic educational data. Run after schema.sql in a fresh database.
BEGIN;
SET LOCAL search_path TO markethub, public;
INSERT INTO customers (full_name,email) VALUES
    ('Ada Okafor','ada@example.test'), ('Tunde Bello','tunde@example.test');
INSERT INTO customer_addresses
    (customer_id,recipient_name,address_line,city,state)
SELECT customer_id,full_name,'10 Example Street','Ikeja','Lagos'
FROM customers WHERE email = 'ada@example.test';

INSERT INTO categories (category_name) VALUES ('Electronics'),('Office Supplies');
INSERT INTO products (category_id,sku,product_name,current_price)
SELECT category_id,'KB-001','USB Keyboard',15000 FROM categories WHERE category_name='Electronics';
INSERT INTO products (category_id,sku,product_name,current_price)
SELECT category_id,'MS-001','Optical Mouse',5000 FROM categories WHERE category_name='Electronics';
INSERT INTO products (category_id,sku,product_name,current_price)
SELECT category_id,'NB-001','Notebook',2000 FROM categories WHERE category_name='Office Supplies';
INSERT INTO inventory (product_id,quantity_on_hand,reorder_level)
SELECT product_id,CASE sku WHEN 'KB-001' THEN 20 WHEN 'MS-001' THEN 50 ELSE 100 END,5 FROM products;

INSERT INTO orders (customer_id,delivery_recipient,delivery_address_line,delivery_city,delivery_state)
SELECT customer_id,recipient_name,address_line,city,state FROM customer_addresses;
INSERT INTO order_items (order_id,product_id,quantity,unit_price)
SELECT o.order_id,p.product_id,CASE p.sku WHEN 'KB-001' THEN 2 ELSE 1 END,p.current_price
FROM orders o CROSS JOIN products p WHERE p.sku IN ('KB-001','MS-001');
UPDATE inventory i SET quantity_on_hand = i.quantity_on_hand - oi.quantity
FROM order_items oi WHERE i.product_id=oi.product_id;
UPDATE orders SET status='placed';
INSERT INTO payment_attempts (order_id,provider_reference,amount,status)
SELECT order_id,'DEMO-FAILED-001',35000,'failed' FROM orders;
INSERT INTO payment_attempts (order_id,provider_reference,amount,status)
SELECT order_id,'DEMO-SUCCESS-001',35000,'successful' FROM orders;
UPDATE orders SET status='paid';
INSERT INTO shipments (order_id,carrier,tracking_number,status,shipped_at)
SELECT order_id,'Demo Courier','DEMO-TRACK-001','in_transit',CURRENT_TIMESTAMP FROM orders;
UPDATE orders SET status='shipped';
COMMIT;

-- Expected: one order, Ada Okafor, shipped, 35000.00.
SELECT o.order_id,c.full_name,o.status,SUM(oi.quantity*oi.unit_price) AS order_total_ngn
FROM markethub.orders o
JOIN markethub.customers c USING (customer_id)
JOIN markethub.order_items oi USING (order_id)
GROUP BY o.order_id,c.full_name,o.status;

-- Expected: KB-001=18, MS-001=49, NB-001=100.
SELECT p.sku,i.quantity_on_hand FROM markethub.products p
JOIN markethub.inventory i USING (product_id) ORDER BY p.sku;

-- Expected: failed=1, successful=1.
SELECT status,COUNT(*) FROM markethub.payment_attempts GROUP BY status ORDER BY status;
