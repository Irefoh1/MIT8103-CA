# Performance analysis: MarketHub

## Actual run

Executed on 23 October 2026 (Africa/Lagos; raw UTC timestamp is in `evidence/environment.txt`), PostgreSQL 18.3 in the existing Docker container, using the separate `markethub_p2` database. P1's database was preserved. Dataset: 100,000 orders, 300,000 items, 60,000 successful payments, 5,000 customers, and 1,000 products. All four ordered result sets matched exactly before and after adding indexes.

## Results

Times below are medians of five measured executor runs after one discarded warm-up, in milliseconds. Source: `evidence/timing-summary.csv`; all measured samples and buffer information are preserved in the JSON plans.

| Query | Before | After | Observed change |
|---|---:|---:|---|
| Q1: customer order history | 2.166 | 0.848 | 2.55x faster; 60.85% lower time |
| Q2: paid orders on a specified day | 13.633 | 0.283 | 48.17x faster; 97.92% lower time |
| Q3: low-stock catalogue | 0.921 | 1.243 | 34.96% higher time; no measured gain |
| Q4: top products by revenue | 619.753 | 647.850 | 4.53% higher time; no measured gain |

These are observations from one controlled lab run, not statistically established production effects. Millisecond-scale results are particularly sensitive to machine scheduling and cache state. Planning time and client/network overhead are excluded from executor times; they can dominate fast queries in actual applications.

## Why the plans changed

**Q1:** The baseline uses a bitmap index/heap scan on P1's customer index, followed by sorting the customer's 20 orders. The additional `(customer_id, ordered_at DESC, order_id DESC)` index supplies the desired order directly and supports an index-only scan for the order header. LIMIT stops at ten rows; the existing item primary key supplies each order's total. In the separately captured readable plans, shared buffer hits fall from 91 to 67. The new index is 5,079,040 bytes, so it has a storage/write cost even though the absolute execution saving is small.

**Q2:** The baseline scans 100,000 orders, discards 99,802, and sorts the 198 matches. After optimisation, a partial index on paid orders supplies the timestamp range and output order through an index-only scan, with zero heap fetches in the saved plan. Readable-plan buffer hits fall from 1,538 to 5. Avoiding most row inspection explains the large observed improvement. This index occupies 2,457,600 bytes.

**Q3:** The partial index reduces inventory-side scanning from 1,000 rows to ten index entries. However, the complete join still scans the 1,000-row products table and sorts the small result. Readable-plan shared buffer hits fall from 19 to 15, but the median executor time increases. PostgreSQL also estimates 333 qualifying inventory rows rather than the actual ten: a comparison between two columns is not accurately captured by the ordinary column statistics here. A smaller estimated plan cost and use of an index do not guarantee a lower measured runtime. The index is only 16,384 bytes, but this run does not justify retaining it for speed. It remains in this experimental database to preserve the measured after-state; omit it from a production deployment unless representative measurements show a benefit.

**Q4:** PostgreSQL uses the new paid-order index to retrieve 60,000 orders, but still scans 300,000 order items, joins 180,000 matching item rows, and aggregates by product before ranking. Those operations dominate the workload. Its median increases slightly; this experiment cannot establish that the index causes a general regression. No improvement is claimed. For a real reporting workload, investigate measured alternatives such as a carefully refreshed summary/materialized view, with explicit freshness and maintenance tradeoffs. Such an alternative is not implemented or benchmarked here.

The three added indexes occupy 7,553,024 bytes together (about 7.20 MiB), excluding any wider operational overhead. Their write-maintenance cost is not measured in this read-only experiment.

## Conclusion and limits

The customer-history and paid-date indexes have measured benefits for the selected queries. The low-stock index does not improve measured runtime on this small catalogue, and the broad revenue aggregation needs a different investigation. Keep these mixed results rather than claiming every index helps.

The baseline retains P1 indexes, PostgreSQL chooses plans freely, and result equality is checked. However, the data distribution is synthetic, only five samples are collected per phase, phases run sequentially, no cold-cache reset occurs, no competing clients run, JIT/parallel workers are disabled, and vacuum visibility favours index-only scans. Neither sustained throughput nor checkout concurrency nor write performance is demonstrated. Individual student reflection and understanding must be added after review.
