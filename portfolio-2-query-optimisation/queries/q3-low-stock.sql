SELECT p.sku,p.product_name,i.quantity_on_hand,i.reorder_level
FROM markethub.inventory i JOIN markethub.products p USING(product_id)
WHERE i.quantity_on_hand<i.reorder_level
ORDER BY i.product_id;
