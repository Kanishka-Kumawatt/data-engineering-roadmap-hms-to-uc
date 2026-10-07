# Databricks notebook source
# MAGIC %md
# MAGIC # 11 · Migration: execute (DRY RUN by default)
# MAGIC 1. Tables from `ops.migration_plan` → SQL from `planner.generate_sql`
# MAGIC 2. Views from `sql/views.sql` (reviewed, version-controlled, created in dependency order)
# MAGIC 3. Grants & ownership from `sql/grants.sql`
# MAGIC
# MAGIC Every statement and its outcome goes to `ops.migration_audit`. Re-runnable (`IF NOT EXISTS` / `OR REPLACE`).

# COMMAND ----------

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.append(os.path.abspath("../src"))

from phoenix.config import from_widgets, validate_identifier
from phoenix.migration.planner import LegacyObject, generate_sql

cfg = from_widgets(dbutils)
dbutils.widgets.text("legacy_catalog", "capstone_legacy")
dbutils.widgets.dropdown("dry_run", "true", ["true", "false"])
legacy = validate_identifier(dbutils.widgets.get("legacy_catalog"))
dry_run = dbutils.widgets.get("dry_run") == "true"
print(f"DRY RUN = {dry_run}")

audit: list[tuple] = []

def execute(object_name: str, step: str, sql: str | None) -> None:
    status, error = "SKIPPED_NO_SQL", None
    if sql:
        if dry_run:
            status = "DRY_RUN"
        else:
            try:
                spark.sql(sql)
                status = "OK"
            except Exception as e:  # noqa: BLE001 - record, continue, report at the end
                status, error = "FAILED", str(e)[:1000]
    audit.append((datetime.now(timezone.utc), object_name, step, sql, status, error, dry_run))
    print(f"[{status}] {object_name}: {sql}")

# COMMAND ----------

# 1. Tables
for r in spark.table(cfg.table("ops", "migration_plan")).filter("method NOT IN ('RECREATE_VIEW', 'RECREATE_FUNCTION', 'MANUAL')").collect():
    obj = LegacyObject(r.schema, r.name, r.object_type, r.provider, r.location)
    execute(f"{r.schema}.{r.name}", r.method, generate_sql(obj, r.method, legacy, cfg.catalog, target_schema="legacy"))

# COMMAND ----------

# 2 & 3. Views, then grants: templated SQL files (reviewed in PRs). ${catalog} is substituted.
def statements(path: str) -> list[str]:
    text = Path(path).read_text(encoding="utf-8").replace("${catalog}", cfg.catalog)
    lines = [ln for ln in text.splitlines() if not ln.strip().startswith("--")]
    return [s.strip() for s in "\n".join(lines).split(";") if s.strip()]

for stmt in statements("../sql/views.sql"):
    execute("views", "RECREATE_VIEW", stmt)
for stmt in statements("../sql/grants.sql"):
    execute("grants", "GRANT", stmt)

# COMMAND ----------

(spark.createDataFrame(audit, "ts TIMESTAMP, object STRING, step STRING, sql STRING, status STRING, error STRING, dry_run BOOLEAN")
      .write.mode("append").saveAsTable(cfg.table("ops", "migration_audit")))

failed = [a for a in audit if a[4] == "FAILED"]
display(spark.table(cfg.table("ops", "migration_audit")).orderBy("ts", ascending=False).limit(50))
if failed:
    raise RuntimeError(f"{len(failed)} migration statement(s) failed; see ops.migration_audit")
