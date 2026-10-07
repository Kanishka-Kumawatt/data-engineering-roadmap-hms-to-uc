# Phase 13 — Performance Optimization

**Weeks:** 13–14 · **Time:** ~12 h (3 h theory, 9 h hands-on)
**Goal:** Investigate a slow job methodically, find the real bottleneck, and fix *that*, rather than applying random tuning rules.

> **Mentor note:** Juniors tune by superstition ("add more nodes", "cache everything", "set shuffle partitions to 2000"). Seniors **measure first**. This phase teaches you an investigation routine. The fixes are the easy part once you know what's wrong.

---

## 1. The investigation routine

```
1. Define "slow"     → baseline? (yesterday 12 min, today 55 min) SLA? Which task?
2. What changed?     → data volume, code (git log), DBR/compute, upstream table layout, concurrency
3. Locate            → Job run → slow task → Spark UI → slowest job → slowest stage
4. Diagnose stage    → duration, input size, shuffle read/write, spill, task max vs median, GC time
5. Read the plan     → SQL/DataFrame tab or EXPLAIN: scans (files read/pruned), joins (type), exchanges
6. Hypothesis        → "Stage 7 is a sort-merge join with 1 skewed task holding 40% of rows"
7. Fix ONE thing     → test on a representative dataset in dev
8. Measure again     → compare against baseline; keep or revert
9. Document          → error/perf log + PR description
```

For SQL warehouses: open the **query profile**. It shows the same information visually: time per operator, rows, bytes, spill, and files pruned.

## 2. Symptoms → causes → fixes

| Symptom in UI / profile | Likely cause | Fixes |
|---|---|---|
| Scan reads far more files/bytes than needed | No pruning: filter not on cluster/partition cols, function on filter column, poor layout | Filter on clustering columns; liquid clustering/Z-ORDER; avoid wrapping columns in functions; select fewer columns |
| Thousands of tiny tasks, long "listing" time | **Small files** (streaming, over-partitioning, `repartition(500)` writes) | `OPTIMIZE`; auto-compaction / optimized writes; fewer partitions; liquid clustering |
| One task takes 20× the median | **Data skew** on join/group key (NULLs, hot keys) | AQE skew join; filter/handle NULL keys separately; salting; broadcast the small side |
| Huge shuffle read/write | Wide joins/aggregations on big data | Broadcast small tables; pre-aggregate before joining; join on fewer rows (filter first); bucketing is rarely worth it now |
| Spill (memory/disk) high | Partitions too large for executor memory | More shuffle partitions (or let AQE handle it); memory-optimised nodes; reduce row width |
| Sort-merge join where one side is small | Statistics missing / threshold too low | `broadcast()` hint; `ANALYZE TABLE ... COMPUTE STATISTICS`; raise `spark.sql.autoBroadcastJoinThreshold` carefully |
| Rows explode after a join | Duplicate keys (fan-out) — correctness *and* perf issue | Fix the grain/dedupe; it isn't a tuning problem |
| Driver busy, executors idle | `collect()`, Python loops on driver, `toPandas`, many small jobs in a loop | Push work to Spark; batch operations; avoid per-row actions |
| Python UDF stage slow | Row-by-row serialisation | Built-in functions; `pandas_udf` if you really need custom logic |
| Job slow to start | Cluster startup | Pools, serverless |
| MERGE slow | Target scan of the whole table | Add a partition/cluster predicate to the `ON` clause; clustering on the merge key; deletion vectors; smaller source |
| Fast yesterday, slow today, same code | Data growth, skew from a new hot key, small files accumulated, stats stale | Check `DESCRIBE DETAIL` (numFiles, size) and history; OPTIMIZE; investigate the data |

## 3. Configuration you should know (not memorise)

| Config | Default (typical) | Meaning |
|---|---|---|
| `spark.sql.shuffle.partitions` | 200 (AQE adapts) | Partitions after shuffles |
| `spark.sql.adaptive.enabled` | true | AQE: coalesce partitions, switch join strategy, handle skew |
| `spark.sql.adaptive.skewJoin.enabled` | true | Split skewed partitions |
| `spark.sql.autoBroadcastJoinThreshold` | 10 MB (Databricks may differ) | Max size to broadcast |
| `spark.sql.files.maxPartitionBytes` | 128 MB | Input split size |

**Rule:** change configs only with evidence, one at a time, and write down why. On serverless, many configs can't be set at all, and you optimise data layout and code instead.

## 4. File formats & Delta layout
- Delta/Parquet are **columnar**: select fewer columns and less is read. CSV/JSON are read fully every time, so ingest them into Delta once (Bronze) and never query the raw files repeatedly.
- Target file sizes of ~100 MB–1 GB. Check with `DESCRIBE DETAIL t` (`numFiles`, `sizeInBytes`).
- **Liquid clustering** for new large tables; **predictive optimisation** for UC managed tables.
- **Data skipping** uses min/max stats on the first 32 columns by default, so put commonly filtered columns early, or configure the stats columns.
- **Deletion vectors** make UPDATE/DELETE/MERGE cheaper (fewer rewritten files).

## 5. Worked investigation

> **Ticket:** "`gold_customer_ltv` went from 15 min to 70 min after the migration to UC."

1. **What changed?** The migration: the table was CTAS'd from Parquet into UC *without* clustering, and the job now runs on a different compute.
2. **Spark UI:** stage 12 takes 50 min: a sort-merge join `orders ⨝ customers`, 200 tasks, max task 48 min vs median 40 s → **skew**.
3. **Data check:** `SELECT customer_id, COUNT(*) FROM orders GROUP BY 1 ORDER BY 2 DESC LIMIT 5` → `customer_id = NULL` has 30% of rows (guest checkouts).
4. **Why was it OK before?** The old job filtered `customer_id IS NOT NULL` in a view that was rewritten during migration, and the filter was lost. **The root cause is a migration defect, not "Spark being slow".**
5. **Fix:** restore the filter (correctness!), and also OPTIMIZE + cluster `orders` by `customer_id, order_date`.
6. **Result:** 11 min. **Prevention:** add a view-result fingerprint comparison to the migration validation suite.

The lesson to take from this: performance problems are often correctness problems underneath.

---

## How this connects to HMS→UC
- Migrated tables may lose their **layout** (CTAS doesn't preserve Z-ORDER/partitioning unless you specify it), their **statistics**, or their **filters in views**.
- Compute changes (job cluster → serverless, access mode) change performance characteristics.
- Capture **performance baselines** before migration and compare afterwards (Phase 11 §4, test #10).

## Hands-on
1. Generate a 50M-row skewed dataset; join and aggregate; find the skew in the UI; fix it three ways (AQE, NULL handling, salting) and compare.
2. Write 2,000 small files; time a query; OPTIMIZE; time it again; compare `numFiles`.
3. Same query with a filter on a clustered column vs a non-clustered column: compare files read in the query profile.
4. Replace a Python UDF with built-ins; measure.
5. Take one slow query from your project (dev), run the investigation routine, and write it up (anonymised).

## After this phase you should be able to explain
- [ ] Your step-by-step routine for a slow job
- [ ] How to spot skew, spill, small files and bad joins in the Spark UI
- [ ] When broadcasting helps, and when it hurts
- [ ] Why Delta layout (clustering, file size, stats) matters
- [ ] Why you change one thing at a time

## Beginner vs experienced
| Beginner | Experienced |
|---|---|
| Bigger cluster | Finds the bottleneck stage, and fixes the data layout or code |
| Copies configs from blogs | Changes configs with evidence, and measures |
| Treats slowness as infra | Checks correctness (fan-out, lost filters) first |

## Interview questions
1. A job that ran in 10 minutes now takes an hour. How do you investigate?
2. What is data skew, and how do you fix it?
3. What causes the small-files problem, and how do you solve it?
4. When would you use a broadcast join? What are the risks?
5. Partitioning vs liquid clustering?
6. How do you optimise a slow MERGE?
7. What does AQE do?
