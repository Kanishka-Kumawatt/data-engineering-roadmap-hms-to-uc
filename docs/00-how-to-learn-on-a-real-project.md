# 00 — How to Learn While Working on a Real Project

> Read this before Phase 1. It explains how to use your HMS→UC project as a classroom without endangering it.

---

## 1. Your unfair advantage

Most people learn Data Engineering from tutorials with clean CSVs and no consequences. You have a **live migration**, with real tables, real permissions, real broken views, real deadlines and real senior engineers nearby. That's worth more than any course, **if you use it deliberately**.

The trap is to spend 3 months running scripts someone else wrote without understanding them. This roadmap is meant to stop that from happening.

### The three-question habit

For every project task, write down:

1. **What** am I doing? (e.g. "Running SYNC on schema `sales` in dry-run mode")
2. **Why** this way? (e.g. "The tables are external Delta on ADLS, so the data can stay where it is and only the metadata moves")
3. **What could go wrong, and how would I know?** (e.g. "The storage path isn't covered by an External Location → the SYNC status shows a failure → check `SHOW EXTERNAL LOCATIONS`")

If you can't answer #2 or #3, that's your learning topic for the week.

---

## 2. The engineering thought process (used in every phase)

```
 ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
 │ 1 Requirement│──▶│ 2 Analyse &  │──▶│ 3 Design     │──▶│ 4 Build      │
 │   received   │   │   ask Qs     │   │   solution   │   │   (code)     │
 └──────────────┘   └──────────────┘   └──────────────┘   └──────┬───────┘
                                                                  ▼
 ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
 │ 9 Improve    │◀──│ 8 Fails? Fix │◀──│ 7 Monitor    │◀──│ 5 Test       │
 │              │   │   + prevent  │   │              │   │              │
 └──────────────┘   └──────────────┘   └──────▲───────┘   └──────┬───────┘
                                              │                  ▼
                                       ┌──────┴───────┐   ┌──────────────┐
                                       │ 6b Deploy    │◀──│ 6a Commit,PR │
                                       │              │   │   review     │
                                       └──────────────┘   └──────────────┘
```

| Step | Questions a good engineer asks |
|---|---|
| **1 Requirement** | Who is asking, and who consumes the output? What decision does it support? What does "done" look like? What's the deadline / SLA? |
| **2 Analyse** | Where is the source? How big is it, and how often does it change? Is there a key? Are there nulls or duplicates? How late can data arrive? Who owns the source? |
| **3 Design** | Batch or streaming? Full or incremental? Which layer? Managed or external table? Who needs access? How do I re-run it safely? |
| **4 Build** | Is it parameterised? Is it idempotent (safe to re-run)? Is the logic in testable functions? |
| **5 Test** | Do the unit tests pass? Do row counts reconcile? Does it handle empty input, duplicates, late data and schema change? |
| **6 Commit/Deploy** | Is the PR small and well described? Is config per-environment? Are there secrets in code? (There should never be.) |
| **7 Monitor** | How will I know it failed? How will I know it *succeeded with wrong data*? Who gets alerted? |
| **8 Fail** | What does the error *actually* say? What changed since the last success? Can I reproduce it in dev? |
| **9 Improve** | Is it too slow, too expensive or too fragile? |

**The same loop in migration terms:** Inventory → Assess → Plan → Migrate (dev) → Validate → Fix → Migrate (prod) → Validate → Cut over → Monitor → Decommission HMS.

---

## 3. Setting up your practice environments

You need **somewhere safe to break things**. Use all three.

### A. Local PySpark + Delta (free, offline, and good for learning HMS)

When you run Spark locally with Hive support turned on, Spark **creates a real embedded (Derby) Hive Metastore** on your laptop, so you can *see* what HMS is: a database of table definitions pointing to files.

```powershell
# Install Java 17 first (Microsoft Build of OpenJDK / Temurin), then:
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install "pyspark==3.5.*" "delta-spark==3.2.*" pytest chispa
```

> **Windows note:** some Spark file operations on Windows need `winutils.exe` and `HADOOP_HOME`. If local Spark gives you trouble, use **WSL2 (Ubuntu)**. It's smoother, and most production DE tooling assumes Linux.

```python
from delta import configure_spark_with_delta_pip
from pyspark.sql import SparkSession

builder = (SparkSession.builder.appName("local-lab")
           .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
           .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
           .enableHiveSupport())          # creates ./metastore_db (Derby HMS) + ./spark-warehouse
spark = configure_spark_with_delta_pip(builder).getOrCreate()

spark.sql("CREATE DATABASE IF NOT EXISTS sales")
spark.range(5).write.format("delta").mode("overwrite").saveAsTable("sales.numbers")
spark.sql("DESCRIBE EXTENDED sales.numbers").show(truncate=False)   # look at 'Location'
```

Now look in your folder: `metastore_db/` holds the **metadata**, and `spark-warehouse/sales.db/numbers/` holds the **data** (Parquet files + `_delta_log/`). **Metadata and data are separate things.** That's the most important idea in the whole migration.

### B. Databricks Free Edition (free, Unity Catalog enabled)

Sign up for **Databricks Free Edition** (the successor to Community Edition). It's serverless and UC-enabled, so you can practise catalogs, schemas, grants, volumes, jobs, SQL warehouses, Delta and Git folders. It has quotas and doesn't offer every feature (classic clusters, account console, or a legacy `hive_metastore` to migrate *from* may not be available), so use local Spark for HMS concepts and the project's dev workspace for real HMS→UC practice.

### C. The project's DEV workspace (with permission)

Ask your lead: *"Can I have a sandbox schema in dev where I can practise migrations without touching project tables?"* Most leads say yes, because it makes you more useful. **Never practise in prod.**

---

## 4. Your personal error log (start it today)

Create `notes/error-log.md` in your fork. Every error gets an entry:

```markdown
### 2026-10-12 — [TABLE_OR_VIEW_NOT_FOUND] in daily_sales job
- **Where:** Job `daily_sales_agg`, task `build_gold`, dev workspace
- **Full error:** `[TABLE_OR_VIEW_NOT_FOUND] The table or view `sales`.`orders` cannot be found...`
- **What I thought first:** The table was deleted
- **Actual cause:** The job ran on UC compute whose default catalog is `main`, so `sales.orders`
  resolved to `main.sales.orders` (doesn't exist). The table lives in `hive_metastore.sales.orders`
  and was migrated to `sales_dev.sales.orders`.
- **Fix:** Fully qualified 3-level name, with the catalog passed as a job parameter
- **Prevention:** Scan code for 2-level names before migration; always use `catalog.schema.table`
- **Time to fix:** 40 min. Next time: 5 min
```

After 3 months you'll have 30–60 entries, and you'll fix repeat problems in minutes instead of hours.

---

## 5. How to ask for help (and get it)

> **Trying to:** Migrate `finance.gl_entries` from HMS to UC with SYNC.
> **Expected:** Table appears as `fin_prod.finance.gl_entries`.
> **Happened:** SYNC dry run returns a location-overlap status *(paste the exact message)*.
> **Tried:** `SHOW EXTERNAL LOCATIONS`, and the path is covered. `DESCRIBE DETAIL` shows location `.../finance/gl_entries`.
> **My guess:** Another UC table already uses this path?
> **Question:** What's the best way to find UC tables by storage location?

Try for **20–30 minutes** first, then ask. Don't wait two days.

---

## 6. Using AI assistants responsibly

- ✅ Use them to explain errors, draft tests, and explain unfamiliar code.
- ✅ **Always run and verify** what they produce. Check UC and permission behaviour against current Databricks docs, because features change quickly.
- ❌ Never paste client data, credentials or internal names into tools your company hasn't approved.
- ❌ Don't commit code you can't explain line by line.

---

## 7. Weekly rhythm

| When | What |
|---|---|
| Mon | Theory for the week (≈1.5 h) |
| Tue–Thu | Hands-on exercises (≈1–1.5 h/day) |
| Fri | Mini-project + commit + update PROGRESS.md (≈2 h) |
| Every workday | The three-question habit + error log (≈10 min) |

Full details: [schedule/daily-weekly-practice-plan.md](../schedule/daily-weekly-practice-plan.md).
