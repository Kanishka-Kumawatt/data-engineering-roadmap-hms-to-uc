# Phase 11 — Testing and Data Quality

**Weeks:** 11–12 · **Time:** ~14 h (3 h theory, 11 h hands-on)
**Goal:** Prove your code and your data are correct, automatically, every run. In a migration, that's how you prove nothing was lost or changed.

> **Mentor note:** "It ran successfully" is the most dangerous phrase in data engineering. Jobs that succeed with wrong data cause more damage than jobs that fail, because nobody notices. Tests catch code bugs before deploy. Data quality checks catch data problems during runs. You need both.

---

## 1. The testing pyramid for data

```
              ▲  fewer, slower, more realistic
             ╱ ╲      Acceptance / reconciliation vs business reports
            ╱───╲     Integration: whole job on sample data in dev
           ╱─────╲    Data quality checks: every production run
          ╱───────╲   Unit tests: pure transformation functions (fast, many)
         ▔▔▔▔▔▔▔▔▔▔▔
```

| Type | Tests | When it runs | Tools |
|---|---|---|---|
| **Unit** | One function's logic on tiny in-memory data | Every commit (CI) | `pytest`, local SparkSession, `chispa` / `pyspark.testing.assertDataFrameEqual` |
| **Integration** | Tasks together, real tables in dev/qa | On PR merge / before release | Databricks job run in a test catalog |
| **Data quality** | The *data* meets rules | Every pipeline run | SQL checks, Delta constraints, Lakeflow expectations, Great Expectations / Soda / DQX |
| **Regression** | Output unchanged after a refactor | Before release | Compare old vs new outputs |
| **Reconciliation** | Source ↔ target agree | Migrations, critical loads | Counts, fingerprints, EXCEPT |

## 2. Unit tests (PySpark)

```python
# tests/conftest.py
import pytest
from pyspark.sql import SparkSession

@pytest.fixture(scope="session")
def spark():
    return (SparkSession.builder.master("local[1]").appName("tests")
            .config("spark.sql.shuffle.partitions", "1").getOrCreate())
```
```python
# tests/unit/test_silver.py
from datetime import datetime
from pyspark.testing import assertDataFrameEqual
from retail_pipeline.silver import latest_per_key, clean_orders

def test_latest_per_key_keeps_newest_version(spark):
    df = spark.createDataFrame([
        (1, datetime(2026, 10, 1, 10), datetime(2026, 10, 1, 10), "old"),
        (1, datetime(2026, 10, 1, 12), datetime(2026, 10, 1, 12), "new"),
        (2, datetime(2026, 10, 1, 9),  datetime(2026, 10, 1, 9),  "only"),
    ], "order_id INT, updated_at TIMESTAMP, _ingested_at TIMESTAMP, note STRING")
    result = latest_per_key(df).select("order_id", "note")
    expected = spark.createDataFrame([(1, "new"), (2, "only")], "order_id INT, note STRING")
    assertDataFrameEqual(result, expected)          # order-insensitive by default

# Note: in PySpark 3.5, assertDataFrameEqual needs pandas + pyarrow and breaks with NumPy 2.
# Two dependency-free alternatives (the capstone uses the first one):
#   assert sorted(tuple(r) for r in result.collect()) == [(1, "new"), (2, "only")]
#   chispa.assert_df_equality(result, expected, ignore_row_order=True)

def test_clean_orders_flags_non_positive_quantity(spark):
    df = spark.createDataFrame([("1", "5", "10", "0", "9.99", "completed",
                                 "2026-10-01 10:00:00", "2026-10-01 10:00:00", None, None)],
        "order_id STRING, store_id STRING, product_id STRING, quantity STRING, unit_price STRING, status STRING,"
        "order_ts STRING, updated_at STRING, _ingested_at TIMESTAMP, _source_file STRING")
    row = clean_orders(df).first()
    assert row["_dq_issue"] == "NON_POSITIVE_QTY"
    assert row["status"] == "COMPLETED"
```

**What to unit test:** dedupe, type casting, business rules (revenue definition), edge cases (NULL, empty input, duplicates, time zones at midnight), and config/naming functions.
**What not to unit test:** Spark itself, or Databricks APIs (mock them, or cover them in integration tests).

## 3. Data quality checks (every run)

| Check | SQL pattern | Typical action |
|---|---|---|
| **Schema** | Compare `df.schema` with the expected schema; `DESCRIBE` | Fail |
| **Not null** | `SELECT COUNT(*) FROM t WHERE key IS NULL` = 0 | Fail / quarantine |
| **Uniqueness** | `SELECT key, COUNT(*) FROM t GROUP BY key HAVING COUNT(*) > 1` = 0 rows | Fail |
| **Referential integrity** | `SELECT COUNT(*) FROM fct f LEFT ANTI JOIN dim d ON f.fk = d.pk` = 0 | Warn / unknown member |
| **Accepted values** | `status NOT IN ('COMPLETED','CANCELLED','PENDING')` = 0 | Quarantine |
| **Range** | `amount < 0 OR amount > 1e6` | Warn |
| **Row count / volume** | Today vs 7-day average within ±50% | Warn |
| **Freshness** | `MAX(event_ts) >= now() - INTERVAL 1 DAY` | Fail / alert |
| **Reconciliation** | Source count = Bronze count for the batch | Fail |

### Enforced by Delta
```sql
ALTER TABLE silver.orders ALTER COLUMN order_id SET NOT NULL;
ALTER TABLE silver.orders ADD CONSTRAINT positive_qty CHECK (quantity > 0);  -- writes violating it FAIL
```

### Lakeflow Declarative Pipelines expectations (if your team uses them)
```sql
CREATE OR REFRESH STREAMING TABLE silver_orders (
  CONSTRAINT valid_id  EXPECT (order_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT valid_qty EXPECT (quantity > 0)         ON VIOLATION FAIL UPDATE
) AS SELECT * FROM STREAM(bronze_orders);
```

### A tiny reusable DQ framework (put this in your capstone)
```python
from dataclasses import dataclass

@dataclass
class Rule:
    name: str
    sql: str            # returns ONE integer: number of violating rows
    severity: str       # "FAIL" | "WARN"

def run_rules(spark, rules: list[Rule], run_id: str, results_table: str) -> None:
    results, failures = [], []
    for r in rules:
        violations = spark.sql(r.sql).first()[0]
        status = "PASS" if violations == 0 else r.severity
        results.append((run_id, r.name, r.severity, int(violations), status))
        if status == "FAIL":
            failures.append(f"{r.name}: {violations} violating rows")
    spark.createDataFrame(results, "run_id STRING, rule STRING, severity STRING, violations BIGINT, status STRING") \
         .write.mode("append").saveAsTable(results_table)
    if failures:
        raise RuntimeError("Data quality gate failed: " + "; ".join(failures))
```

## 4. Migration validation (HMS→UC): a test suite in its own right

| # | Test | Query/approach |
|---|---|---|
| 1 | Every planned object exists | Plan CSV ⟂ `information_schema.tables` (anti join → missing) |
| 2 | Object type & location | `DESCRIBE DETAIL` / `information_schema.tables` vs plan |
| 3 | Schema equality | Compare `DESCRIBE` output (name, type, order), or `df.schema` |
| 4 | Row counts | `COUNT(*)` both sides (per partition for big tables) |
| 5 | Aggregate fingerprint | `COUNT DISTINCT key`, `SUM(numeric)`, `MIN/MAX(dates)` |
| 6 | Row-level equality (critical tables) | `EXCEPT ALL` both directions, or compare `xxhash64(*)` per row aggregated by partition |
| 7 | Views return the same results | Run the old and new view; fingerprint both |
| 8 | Grants | `SHOW GRANTS` vs mapping; positive and negative access tests |
| 9 | Jobs | Job runs green on UC in QA; outputs reconcile with the HMS run |
| 10 | Performance | Duration within ±20% of the baseline |

```sql
-- Row-level hash comparison by partition (scales better than EXCEPT on huge tables)
-- (cast to DECIMAL so the SUM can't overflow BIGINT under ANSI mode)
WITH s AS (SELECT order_date, COUNT(*) c, SUM(CAST(xxhash64(*) AS DECIMAL(38,0))) h FROM hive_metastore.sales.orders GROUP BY order_date),
     t AS (SELECT order_date, COUNT(*) c, SUM(CAST(xxhash64(*) AS DECIMAL(38,0))) h FROM sales_prod.sales.orders     GROUP BY order_date)
SELECT COALESCE(s.order_date, t.order_date) d, s.c src_rows, t.c tgt_rows,
       CASE WHEN s.c = t.c AND s.h = t.h THEN 'MATCH' ELSE 'DIFF' END status
FROM s FULL OUTER JOIN t ON s.order_date = t.order_date
WHERE NOT (s.c <=> t.c AND s.h <=> t.h);
```
(Hashes depend on column order and types. If the target schema intentionally differs, hash an explicit column list with casts.)

**Output a validation report** (a table + Markdown) per wave: object, check, source value, target value, status, explanation. **Explained differences** (e.g. DOUBLE → DECIMAL) are recorded and signed off.

## 5. Regression testing
Before you refactor a pipeline (or migrate it), capture its output on a fixed input. After the change, run it again and diff. Same approach as migration validation.

---

## How this connects to HMS→UC
Section 4 *is* your project's validation work. Build it once as reusable code (part of the capstone), and you'll be the person on the team who can validate a wave in an hour instead of a day.

## Hands-on
1. Set up `pytest` + local Spark; write 8 unit tests for the capstone transformations (including NULL/empty/duplicate cases).
2. Add `NOT NULL` and `CHECK` constraints to a Silver table; try to violate them.
3. Implement the `run_rules` framework, with 8 rules on your Gold tables; make one fail on purpose and see the job fail.
4. Write the migration validation suite (tests 1–6) as a parameterised notebook, run it on a migrated sandbox schema, and produce a report.
5. Introduce a subtle bug (wrong time zone). Which test catches it? If none, write one.

## After this phase you should be able to explain
- [ ] Unit vs integration vs DQ vs reconciliation tests
- [ ] How to unit test PySpark
- [ ] Which DQ checks you'd put on a fact table, and which fail vs warn
- [ ] How you'd prove a migrated table equals its source, at scale
- [ ] What an "explained difference" is

## Beginner vs experienced
| Beginner | Experienced |
|---|---|
| Tests manually by looking at `display(df)` | Automated unit tests in CI + DQ gates in jobs + reconciliation reports |
| Checks row counts | Designs layered validation, and knows what counts *can't* detect |

## Interview questions
1. How do you test a PySpark transformation?
2. What data quality checks would you implement for a new pipeline?
3. How do you validate a data migration?
4. A job succeeded but the data is wrong. How could you have caught it?
5. Fail the pipeline or quarantine bad records? How do you decide?
6. How do you compare two very large tables efficiently?
