-- Broad aggregation: a selective index need not improve this workload.
SELECT p.product_id,p.product_name,SUM(i.quantity) AS units_sold,
       SUM(i.quantity*i.unit_price) AS revenue_ngn
FROM markethub.orders o
JOIN markethub.order_items i USING(order_id)
JOIN markethub.products p USING(product_id)
WHERE o.status='paid'
GROUP BY p.product_id,p.product_name
ORDER BY revenue_ngn DESC,p.product_id
LIMIT 10;
