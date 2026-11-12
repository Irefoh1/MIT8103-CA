SELECT COALESCE(json_agg(p ORDER BY p.sku),'[]'::json) FROM
 (SELECT p.product_id::text,p.sku,p.product_name AS name,p.description,
 p.current_price::text AS price,p.is_active AS active,c.category_id::text,c.category_name
 FROM markethub.products p JOIN markethub.categories c USING(category_id)
 WHERE p.sku IN ('KB-001','MS-001','NB-001')) p;
