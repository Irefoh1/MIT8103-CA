# Portfolio 2: Query Processing and Optimisation

## Purpose and case study

Continue the MarketHub e-commerce case study from Portfolio 1. Implement business queries, inspect actual execution plans, add justified indexes, and compare measured performance without changing query results. No Portfolio 1 schema or seed file is edited.

## Files

| File/folder | Purpose |
|---|---|
| `seed.sql` | Deterministic synthetic workload for a new database using the P1 schema |
| `queries/` | Four standalone business queries |
| `optimise.sql` | Three additional workload-specific indexes |
| `run-benchmark.py` | Reproducible Docker/psql runner using Python's standard library |
| `evidence/` | Actual results, execution plans, timing samples, environment, index sizes, and verification |
| `performance-analysis.md` | Interpretation of the recorded measurements |

## Dataset

5,000 customers, 10 categories, 1,000 products and stock records, 100,000 orders, and 300,000 order items. Each order has three distinct products, positive quantities, and purchase prices copied from the catalogue. Dates span approximately January to October 2026; all filters use explicit UTC boundaries. Successful payments equal the associated paid-order totals. Cancelled and unpaid orders are excluded from the revenue query.

Data is fabricated using SQL generate_series and deterministic arithmetic. Inventory is an independent current-stock snapshot, not a reconstructed inventory ledger. No shipments or saved addresses are needed for these queries. This workload demonstrates query behaviour; it does not simulate real customer distributions, stock-reservation workflows, or production payment processing.

## Queries and optimisation decisions

1. **Q1: Customer order history.** Return customer 42's ten latest orders and their totals. P1 already has an index on customer_id; the new composite index also supplies the requested timestamp/ID order, helping LIMIT avoid sorting all matching orders. The existing order-item primary key supports total lookups. Each customer has only 20 orders, so the baseline is already efficient; a dramatic gain is not assumed.
2. **Q2: Paid orders for one day.** Use a half-open timestamp range and a literal paid-status predicate. The new partial covering index holds only paid orders and supports date filtering, ordering, and the returned customer ID. Do not replace the timestamp predicate with a date conversion and assume the same index access path.
3. **Q3: Low-stock products.** A partial index contains the ten inventory rows whose quantity is below the reorder level. This can avoid scanning all stock rows, but the table is small and measured savings may be modest.
4. **Q4: Top products by revenue.** Join orders, items, and products, group sales, and rank the top ten. This intentionally broad query acts as a comparison: indexes aimed at selective lookups may not help an aggregation that processes much of the data. Order status defines paid orders in this seed; production revenue recognition/refunds are outside scope.

All result orders include a unique tie-breaker. No query joins payments to item rows and accidentally multiplies revenue by the number of payment attempts.

## Reproduce

Prerequisites: running Docker engine, a PostgreSQL container, Python 3, and permission to run Docker. The original container is `markethub-p1-validation` using `postgres:18-alpine`. Run from the repository root:

```powershell
python portfolio-2-query-optimisation/run-benchmark.py
```

The runner creates `markethub_p2`, executes the P1 schema **without** its tiny seed, then runs the P2 seed. It fails if that database already exists; it never drops or resets an existing database. For another run:

```powershell
python portfolio-2-query-optimisation/run-benchmark.py --database markethub_p2_repeat
```

This replaces the local evidence files, so preserve the previous evidence first if you want both runs. Use `--container NAME` for another PostgreSQL container. Nothing is pushed to GitHub automatically.

## Measurement method

- Keep all P1 primary keys, unique constraints, and FK indexes as the baseline. Do not disable sequential scans or force index plans.
- Run VACUUM ANALYZE after loading. Create additional indexes only after all baseline measurements; run ANALYZE again afterward.
- Fix timezone to UTC, disable JIT, and use zero parallel query workers in both phases to reduce sources of variation. This is a controlled single-session experiment, not a production tuning recommendation.
- Execute each result query, discard one EXPLAIN warm-up, then collect five `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` runs. Report median execution time, not planner estimated cost or wall-clock Docker startup time.
- Save all five JSON plans and an additional readable plan per query per phase. The readable plan is an extra execution and need not match the median timing.
- Compare complete ordered CSV results before and after. Changing output invalidates the comparison.
- Record environment settings and index sizes. Cache state is warmed but not forcibly controlled; before/after phases are sequential, so cache effects and background activity remain limitations.

## Reading a plan

`Seq Scan` visits table rows; an `Index Scan` uses an index to locate rows; an `Index Only Scan` can retrieve columns from the index, although visibility checks may still require heap access. A `Sort` orders rows. A `Hash Join` or `Nested Loop` combines tables. An aggregate calculates totals.

Planner `cost` is an estimate, not milliseconds. `actual time` describes observed node timing; `Execution Time` is the overall measured executor time. `rows` and `loops` help identify repeated work. Buffer hits are accesses served from PostgreSQL shared buffers; reads do not necessarily mean physical disk I/O because the operating system may cache data. Do not sum overlapping parent/child node timings as though they were independent.

## Tradeoffs and limitations

Indexes consume storage and make inserts and indexed-column updates more expensive. Partial indexes serve queries whose predicates match or imply their conditions. This experiment measures read performance and index storage, not write throughput. Index-only behaviour depends on visibility maps and will differ under frequent updates. Results apply to this dataset, machine, settings, and run; they are not guarantees of production speedups. Larger or more representative data may change the best plan.

## Student review and submission

Reference: MIT 8103 assignment brief, Portfolio 2 expected deliverables. AI assistance: OpenAI Codex prepared the queries, data generator, benchmark runner, and initial analysis and executed the lab. The student must review the scripts, understand the measurements, document personal verification/corrections, and include the final AI-use declaration. No personal reflection is fabricated here.
