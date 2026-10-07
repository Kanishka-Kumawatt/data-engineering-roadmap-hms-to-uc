# Databricks notebook source
# MAGIC %md
# MAGIC # 12 · Migration: validate
# MAGIC Per migrated table: **exists → schema → row count → fingerprint (row-hash sum)**. Results go to `ops.migration_validation`.
# MAGIC Any difference must be fixed **or** written up as an *explained difference* in `docs/validation-report.md`.
# MAGIC
# MAGIC TODO(learner): add EXCEPT ALL (both directions) for one critical table, hash-by-partition for the big table,
# MAGIC view-result comparison, and permission tests (run as a member of grp_phoenix_bi).

# COMMAND ----------

import os
import sys

sys.path.append(os.path.abspath("../src"))

from phoenix.config import from_widgets, validate_identifier

cfg = from_widgets(dbutils)
dbutils.widgets.text("legacy_catalog", "capstone_legacy")
legacy = validate_identifier(dbutils.widgets.get("legacy_catalog"))

# COMMAND ----------

def source_ref(r) -> str:
    return f"{r.provider}.`{r.location}`" if r.object_type == "PATH" else f"{legacy}.{r.schema}.{r.name}"

def fingerprint(ref: str) -> tuple[int, str]:
    row = spark.sql(f"SELECT COUNT(*) AS c, CAST(SUM(CAST(xxhash64(*) AS DECIMAL(38,0))) AS STRING) AS h FROM {ref}").first()
    return int(row.c), row.h

def schema_of(ref: str) -> list[tuple[str, str]]:
    return [(f.name, f.dataType.simpleString()) for f in spark.sql(f"SELECT * FROM {ref} LIMIT 0").schema]

results = []
plan = spark.table(cfg.table("ops", "migration_plan")).filter("method NOT IN ('RECREATE_VIEW', 'RECREATE_FUNCTION', 'MANUAL')")
for r in plan.collect():
    src, tgt = source_ref(r), f"{cfg.catalog}.legacy.{r.name}"
    if not spark.catalog.tableExists(tgt):
        results.append((r.name, "exists", src, "missing", "FAIL"))
        continue
    s_schema, t_schema = schema_of(src), schema_of(tgt)
    results.append((r.name, "schema", str(s_schema), str(t_schema), "PASS" if s_schema == t_schema else "FAIL"))
    (s_cnt, s_hash), (t_cnt, t_hash) = fingerprint(src), fingerprint(tgt)
    results.append((r.name, "row_count", str(s_cnt), str(t_cnt), "PASS" if s_cnt == t_cnt else "FAIL"))
    results.append((r.name, "row_hash", s_hash, t_hash, "PASS" if s_hash == t_hash else "FAIL"))

report = spark.createDataFrame(results, "object STRING, check STRING, source_value STRING, target_value STRING, status STRING")
report.write.mode("overwrite").saveAsTable(cfg.table("ops", "migration_validation"))
display(report)

# COMMAND ----------

# Markdown table to paste into docs/validation-report.md
print("| Object | Check | Source | Target | Status |\n|---|---|---|---|---|")
for o, c, s, t, st in results:
    print(f"| {o} | {c} | {s[:40]} | {t[:40]} | {st} |")
