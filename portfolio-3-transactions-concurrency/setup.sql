-- Fresh P3 database only, AFTER the unchanged Portfolio 1 schema.
BEGIN;
INSERT INTO markethub.customers(full_name,email) VALUES
 ('Ada Okafor','ada@example.test'),('Tunde Bello','tunde@example.test');
INSERT INTO markethub.categories(category_name) VALUES ('Electronics');
INSERT INTO markethub.products(category_id,sku,product_name,current_price) VALUES
 (1,'P3-KEYBOARD','USB Keyboard',15000),(1,'P3-MOUSE','Optical Mouse',5000);
INSERT INTO markethub.inventory(product_id,quantity_on_hand,reorder_level)
SELECT product_id,10,2 FROM markethub.products;
COMMIT;
