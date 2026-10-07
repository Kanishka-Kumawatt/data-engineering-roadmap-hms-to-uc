# Phase 4 — Apache Spark / PySpark

**Weeks:** 4–6 · **Time:** ~24 h (7 h theory, 17 h hands-on)
**Goal:** Write correct PySpark, and understand **what Spark is doing internally** so you can debug and tune it.

> **Mentor note:** Many people can write PySpark. Fewer can explain *why* their job took 40 minutes. That understanding (jobs, stages, shuffles, partitions) is what separates a script-runner from an engineer. Open the **Spark UI** after every exercise this phase, even when nothing is wrong. You're training your eye.

---

## 1. Why Spark is needed

**Simply:** One computer can't process 5 TB fast. Spark splits the data into chunks (**partitions**) and processes them in parallel across many machines (**executors**), coordinated by one **driver**.

**Real-world:** Counting all the votes in a country. One person would take years; 10,000 counting stations (executors) count in parallel and report to a central office (driver), which adds up the totals.

## 2. Architecture

```
                ┌───────────────────────────┐
  your code ──▶ │ DRIVER                    │  builds the plan, schedules tasks,
                │ SparkSession, DAG,        │  collects small results
                │ scheduler                 │  (OOM here if you .collect() big data!)
                └──────────┬────────────────┘
          ┌────────────────┼─────────────────┐
   ┌──────▼─────┐   ┌──────▼─────┐   ┌──────▼─────┐
   │ EXECUTOR 1 │   │ EXECUTOR 2 │   │ EXECUTOR 3 │   each has cores (task slots) + memory
   │ task task  │   │ task task  │   │ task task  │   one task = one partition
   └────────────┘   └────────────┘   └────────────┘
```

| Term | Meaning |
|---|---|
| **Application** | Your SparkSession (on Databricks, the cluster's session) |
| **Job** | Triggered by each **action** (`count`, `write`, `collect`, `show`) |
| **Stage** | A set of tasks that run without a shuffle; **stage boundaries = shuffles** |
| **Task** | Work on **one partition** on one core |
| **Partition** | A chunk of data. Parallelism = number of partitions (limited by cores) |

## 3. DataFrames vs RDDs

- **DataFrame:** a table with a schema, optimised by the **Catalyst optimizer** and the **Tungsten** engine. **Use this, always.**
- **RDD:** low-level distributed collection with no schema and no optimisation. Legacy.

**HMS→UC connection:** On UC **Standard (shared) access mode** compute, RDD APIs and `sparkContext` access are restricted. Legacy code using `sc.parallelize`, `rdd.map` or `sc._jsc` breaks after migration and has to be rewritten with DataFrames, or run on **Dedicated** compute. This is a real migration work item.

## 4. Transformations vs actions, and lazy evaluation

```python
df = spark.read.table("samples.tpch.orders")            # nothing runs yet
big = df.filter("o_totalprice > 100000")                # transformation: lazy
by_status = big.groupBy("o_orderstatus").count()        # transformation: lazy
by_status.show()                                        # ACTION: now Spark plans and runs everything
```

Spark builds a **logical plan**, optimises it (pushes filters down, prunes columns) and only runs it at an action. `by_status.explain("formatted")` shows the plan. **Look for `PushedFilters`, `Exchange` (= shuffle) and `BroadcastHashJoin` vs `SortMergeJoin`.**

| Narrow transformation (no shuffle) | Wide transformation (shuffle) |
|---|---|
| `select`, `filter`, `withColumn`, `union` | `groupBy`, `join` (non-broadcast), `distinct`, `orderBy`, `repartition`, window functions |

## 5. Partitions and shuffles

- Reading files: roughly one partition per ~128 MB (`spark.sql.files.maxPartitionBytes`).
- After a shuffle: `spark.sql.shuffle.partitions` (default 200). **AQE** (Adaptive Query Execution, on by default in Databricks) coalesces these at runtime.
- `repartition(n)`: full shuffle, even distribution. `coalesce(n)`: merges partitions without a full shuffle (reduce only).

**A shuffle** redistributes data across the network so that rows with the same key end up together. It's expensive: disk + network + serialisation. **Most performance work is reducing or fixing shuffles.**

## 6. Joins

| Strategy | When | Cost |
|---|---|---|
| **Broadcast hash join** | One side small (default threshold 10 MB, often raised; AQE can switch at runtime) | Small side copied to every executor; **no shuffle of the big side** |
| **Sort-merge join** | Both sides large | Both sides shuffled + sorted |
| Shuffle hash join | Medium | Shuffle, hash build |

```python
from pyspark.sql.functions import broadcast
fact.join(broadcast(dim_country), "country_code")
```

**Skew:** if one key (e.g. `country = 'US'`, or `customer_id = NULL`) has 50% of the rows, one task does 50% of the work while the others sit idle. Symptom: in the Spark UI one task takes 30 min and the median is 20 s. Fixes: AQE skew join (`spark.sql.adaptive.skewJoin.enabled`), filtering NULL keys, salting, or broadcasting.

## 7. Aggregations, windows and caching

```python
from pyspark.sql import functions as F, Window as W

agg = (orders.groupBy("customer_id")
       .agg(F.count("*").alias("n_orders"), F.sum("amount").alias("revenue"),
            F.max("order_ts").alias("last_order_ts")))

w = W.partitionBy("customer_id").orderBy(F.col("updated_at").desc())
latest = df.withColumn("rn", F.row_number().over(w)).filter("rn = 1").drop("rn")
```

**Caching:** `df.cache()` keeps a DataFrame in memory after the first action. Only use it when the **same DataFrame is reused several times** in one job, and `unpersist()` when you're done. Caching everything wastes memory and causes spill/OOM. (Databricks also has automatic disk caching for Delta/Parquet reads. Note that `.cache()` isn't supported on serverless compute.)

## 8. Spark SQL ↔ DataFrame API

They compile to the **same plan**. Use whichever reads better.
```python
orders.createOrReplaceTempView("orders_v")
spark.sql("SELECT customer_id, SUM(amount) FROM orders_v GROUP BY customer_id")
```

## 9. Reading and writing data

```python
# Read with an explicit schema (production) instead of inferSchema (slow, fragile)
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, TimestampType, DecimalType
schema = StructType([
    StructField("order_id", IntegerType(), False),
    StructField("customer_id", IntegerType(), True),
    StructField("amount", DecimalType(12, 2), True),
    StructField("order_ts", TimestampType(), True),
])
raw = (spark.read.format("csv").option("header", True).schema(schema)
       .option("mode", "PERMISSIVE").option("columnNameOfCorruptRecord", "_corrupt")
       .load("/Volumes/learn/retail/landing/orders/"))

# Source file metadata (works on UC; input_file_name() does not on Standard access mode)
raw = raw.select("*", "_metadata.file_path", "_metadata.file_modification_time")

# Write to a UC table (3-level name)
raw.write.format("delta").mode("append").saveAsTable("learn.retail.bronze_orders")
```

Formats: **Delta** (default for tables), Parquet (columnar), CSV/JSON (sources), Avro (Kafka). Know read modes: `PERMISSIVE`, `DROPMALFORMED`, `FAILFAST`.

## 10. Performance and debugging basics (deeper in Phase 13)

**Reading the Spark UI** (Compute → your cluster → Spark UI, or the job run → "Spark UI"):
1. **Jobs tab:** which job is slow?
2. **Stages tab:** which stage? Look at **duration**, **shuffle read/write** and **spill (memory/disk)**.
3. **Task summary:** compare **max vs median** duration. A large gap means **skew**.
4. **SQL/DataFrame tab:** the physical plan with row counts per operator. Find where rows explode.

**Never do this in production:**
- `df.collect()` / `toPandas()` on large data (driver OOM)
- `df.count()` everywhere for logging (each one is a full job)
- Python UDFs where a built-in function exists (slow serialisation). Check `pyspark.sql.functions` first.
- Loops that call `withColumn` 200 times (use a single `select`)

---

## How this connects to HMS→UC

- `DEEP CLONE` and `CTAS` migrations are Spark jobs, and big tables need the right cluster size.
- Validation (`EXCEPT`, hashing, counts) on large tables is Spark, so knowing shuffles makes it fast.
- Code breakages to look for: RDD/`sparkContext` usage, `input_file_name()`, Hive SerDe tables, `spark.read.load("/mnt/...")`, 2-level `saveAsTable("db.tbl")`, and custom JARs/init scripts on Standard access mode.

## Hands-on

Use `samples.tpch.*` / `samples.nyctaxi.trips` in Databricks, or generate data locally with `spark.range(10_000_000)`.

1. Run a filter + groupBy and open the Spark UI. Count the jobs and stages, and find the `Exchange`.
2. Join `orders` to `customer` with and without `broadcast()`. Compare the plans and durations.
3. Create skew: `spark.range(10_000_000).withColumn("k", F.when(F.rand() < 0.7, 0).otherwise((F.rand()*1000).cast("int")))`. groupBy `k`, then find the skewed task in the UI.
4. `repartition(1)` vs `repartition(200)` vs `coalesce(8)`. Write each to Delta and look at the number and size of files.
5. Read a CSV with a deliberately bad row in PERMISSIVE vs FAILFAST mode, and inspect `_corrupt`.
6. Cache a DataFrame used 3 times and compare with no cache. Then see what happens on serverless.

## Build

**`orders_daily` PySpark job:** read raw CSV orders + customer JSON → apply an explicit schema → dedupe with a window → join with a broadcast dim → aggregate daily revenue per country → write to Delta, partitioned/clustered by date. Write a **README explaining the jobs/stages/shuffles you observed**, with Spark UI screenshots.

## Troubleshooting you must be able to handle

| Error / symptom | Investigate |
|---|---|
| `java.lang.OutOfMemoryError` on **driver** | `collect()`, `toPandas()`, broadcasting something huge, too many small files listed |
| OOM / "executor lost" on **executors** | Skew, huge partitions, too few shuffle partitions, wide rows, exploding joins |
| `AnalysisException: [UNRESOLVED_COLUMN]` | Column name/case/alias, schema changed upstream |
| `Py4JJavaError` | It's a wrapper. **Scroll down to the "Caused by:"** for the real error |
| One task runs forever | Skew. Check the max vs median task time |
| Job slow, lots of spill | Partitions too large → more shuffle partitions, or a bigger memory per core |
| `[PATH_NOT_FOUND]` | Wrong path, or no permission (in UC this often surfaces differently, see Phase 7) |

## After this phase you should be able to explain

- [ ] Driver vs executor, and what runs where
- [ ] Job vs stage vs task, and what creates a new stage
- [ ] Lazy evaluation, and why `explain()` is useful
- [ ] Narrow vs wide transformations
- [ ] Broadcast vs sort-merge join, and when Spark picks each
- [ ] What data skew is, how you'd spot it in the UI, and 3 ways to fix it
- [ ] When caching helps and when it hurts

## Beginner vs experienced

| Beginner | Experienced |
|---|---|
| Writes PySpark that produces the right answer | Predicts the number of stages/shuffles before running; reads physical plans |
| Increases cluster size when slow | Finds the slow stage and fixes the cause (skew, spill, small files) |
| Uses UDFs freely | Uses built-ins, and knows the cost of Python ↔ JVM serialisation |

Exercises: [exercises/pyspark-exercises.md](../exercises/pyspark-exercises.md)

## Interview questions

1. Explain Spark architecture: driver, executors, cluster manager.
2. What is lazy evaluation? Why is it useful?
3. Narrow vs wide transformations, with examples.
4. What triggers a shuffle? Why is it expensive?
5. `repartition` vs `coalesce`?
6. How does a broadcast join work? When would it fail?
7. What is data skew, and how do you handle it?
8. What is AQE and what does it do?
9. Your job failed with executor OOM. How do you investigate?
10. Why avoid Python UDFs?
