# Phase 8 — Data Pipeline Development: From Requirement to Production

**Weeks:** 9–11 · **Time:** ~26 h (6 h theory, 20 h hands-on)
**Goal:** Take a business requirement and deliver a production-grade Bronze → Silver → Gold pipeline: designed, coded, tested, deployed, scheduled and monitored.

> **Mentor note:** This phase brings everything together. Follow along with a single worked example ("Daily Sales Performance") and build it yourself. It becomes the core of your capstone. Notice how much of the work happens **before** any code: questions, analysis, design. That's normal, and it's what experienced engineers spend their time on.

---

## Step 0 — The requirement you receive

> **JIRA DE-142:** *"Sales leadership needs a daily dashboard of revenue, orders and average order value by store and product category, refreshed by 7 a.m. Dubai time. Data comes from the POS system (orders) and the product master (CSV from merchandising). Needs to be in Unity Catalog so the BI team can access it."*

It looks simple. It's actually full of ambiguity.

## Step 1 — Requirements gathering: the questions you ask

| Area | Questions |
|---|---|
| **Business meaning** | What is "revenue": gross or net of discounts, refunds, tax? Which time zone defines "a day"? Do cancelled orders count? |
| **Consumers** | Who uses it: dashboard only, or also analysts via SQL? Which BI tool? Which groups need access? Is any PII involved? |
| **Freshness / SLA** | Ready by 7 a.m. Dubai. What happens if it's late? Who gets told? |
| **History** | How far back? Is a backfill needed? |
| **Sources** | How do we get POS data (DB extract, files, API, CDC)? How often? Who owns it? Volumes? |
| **Changes** | Can orders be updated after creation (status changes, refunds)? How late can they arrive? |
| **Quality** | What should happen with bad records: drop, quarantine or fail? |
| **Acceptance** | How will we know the numbers are right? Is there an existing report to reconcile against? |

Write the answers down as a short **design doc** (template below). **This is the most underrated skill in DE.**

## Step 2 — Source analysis (profile before you design)

```sql
-- On a sample of the source: volume, keys, nulls, ranges, duplicates, late data
SELECT COUNT(*) rows, COUNT(DISTINCT order_id) distinct_ids,
       SUM(CASE WHEN store_id IS NULL THEN 1 ELSE 0 END) null_store,
       MIN(order_ts) min_ts, MAX(order_ts) max_ts,
       MAX(datediff(_ingested_at, order_ts)) max_lateness_days
FROM bronze_orders;
```
Findings for our example: ~2M orders/day as JSON files every 15 minutes; `order_id` is unique per *version* (updates resend the full order with a newer `updated_at`); orders can arrive up to 3 days late; 0.1% are missing `store_id`. Product master is a daily full CSV snapshot.

## Step 3 — Design

```
POS JSON files ──▶ /Volumes/retail_<env>/landing/pos_orders/   (external volume / landing zone)
Product CSV    ──▶ /Volumes/retail_<env>/landing/products/

[Bronze]  retail_<env>.bronze.pos_orders        Auto Loader, append-only, + _ingested_at, _source_file
          retail_<env>.bronze.products          daily snapshot append, + _snapshot_date

[Silver]  retail_<env>.silver.orders            typed, deduped (latest per order_id), MERGE on order_id,
                                                quality rules, bad rows → silver.orders_quarantine
          retail_<env>.silver.products          SCD2 (category changes tracked)

[Gold]    retail_<env>.gold.fct_sales_daily     grain: date × store × category; rebuilt for affected dates
          retail_<env>.gold.dim_store, dim_product

[Ops]     retail_<env>.ops.pipeline_runs        run audit (rows in/out, status, duration)
          retail_<env>.ops.dq_results           data quality results per run
```

Design decisions, and why:
- **Incremental Bronze** via Auto Loader (exactly-once file tracking).
- **Silver MERGE** because orders are updated. Deduplicate inside the batch first.
- **Gold incremental by affected dates:** find the dates touched in this batch (including late ones) and recompute only those (`replaceWhere` or MERGE). That keeps it idempotent and lets it handle late data.
- **Quarantine, don't drop:** bad rows go to a table with a reason column.
- **Parameterised by env** (catalog) and `run_date` (for backfills).
- **Managed UC tables, liquid clustering** on `order_date`.
- **Grants:** `grp_bi_readers` → `SELECT` on `gold` only. Pipeline SP → `MODIFY` on all three schemas.

### Design doc template (keep it to 1–2 pages)
```markdown
# DE-142 Daily Sales Performance — Design
## Problem & consumers
## Definitions (revenue, day, cancelled orders...)
## Sources (owner, format, frequency, volume, keys, lateness)
## Architecture (diagram + tables per layer with grain & keys)
## Incremental strategy & idempotency
## Data quality rules & handling (fail / quarantine / warn)
## Security (catalog/schema, grants, PII)
## Scheduling, SLA, alerting
## Testing & acceptance criteria
## Risks & open questions
```

## Step 4 — Build

### Repository layout
```
retail-pipeline/
├── databricks.yml                 # Asset Bundle: jobs + targets dev/qa/prod (Phase 12)
├── resources/daily_sales_job.yml
├── conf/{dev,qa,prod}.yaml        # non-secret config
├── src/retail_pipeline/
│   ├── __init__.py
│   ├── config.py                  # load config, build table names
│   ├── bronze.py                  # ingest functions
│   ├── silver.py                  # clean/dedupe/merge (pure transforms + write)
│   ├── gold.py                    # aggregates
│   ├── quality.py                 # DQ rules engine
│   └── audit.py                   # run logging
├── notebooks/                     # thin entry points per task
│   ├── 01_bronze.py  02_silver.py  03_gold.py  04_dq_gate.py
├── tests/
│   ├── unit/test_silver.py  test_gold.py  test_quality.py
│   └── integration/test_pipeline_end_to_end.py
└── README.md / RUNBOOK.md
```

### Bronze: ingest (Auto Loader)
```python
def ingest_pos_orders(spark, cfg):
    return (spark.readStream.format("cloudFiles")
            .option("cloudFiles.format", "json")
            .option("cloudFiles.schemaLocation", f"{cfg.checkpoint_root}/bronze_pos_orders/schema")
            .option("cloudFiles.schemaEvolutionMode", "rescue")      # unexpected fields → _rescued_data
            .load(f"{cfg.landing_root}/pos_orders/")
            .select("*", F.current_timestamp().alias("_ingested_at"),
                         F.col("_metadata.file_path").alias("_source_file"))
            .writeStream
            .option("checkpointLocation", f"{cfg.checkpoint_root}/bronze_pos_orders")
            .trigger(availableNow=True)                              # incremental batch
            .toTable(cfg.table("bronze", "pos_orders")))
```

### Silver: transform, which keeps logic pure and testable
```python
from pyspark.sql import DataFrame, functions as F, Window as W

def clean_orders(df: DataFrame) -> DataFrame:
    """Type, standardise, and flag invalid rows. Pure: no reads/writes."""
    return (df.select(
                F.col("order_id").cast("bigint"),
                F.col("store_id").cast("int"),
                F.col("product_id").cast("int"),
                F.col("quantity").cast("int"),
                F.col("unit_price").cast("decimal(12,2)"),
                F.upper(F.trim("status")).alias("status"),
                F.to_timestamp("order_ts").alias("order_ts"),
                F.to_timestamp("updated_at").alias("updated_at"),
                "_ingested_at", "_source_file")
            .withColumn("order_date", F.to_date(F.from_utc_timestamp("order_ts", "Asia/Dubai")))
            .withColumn("_dq_issue",
                F.when(F.col("order_id").isNull(), "NULL_ORDER_ID")
                 .when(F.col("store_id").isNull(), "NULL_STORE_ID")
                 .when(F.col("quantity") <= 0, "NON_POSITIVE_QTY")
                 .otherwise(None)))

def latest_per_key(df: DataFrame, key: str = "order_id", order_col: str = "updated_at") -> DataFrame:
    w = W.partitionBy(key).orderBy(F.col(order_col).desc(), F.col("_ingested_at").desc())
    return df.withColumn("_rn", F.row_number().over(w)).filter("_rn = 1").drop("_rn")
```
```python
def upsert_silver_orders(spark, batch_df, cfg):
    cleaned = clean_orders(batch_df)
    good = latest_per_key(cleaned.filter("_dq_issue IS NULL")).drop("_dq_issue")
    cleaned.filter("_dq_issue IS NOT NULL").write.mode("append").saveAsTable(cfg.table("silver", "orders_quarantine"))

    good.createOrReplaceTempView("src")
    spark.sql(f"""
      MERGE INTO {cfg.table('silver','orders')} t USING src s ON t.order_id = s.order_id
      WHEN MATCHED AND s.updated_at > t.updated_at THEN UPDATE SET *
      WHEN NOT MATCHED THEN INSERT *""")
    return good.select("order_date").distinct()     # affected dates → Gold
```

### Gold: recompute affected dates only (idempotent)
```python
def build_fct_sales_daily(spark, cfg, affected_dates: list):
    if not affected_dates:
        return
    dates_sql = ", ".join(f"DATE'{d}'" for d in affected_dates)
    df = spark.sql(f"""
      SELECT o.order_date, o.store_id, p.category,
             SUM(o.quantity * o.unit_price)                      AS revenue,
             COUNT(DISTINCT o.order_id)                          AS orders,
             SUM(o.quantity * o.unit_price) / COUNT(DISTINCT o.order_id) AS avg_order_value
      FROM {cfg.table('silver','orders')} o
      JOIN {cfg.table('silver','products')} p
        ON o.product_id = p.product_id AND p.is_current
      WHERE o.status = 'COMPLETED' AND o.order_date IN ({dates_sql})
      GROUP BY ALL""")
    (df.write.mode("overwrite")
       .option("replaceWhere", f"order_date IN ({dates_sql})")
       .saveAsTable(cfg.table("gold", "fct_sales_daily")))
```
(Production refinement: join the product version valid at order time (SCD2 range join) rather than `is_current`. Ask the business which one they want. That's a requirement question.)

### Data quality gate
```python
RULES = [
  ("gold_not_empty",      "SELECT COUNT(*) = 0 FROM {gold} WHERE order_date = '{d}'", "FAIL"),
  ("no_negative_revenue", "SELECT COUNT(*) > 0 FROM {gold} WHERE revenue < 0",          "FAIL"),
  ("quarantine_rate",     "SELECT (SELECT COUNT(*) FROM {q} WHERE _ingested_at >= current_date()) > 1000", "WARN"),
]
# each query returns TRUE when the rule is violated; FAIL → raise (job fails, alert fires), WARN → log + notify
```

### Logging & audit
```python
log.info("silver.orders merged: in=%d good=%d quarantined=%d dates=%s", n_in, n_good, n_bad, dates)
write_run_audit(spark, cfg, job="daily_sales", task="silver", status="SUCCESS", rows_in=n_in, rows_out=n_good)
```

## Step 5 — Test (details in Phase 11)
- **Unit:** `clean_orders` flags each bad case; `latest_per_key` keeps the newest; Gold math on a tiny DataFrame.
- **Integration:** run the whole job in dev on a fixed sample; assert the counts and totals against hand-calculated values.
- **Idempotency:** run twice with the same input and expect the same Gold output.
- **Late data:** add a 3-day-old order and check that only that date's Gold row changes.
- **Reconciliation:** compare Gold totals with the existing finance report for a week (acceptance).

## Step 6 — Commit & review (Phase 10)
Branch `feature/DE-142-daily-sales` → small commits → PR with a description, test evidence and screenshots → reviewer comments → merge.

## Step 7 — Deploy & schedule (Phase 12)
Asset Bundle job: `bronze → silver → gold → dq_gate`. Schedule 05:30 Dubai. Retries: 2 on bronze/silver. Timeout: 60 min. Run as `sp_retail_pipeline_<env>`. Notifications on failure and on duration > 45 min.

## Step 8 — Monitor
- Job alerts (failure, duration).
- `ops.pipeline_runs`: rows per run (sudden drops = upstream issue).
- **Freshness check:** `MAX(order_date)` in Gold = yesterday by 7 a.m.
- **Volume anomaly:** today's orders < 50% of the 7-day average → warn.
- A Databricks SQL dashboard on `ops.*` tables, and SQL alerts.

## Step 9 — When it fails (Phase 14)
Read the error → which task → what changed → reproduce in dev with the same `run_date` → fix → PR → deploy → **repair run** → verify Gold → notify stakeholders → error log + prevention.

## Step 10 — Improve
Performance (clustering, file sizes), cost (serverless vs job cluster, schedule), robustness (more DQ rules), and documentation (table comments, column descriptions, tags).

---

## How this connects to HMS→UC

Every pipeline you migrate is a pipeline like this one, built under HMS conventions. When you migrate it, you're effectively doing steps 4–8 again: change names/paths, re-test, redeploy and re-monitor. Building one from scratch makes you much better at migrating them, because you'll recognise which parts are fragile.

## Practice & build

Build the full Daily Sales pipeline above on Free Edition, with the synthetic data generator in [capstone/starter/scripts/generate_data.py](../capstone/starter/scripts/generate_data.py). Then do the variations in [exercises/hands-on-projects.md](../exercises/hands-on-projects.md).

## Troubleshooting drills
1. Feed a duplicate order in one batch → MERGE error? (No, because you dedupe. Remove the dedupe and see.)
2. Feed a file with a new column → `_rescued_data`. Decide how to handle it.
3. Feed a late order (3 days old) → is the right Gold date updated?
4. Delete the checkpoint and re-run → what happens to Bronze? (Duplicates! Learn why.)
5. Make the product CSV arrive late → what does Gold show? Should the job wait, fail or proceed?

## After this phase you should be able to explain
- [ ] The questions you ask before building a pipeline
- [ ] Why Bronze is append-only and Silver uses MERGE
- [ ] How the pipeline handles duplicates, late data, bad records and re-runs
- [ ] How config/parameters let the same code run in dev/qa/prod
- [ ] What you monitor beyond "did the job succeed"

## Beginner vs experienced

| Beginner | Experienced |
|---|---|
| Starts coding from the ticket text | Writes a design doc and resolves definitions first |
| Full reload every run | Incremental, idempotent, late-data aware |
| "It ran" = done | Done = tested, reconciled, monitored, documented, handed over |

## Interview questions
1. Walk me through how you'd build a pipeline from a business requirement.
2. How do you handle late-arriving data?
3. How do you make a pipeline idempotent?
4. How do you handle bad records?
5. What do you monitor in a production pipeline?
6. Full load vs incremental: when do you pick each?
7. How do you backfill historical data safely?
