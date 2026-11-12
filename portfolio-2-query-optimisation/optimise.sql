BEGIN;
-- Filter on customer, then read directly in requested deterministic order.
CREATE INDEX p2_orders_customer_recent_idx
ON markethub.orders(customer_id,ordered_at DESC,order_id DESC) INCLUDE(status);
-- Only paid rows, ordered by date. Include customer for an index-only scan
-- when the visibility map allows it. The literal predicate matches Q2.
CREATE INDEX p2_paid_orders_date_idx
ON markethub.orders(ordered_at,order_id) INCLUDE(customer_id) WHERE status='paid';
-- Small partial index containing only products needing replenishment.
CREATE INDEX p2_inventory_low_stock_idx
ON markethub.inventory(product_id) INCLUDE(quantity_on_hand,reorder_level)
WHERE quantity_on_hand<reorder_level;
COMMIT;
ANALYZE markethub.orders;
ANALYZE markethub.inventory;
