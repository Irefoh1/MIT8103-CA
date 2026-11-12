-- Latest ten orders for one customer, including calculated order totals.
SELECT o.order_id,o.ordered_at,o.status,
       (SELECT SUM(i.quantity*i.unit_price)
        FROM markethub.order_items i WHERE i.order_id=o.order_id) AS total_ngn
FROM markethub.orders o
WHERE o.customer_id=42
ORDER BY o.ordered_at DESC,o.order_id DESC
LIMIT 10;
