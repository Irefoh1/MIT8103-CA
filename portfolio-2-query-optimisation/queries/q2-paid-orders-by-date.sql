-- Half-open UTC range avoids wrapping the indexed timestamp in a function.
SELECT order_id,customer_id,ordered_at
FROM markethub.orders
WHERE status='paid'
  AND ordered_at >= timestamptz '2026-07-15 00:00:00+00'
  AND ordered_at < timestamptz '2026-07-16 00:00:00+00'
ORDER BY ordered_at,order_id;
