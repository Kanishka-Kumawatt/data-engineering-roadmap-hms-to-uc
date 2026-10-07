# Phase 6 — Delta Lake

**Weeks:** 6–7 · **Time:** ~14 h (4 h theory, 10 h hands-on)
**Goal:** Understand what Delta does under the hood, and use MERGE, time travel, schema evolution and maintenance commands confidently.

> **Mentor note:** Open the `_delta_log` folder and read the JSON files. Once you've seen that a Delta table is just Parquet files plus a transaction log, everything else (time travel, ACID, VACUUM, CLONE, even why SYNC works) makes sense.

---

## 1. What Delta Lake is

**Simply:** Delta = **Parquet data files + a `_delta_log/` transaction log** that records every change as an ordered, atomic commit.

```
orders/
├── _delta_log/
│   ├── 00000000000000000000.json   ← commit 0: CREATE, schema, add file A, B
│   ├── 00000000000000000001.json   ← commit 1: add file C (append)
│   ├── 00000000000000000002.json   ← commit 2: remove B, add D (update)
│   └── 00000000000000000010.checkpoint.parquet  ← periodic snapshot of the log
├── part-0000-A.snappy.parquet
├── part-0001-B.snappy.parquet      ← logically removed at v2, physically present until VACUUM
├── part-0002-C.snappy.parquet
└── part-0003-D.snappy.parquet
```

Readers read the log to know **which files make up the current version**. That's the whole trick.

## 2. Why Delta (vs plain Parquet/CSV)

| Problem with plain files | Delta solution |
|---|---|
| Job fails halfway → partial, corrupt output | **ACID**: the commit is all-or-nothing |
| Two writers corrupt each other | **Optimistic concurrency** with conflict detection |
| Someone writes a string into an int column | **Schema enforcement** |
| Need a new column | **Schema evolution** (opt-in) |
| "What did this table look like yesterday?" | **Time travel** |
| Can't UPDATE/DELETE files | **UPDATE, DELETE, MERGE** |
| Millions of tiny files are slow | **OPTIMIZE**, auto-compaction, liquid clustering |

## 3. Core operations, with practical examples

```sql
USE learn.retail;

CREATE OR REPLACE TABLE silver_customers (
  customer_id INT NOT NULL, name STRING, city STRING, email STRING, updated_at TIMESTAMP
) USING DELTA;

-- ACID + history
INSERT INTO silver_customers VALUES (1,'Asha','Mumbai','asha@x.com', current_timestamp());
UPDATE silver_customers SET city = 'Pune' WHERE customer_id = 1;
DELETE FROM silver_customers WHERE customer_id = 99;
DESCRIBE HISTORY silver_customers;                 -- every version, operation, user, metrics
DESCRIBE DETAIL  silver_customers;                 -- location, numFiles, sizeInBytes, format

-- Time travel
SELECT * FROM silver_customers VERSION AS OF 0;
SELECT * FROM silver_customers TIMESTAMP AS OF '2026-10-01';
RESTORE TABLE silver_customers TO VERSION AS OF 1;  -- undo a bad load
```

### Schema enforcement vs evolution
```python
# Enforcement: this FAILS because of an extra column 'phone'
new_df.write.format("delta").mode("append").saveAsTable("learn.retail.silver_customers")
# -> [DELTA_METADATA_MISMATCH] / schema mismatch error

# Evolution: explicitly opt in
new_df.write.format("delta").mode("append").option("mergeSchema", "true").saveAsTable("learn.retail.silver_customers")
```
Opt in deliberately. **Silent schema evolution in Silver/Gold is a common production bug source.**

### MERGE: the upsert workhorse
```sql
MERGE INTO silver_customers AS t
USING (
  -- ALWAYS dedupe the source first: one row per key
  SELECT * FROM bronze_customers_increment
  QUALIFY ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY _ingested_at DESC) = 1
) AS s
ON t.customer_id = s.customer_id
WHEN MATCHED AND s.updated_at > t.updated_at THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *
WHEN NOT MATCHED BY SOURCE AND t.is_active = true THEN UPDATE SET t.is_active = false;  -- optional: soft-delete
```
**The #1 MERGE failure:** `[DELTA_MULTIPLE_SOURCE_ROW_MATCHING_TARGET_ROW_IN_MERGE]`. More than one source row matched the same target row. Fix: dedupe the source.

### Partitioning, OPTIMIZE, Z-ORDER, liquid clustering
- **Partitioning** (`PARTITIONED BY (order_date)`): only for **large** tables (≳1 TB) with a **low-cardinality**, commonly filtered column. Over-partitioning (e.g. by `customer_id`) creates millions of tiny files, a classic HMS-era anti-pattern you'll find in migrations.
- **OPTIMIZE:** compacts small files into large ones. `OPTIMIZE t ZORDER BY (customer_id)` co-locates data for skipping.
- **Liquid clustering** (`CLUSTER BY (col)`): the modern replacement for partitioning + Z-ORDER, and the recommended choice for new tables. Clustering keys can be changed later.
- **Predictive optimization:** on UC managed tables, Databricks can run OPTIMIZE/VACUUM/ANALYZE automatically.

### VACUUM
```sql
VACUUM silver_customers RETAIN 168 HOURS;   -- default retention is 7 days
```
It deletes data files no longer referenced by versions within the retention window. **After VACUUM you can't time travel past the retention window.** Never reduce retention without understanding the consequences (and long-running readers can break).

### CLONE (very relevant to your migration)
```sql
CREATE TABLE uc_cat.sales.orders DEEP CLONE hive_metastore.sales.orders;    -- copies data + metadata
CREATE TABLE dev.sales.orders_test SHALLOW CLONE prod.sales.orders;        -- metadata only, points to source files
```
DEEP CLONE is incremental when re-run (it copies only new or changed files), which makes it useful for **staged migration with a final sync**.

### Change Data Feed (CDF) for incremental processing
```sql
ALTER TABLE silver_customers SET TBLPROPERTIES (delta.enableChangeDataFeed = true);
SELECT * FROM table_changes('silver_customers', 5);   -- changes since version 5: insert/update_preimage/update_postimage/delete
```
Downstream jobs can read only what changed instead of the full table.

## 4. Slowly Changing Dimensions with Delta

- **SCD Type 1:** overwrite (MERGE `UPDATE SET *`). No history.
- **SCD Type 2:** keep history with `effective_from`, `effective_to` and `is_current`.

```sql
-- SCD2 in one MERGE using the "staged updates" trick
MERGE INTO dim_customer t
USING (
  SELECT s.customer_id AS merge_key, s.* FROM updates s
  UNION ALL
  -- rows whose attributes changed: insert a new version (merge_key NULL => NOT MATCHED)
  SELECT NULL AS merge_key, s.* FROM updates s
  JOIN dim_customer t ON s.customer_id = t.customer_id
  WHERE t.is_current AND (s.city <> t.city OR s.email <> t.email)
) s
ON t.customer_id = s.merge_key AND t.is_current
WHEN MATCHED AND (s.city <> t.city OR s.email <> t.email) THEN
  UPDATE SET is_current = false, effective_to = s.updated_at
WHEN NOT MATCHED THEN
  INSERT (customer_id, city, email, effective_from, effective_to, is_current)
  VALUES (s.customer_id, s.city, s.email, s.updated_at, NULL, true);
```
(Use NULL-safe comparisons, `NOT (a <=> b)`, in real code.) Lakeflow Declarative Pipelines also offer `AUTO CDC` (formerly `APPLY CHANGES`) with SCD2 built in.

## 5. Incremental processing patterns

| Pattern | How |
|---|---|
| **Watermark/high-water mark** | Store `max(updated_at)` processed; next run reads `> last_watermark` |
| **Auto Loader** | Tracks which files have been ingested (`cloudFiles`), exactly once |
| **Change Data Feed** | Read changes between versions |
| **Streaming with `availableNow`** | Process everything new since the last checkpoint, then stop |

Make every incremental job **idempotent**: re-running the same window gives the same result (MERGE, or `replaceWhere` overwrite for a date range).

---

## How this connects to HMS→UC

- **Delta tables migrate cleanly**, because the log carries the schema and history. **Parquet/CSV/Hive SerDe tables** need converting (`CONVERT TO DELTA`, CTAS) or special handling.
- Migration choice depends on Delta: `SYNC` (external Delta, metadata only), `DEEP CLONE` (copy data with history semantics), CTAS (copy data, no history).
- **History:** DEEP CLONE does *not* copy the table history. The UC table starts at its own version 0. CTAS starts fresh too. SYNC of an external table keeps the same `_delta_log`, so history is preserved. Know this when someone asks "can we still time travel after migration?"
- Validate with `DESCRIBE DETAIL` (numFiles, size) and `DESCRIBE HISTORY` on source vs target.
- **Don't VACUUM HMS source tables aggressively during migration.** You may need them for rollback.

## Hands-on

1. Create a Delta table locally. Do insert/update/delete/merge, then open every `_delta_log/*.json` file and explain each `add`/`remove` action.
2. Time travel: corrupt the table with a bad UPDATE, then `RESTORE`.
3. Trigger schema enforcement, then evolution with `mergeSchema`.
4. Trigger the MERGE duplicate-source error, then fix it.
5. Write 500 tiny files (`repartition(500)`), check `DESCRIBE DETAIL numFiles`, then `OPTIMIZE` and check again.
6. DEEP CLONE vs SHALLOW CLONE. Delete a source file in the shallow case (local only!) and see what breaks.
7. Implement SCD2 for `customers` with 3 batches of changes.

## Build

**Customer SCD2 dimension:** daily batches (3 CSVs) → Bronze append → Silver SCD1 (latest) → Gold `dim_customer` SCD2. Include a test notebook that asserts exactly one `is_current` row per customer and no overlapping date ranges.

## Troubleshooting

| Error | Cause / fix |
|---|---|
| `DELTA_MULTIPLE_SOURCE_ROW_MATCHING_TARGET_ROW_IN_MERGE` | Duplicate keys in the source → dedupe |
| Schema mismatch on write | New/renamed/type-changed column → decide: evolve, cast or reject |
| `ConcurrentAppendException` / `ConcurrentModificationException` | Two jobs writing the same partitions/files → serialise, partition-separate, or use row-level concurrency features |
| `VersionNotFound` / files missing on time travel | VACUUM removed them |
| `FileNotFoundException` reading a table | Files deleted outside Delta, or VACUUM while a reader was running → `FSCK REPAIR TABLE` (last resort) |
| Very slow reads | Small files → OPTIMIZE / clustering; check `numFiles` |

## After this phase you should be able to explain

- [ ] How the transaction log provides ACID and time travel
- [ ] Schema enforcement vs evolution, and when to allow evolution
- [ ] How MERGE works, and the duplicate-source failure
- [ ] OPTIMIZE vs VACUUM vs Z-ORDER vs liquid clustering
- [ ] DEEP vs SHALLOW CLONE, and when each fits a migration
- [ ] SCD1 vs SCD2
- [ ] How you make an incremental load idempotent

## Beginner vs experienced

| Beginner | Experienced |
|---|---|
| Uses MERGE from a template | Designs merge conditions, handles late/out-of-order data and deletes |
| Partitions by date out of habit | Chooses liquid clustering or no partitioning based on size and query patterns |
| Knows VACUUM deletes files | Knows the retention/time-travel/reader trade-offs and recovery options |

## Interview questions

1. What is Delta Lake, and how does it provide ACID on object storage?
2. What does `_delta_log` contain?
3. Schema enforcement vs schema evolution?
4. How does MERGE work? What's a common failure?
5. OPTIMIZE vs VACUUM?
6. What is time travel? What limits it?
7. How would you implement SCD Type 2?
8. Partitioning vs Z-ordering vs liquid clustering?
9. DEEP CLONE vs SHALLOW CLONE?
10. How do you make incremental loads idempotent?
