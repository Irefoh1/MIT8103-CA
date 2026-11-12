# MarketHub: alignment across the five portfolios

This roadmap explains cross-portfolio alignment. Actual completion and execution evidence are recorded in each activity's README and evidence folder; proposed features are not evidence of implementation. The case study remains the same simulated retailer throughout. Different database models represent different access patterns within that organisation.

| Portfolio | Planned work | How Portfolio 1 supports it |
|---|---|---|
| 1: Design and modelling | ER model, relational schema, constraints, normalisation | Nine connected entities covering catalogue, customers, sales, payments, inventory, and delivery tracking |
| 2: Query processing and optimisation | Customer order history, sales aggregation, low-stock queries; EXPLAIN ANALYZE before and after a justified index | Orders, order_items, products, inventory, and payment_attempts support joins and aggregation. Generate a larger synthetic dataset; the tiny P1 seed cannot establish meaningful performance gains. Existing FK indexes are a baseline, not proof of optimisation. |
| 3: Transactions and concurrency | Commit and rollback of checkout; competing purchases of the final unit; row locking or a conditional stock update under a stated isolation level | Integer stock balances and order items support a reproducible two-session example. Use a consistent product lock order for multi-item checkout. Inventory, item creation, and order placement must commit atomically. |
| 4: NoSQL and advanced data models | Implement a MongoDB product catalogue with category and variable product attributes; demonstrate inserts, reads, updates, and an index | Reuse P1 product_id/SKU, names, categories, and NGN prices. Add category-specific attributes such as keyboard layout or notebook page count as an explicit extension of the same case study. Explain embedding, document validation, and the tradeoff against relational joins. |
| 5: Distributed and cloud database exercise | Implement a small local PostgreSQL primary/standby replication exercise; analyse replication lag, read routing, availability, and consistency; discuss sharding and a possible cloud deployment | Replicate the existing MarketHub database. Order-history/catalogue reporting can tolerate explicitly stated stale reads; checkout stock and payment decisions use the primary. Capture configuration and actual replication observations. |

## Portfolio 4 boundaries

MongoDB is the chosen document database implementation, not a requirement imposed by the brief. Portfolio 4 now implements the catalogue snapshot with 19 verified checks; see `portfolio-4-nosql/README.md`. Product documents embed category display data and a flexible attributes object while retaining stable SKU and product_id values mapped from P1. Prices use Decimal128, not binary floating point.

The document model intentionally differs from the normalised SQL model because its read pattern is fetching a complete product listing. Explain how category renaming and catalogue updates propagate to embedded values. For the exercise, label the catalogue import as a snapshot; do not imply automatic synchronisation. PostgreSQL remains the authoritative transactional stock, order, and payment store. Do not duplicate live stock into MongoDB and imply that it is safe for checkout without a consistency mechanism.

## Portfolio 5 boundaries

The brief allows a distributed/cloud discussion **or** setup for the same case study. A local replication lab provides practical distributed-database evidence; it is not evidence of a cloud deployment. If a cloud service is actually deployed later, record that separately.

Asynchronous replication can produce stale standby reads and lose unreplicated transactions if the primary fails. A primary plus standby does not automatically provide failover, split-brain prevention, or continuous availability. Any failover claim requires a tested promotion/routing procedure and its limitations. Compare synchronous replication's durability benefits with its latency and availability costs.

Discuss sharding as a proposed future design, not an implemented feature. Customer-based partitioning could colocate order history, but globally shared inventory and product data create cross-shard coordination challenges. Do not claim that ordinary table partitioning constitutes distributed sharding.

## Corrections and current limits

- Multiple shipment records provide tracking for multiple parcels; there is no shipment_items relation, so item-level partial fulfilment is not implemented. Add that relation only if later requirements need it.
- SQL alone does not enforce every business workflow. Nonempty placed orders, matching successful-payment totals, immutable placed-order contents, and safe concurrent checkout still need implementation and evidence.
- P1 can remain relational and in 3NF. P4 does not require converting all sales tables to NoSQL, and P5 does not require redesigning the retailer as a marketplace or adding multiple warehouses.
