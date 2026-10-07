# Python & PySpark Exercises

Commit your solutions to `solutions/python/` and `solutions/pyspark/`. After **every** PySpark exercise, open the Spark UI (or `explain("formatted")`) and write one line about what you saw: jobs, stages, shuffles.

## Part A — Python warm-ups (Weeks 2–4)

- **P1.** Given a list of table names with duplicates, return a sorted unique list.
- **P2.** Given `["sales.orders", "sales.customers", "finance.gl"]`, build `{schema: [tables]}`.
- **P3.** Invert `{"orders": "EXTERNAL", "customers": "MANAGED", "gl": "EXTERNAL"}` to `{type: [tables]}`.
- **P4.** Write `build_target_name(source, catalog_map)` (see [Phase 3](../phases/phase-03-python.md)) + 5 pytest tests.
- **P5.** Read `inventory.csv` (`schema,table,type,format,location`) with `csv.DictReader`; count by type × format.
- **P6.** Write the same counts to `summary.json`.
- **P7.** Function that returns the migration method for a table dict, following the decision matrix in [Phase 7 §10](../phases/phase-07-hms-to-unity-catalog.md#10-migration-strategies-and-tools). Test every branch.
- **P8.** Comprehension: generate `GRANT` statements for a list of `(principal, privilege, schema)` tuples.
- **P9.** Custom exception `MigrationError`; a function that raises it with a helpful message on invalid input.
- **P10.** `logging` setup with timestamp/level/module; log at INFO and WARNING; write to a file and to the console.
- **P11.** Load `conf/dev.yaml` into a frozen dataclass; fail clearly if a key is missing.
- **P12.** Call `https://jsonplaceholder.typicode.com/posts` with timeout + retries + backoff; save the results to JSON.
- **P13.** Walk a folder of `.py`/`.sql` files; report lines matching `/mnt/`, `dbfs:/`, `input_file_name`, `sparkContext`, and `FROM <word>.<word>` (2-level).
- **P14.** Package P4/P7/P13 as `migration_gen` with `src/` layout + `pyproject.toml`; `pip install -e .`; run the tests.
- **P15.** Fix the mutable-default bug: `def add_table(t, tables=[]): tables.append(t); return tables`.

## Part B — PySpark (Weeks 4–6)

Data: `samples.tpch.*`, `samples.nyctaxi.trips` (Databricks), or generate it with `spark.range()` locally.

### Basics
1. Create a DataFrame from a list of tuples with an explicit schema; print the schema.
2. Read a CSV with `inferSchema`, then with an explicit schema. Compare the types and the speed.
3. `select`, `withColumn`, `filter`, `when/otherwise`: classify taxi trips into short/medium/long.
4. `groupBy` + `agg` (count, sum, avg, max): revenue per pickup zip.
5. Replace a 10× `withColumn` loop with a single `select`. Compare the plans.
6. Handle NULLs: `fillna`, `dropna`, `coalesce`; count NULLs per column in one pass.
7. Dates: parse strings to timestamps, extract hour/day, convert UTC → `Asia/Dubai`.

### Joins & windows
8. Join `orders` and `customer` (TPCH). Inspect the plan: what join strategy was used?
9. Force `broadcast()` on the smaller side. Compare the plans and durations.
10. Anti join: customers with no orders.
11. Window: latest order per customer (`row_number`).
12. Window: running total and `lag` per customer.
13. Explode a nested JSON array into rows; flatten a struct.

### Internals
14. Count jobs/stages for: `filter → groupBy → count`. Predict the number first, then verify.
15. Print `df.rdd.getNumPartitions()` after reading, after `groupBy` (with AQE on/off), after `repartition(50)` and after `coalesce(5)`.
16. **Skew lab**: create a key where 70% of rows share one value; `groupBy` it; find the slow task (max vs median). Fix it with (a) AQE skew settings, (b) salting.
17. Write with `repartition(500)` vs `repartition(4)`; compare file counts with `DESCRIBE DETAIL`.
18. Cache a DataFrame used 3 times; compare the total time with/without the cache; `unpersist()`.
19. Trigger a driver OOM *safely* in local mode (`collect()` on a big range with small driver memory). Read the error.
20. Replace a Python UDF (e.g. string normalisation) with built-ins; compare the timings.

### I/O & robustness
21. Read CSV with a corrupt row in `PERMISSIVE` (`columnNameOfCorruptRecord`), `DROPMALFORMED` and `FAILFAST`.
22. Add `_metadata.file_path` and `_metadata.file_modification_time` to a file read.
23. Write to Delta with `partitionBy` vs `clusterBy` (Databricks); query each with a filter; compare files read.
24. Append a DataFrame with an extra column → see the schema error → fix it with `mergeSchema`.
25. **Mini-pipeline**: raw CSV + JSON → typed → deduped → joined (broadcast dim) → aggregated → written to Delta. Then write unit tests for 2 of the transformation functions.

## Part C — Stretch
- S1. Auto Loader with `availableNow`: ingest, add files, re-run, add a new-column file.
- S2. Implement SCD2 with the PySpark `DeltaTable.merge()` API instead of SQL.
- S3. Read a table's Change Data Feed and apply the changes to a downstream aggregate.
- S4. Write a generic `compare_tables(spark, src, tgt, keys)` returning counts of match/mismatch/missing/extra. You'll reuse it for migration validation.
