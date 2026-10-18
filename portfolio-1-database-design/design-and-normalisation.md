# Relational schema and normalisation

## Relations and keys

PK = primary key, FK = foreign key, AK = alternate candidate key. All FKs are mandatory. All attributes are mandatory except customer phone, address postal codes, product description, and shipment timestamps.

| Relation | Primary key | Foreign keys | Alternate keys |
|---|---|---|---|
| customers | customer_id | — | email |
| customer_addresses | address_id | customer_id → customers | — |
| categories | category_id | — | category_name |
| products | product_id | category_id → categories | sku |
| inventory | product_id | product_id → products | — |
| orders | order_id | customer_id → customers | — |
| order_items | (order_id, product_id) | order_id → orders; product_id → products | — |
| payment_attempts | payment_id | order_id → orders | provider_reference |
| shipments | shipment_id | order_id → orders | (carrier, tracking_number) |

The complete attributes and data types are in `schema.sql` and the ER diagram. Email is stored trimmed and lowercase so the ordinary unique constraint also prevents duplicates differing only by case. Provider references are assumed unique across the single payment integration in this version.

## Normalisation progression

Start with an illustrative unnormalised order record containing customer details, delivery details, a repeating list of products and quantities, a category name for each product, and lists of payment attempts and shipments. Repeating lists make updating and querying individual facts difficult.

**First normal form (1NF):** Store one value per attribute and separate repeated items, payments, and shipments into individual rows. Address line is treated as a single delivery component; city, state, postal code, and country are separate. No comma-separated product IDs or numbered product columns are used.

**Second normal form (2NF):** The order-item relation has composite key `(order_id, product_id)`. Quantity and purchase unit price depend on the complete pair. Customer and order date depend only on order_id and belong in orders. Product name, SKU, category, and current catalogue price depend only on product_id and belong in products. This removes partial dependencies.

**Third normal form (3NF):** Separate customer contact details into customers and category names into categories. Orders store customer_id rather than duplicating the customer's email; products store category_id rather than duplicating category names. Each non-key fact depends on a candidate key without an intervening non-key determinant under the stated business assumptions.

## Principal functional dependencies

- `customer_id → full_name, email, phone, created_at`; email is also a candidate key.
- `address_id → customer_id, recipient_name, address_line, city, state, postal_code, country`.
- `category_id → category_name`; category_name is also a candidate key.
- `product_id → category_id, sku, product_name, description, current_price, is_active`; sku is also a candidate key.
- `product_id → quantity_on_hand, reorder_level` in inventory.
- `order_id → customer_id, ordered_at, status, delivery snapshot attributes`.
- `(order_id, product_id) → quantity, unit_price` in order_items.
- `payment_id → order_id, provider_reference, amount, status, attempted_at`; provider_reference is also a candidate key.
- `shipment_id → order_id, carrier, tracking_number, status, shipped_at, delivered_at`; `(carrier, tracking_number)` is also a candidate key.

No rule assumes that city determines state or that postal code determines address. Those dependencies are not valid across all supported addresses.

## Historical facts and calculated values

`order_items.unit_price` is the agreed price for a particular sale, not a duplicate of `products.current_price`. It therefore depends on the complete order-item key. A delivery snapshot represents the destination agreed for that order, not the customer's current saved address. Repeated text across different historical orders does not by itself violate normalisation.

Line totals are calculated as `quantity * unit_price`; order totals are calculated using SUM over items. Neither is stored, avoiding inconsistent totals when items change. Stock quantity is a stored current balance; a stock-movement ledger is a possible future extension.

## Constraint boundaries

SQL enforces primary-key uniqueness, mandatory values, foreign-key validity, positive quantities, non-negative stock/prices, allowed statuses, timestamp relationships, and at most one successful payment per order. Names and address fields reject whitespace-only values.

Foreign keys use RESTRICT on deletion to preserve referenced history. This does not make records immutable: restricting edits to placed orders and controlling status transitions require application permissions and transactional workflows. A row CHECK cannot ensure that an order has items, a payment equals the item total, inventory exists for every product, or aggregate stock changes are correct across concurrent sessions. Those rules must not be claimed as enforced by this schema alone.

## Anomalies avoided

- Changing a customer's phone updates one customer row rather than every order.
- Adding a product does not require an order to exist.
- Deleting a draft order's items does not delete product or customer details.
- Renaming a category updates one row rather than every product.
- Updating catalogue prices or saved addresses does not rewrite previous sales.
