# Portfolio 1: Database Design and Modelling

## 1. Selected organisation

**Organisation:** MarketHub, a simulated e-commerce retailer.

**Nature of business:** MarketHub sells physical products through an online storefront and fulfils customer orders from one stock location. It is a single retailer rather than a marketplace of independent sellers.

**Database users:** Customers browse products and place orders; catalogue staff maintain products and categories; warehouse staff maintain stock and dispatch orders; finance staff reconcile payments; administrators maintain accounts and reporting access. These are business roles; database access roles are outside this initial schema.

**Major data:** Customers, saved addresses, categories, products, inventory, orders, order items, payment attempts, and shipments.

**Key operations:** Register customers, maintain addresses, browse products, check stock, place multi-item orders, record payment attempts, retrieve order histories, and track deliveries.

## 2. Scope and business rules

1. Each customer has a unique email address and may have multiple saved addresses and orders.
2. A product belongs to one category. A category may contain many products. Multiple categories per product are outside this version's scope.
3. Every product has a unique SKU and at most one inventory record. The product-creation workflow must create its inventory record in the same transaction.
4. Stock quantity and reorder level cannot be negative. Stock reservations, warehouses, returns, tax, discounts, and refunds are outside this initial version.
5. An order belongs to one customer and must contain at least one item before placement. The schema permits an empty draft while its items are being inserted.
6. A product appears at most once in an order; quantity captures multiple units. Quantity must be positive.
7. Each item stores the unit price agreed at purchase. Changing the catalogue price must not change an existing order's price.
8. Each order stores a delivery-address snapshot. Editing a customer's saved address must not change the destination recorded for an existing order. Saved addresses are optional and are not linked to historical orders.
9. All amounts use Nigerian naira (NGN). Prices are fixed-precision decimals; floating-point types are not used for money.
10. An order may have multiple payment attempts, but at most one successful payment. This version supports full payment only, not instalments. A successful payment must equal the order item total; this is checked by the payment workflow, not a row CHECK constraint.
11. An order may have multiple shipments. Shipment item allocation is deferred; this version records shipment tracking only and does not prove which items are in each parcel.
12. Customer, product, and order records referenced by historical transactions cannot be deleted through cascading deletion. Inactive products remain available for historical reporting.
13. The checkout workflow must atomically check stock, create items, reduce inventory, and place the order. Locking and concurrent checkout behaviour will be demonstrated in Portfolio 3.

## 3. Design artefacts

- [ER diagram](er-diagram.md): entities, relationships, and cardinalities.
- [Relational schema and normalisation](design-and-normalisation.md): keys, dependencies, and design reasoning.
- [PostgreSQL schema](schema.sql): tables, constraints, and indexes.
- [Sample data and verification](sample-data-and-checks.sql): a small reproducible dataset and inspection queries.
- [Constraint checks](constraint-checks.sql): five expected rejection checks, rolled back after execution.
- [Whole-project alignment](../portfolio-roadmap.md): proposed work for all five activities, including NoSQL and distributed database boundaries.

## 4. Implementation procedure

Target DBMS: PostgreSQL. The scripts use PostgreSQL identity columns and a partial unique index. They are not intended to run unchanged in MySQL or SQLite.

Use a new, empty practice database. From this portfolio directory, with PostgreSQL installed and `psql` available:

```powershell
createdb markethub_portfolio
psql -X -v ON_ERROR_STOP=1 -d markethub_portfolio -f schema.sql
psql -X -v ON_ERROR_STOP=1 -d markethub_portfolio -f sample-data-and-checks.sql
```

Scripts are intended for one execution against a fresh database. Both use transactions so a failure rolls back that script's changes. No database reset or destructive cleanup is included.

The sample contains two customers, two categories, three products, one order with two items, one failed payment attempt, one successful attempt, and one shipment. The verification query should return an order total of **NGN 35,000.00**. Stock was reduced from 20 to 18 keyboards and from 50 to 49 mice as part of the example sale.

## 5. Evidence to collect after execution

Create an `evidence/` folder and save actual evidence showing:

- PostgreSQL version and successful script execution.
- Tables and constraints, for example `\dt markethub.*` and `\d markethub.order_items` in psql.
- Results of the sample order and stock queries.
- Rejected duplicate email, invalid item quantity, negative stock, missing foreign key, and second successful payment. Run each deliberate failure separately so an expected error does not hide later checks.

**Current verification status:** On 18 October 2026, the schema and sample scripts executed successfully in PostgreSQL 18.3 using the local Docker image `postgres:18-alpine`. The query returned NGN 35,000.00; stock balances were 18 keyboards, 49 mice, and 100 notebooks. All five rejection checks passed. Actual output is saved in [execution evidence](evidence/postgresql-execution.txt) and [constraint evidence](evidence/constraint-checks.txt). The isolated container is named `markethub-p1-validation`; it has no network connectivity or published ports. Student review, reflection, and any desired screenshots remain pending. These checks do not establish concurrency correctness or validate unimplemented workflow rules.

## 6. References and AI-use record

- Course assignment brief: MIT 8103 Advanced Database Systems, 2026/2027 First Semester Continuous Assessment, sections 2–5, 7–9, and 11–12.
- AI assistance: OpenAI Codex helped prepare the initial design, SQL, and documentation. Student review, corrections, and execution results are pending and must be recorded truthfully before submission.
