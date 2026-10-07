# Databricks notebook source
# MAGIC %md
# MAGIC # 10 · Migration: inventory + plan
# MAGIC Works against a simulated legacy catalog **or** a real `hive_metastore` (set `legacy_catalog = hive_metastore`).
# MAGIC Output: `ops.migration_plan` (one row per object, with method + reason from `phoenix.migration.planner`).

# COMMAND ----------

import os
import sys

sys.path.append(os.path.abspath("../src"))

from phoenix.config import from_widgets, validate_identifier
from phoenix.migration.planner import LegacyObject, choose_method

cfg = from_widgets(dbutils)
dbutils.widgets.text("legacy_catalog", "capstone_legacy")
dbutils.widgets.text("legacy_schema", "retail")
legacy = validate_identifier(dbutils.widgets.get("legacy_catalog"))
legacy_schema = validate_identifier(dbutils.widgets.get("legacy_schema"))

# COMMAND ----------

objects: list[LegacyObject] = []
errors: list[tuple[str, str]] = []

for t in spark.sql(f"SHOW TABLES IN {legacy}.{legacy_schema}").collect():
    if t.isTemporary:
        continue
    fqn = f"{legacy}.{legacy_schema}.{t.tableName}"
    try:
        info = {r.col_name.strip(): (r.data_type or "").strip()
                for r in spark.sql(f"DESCRIBE TABLE EXTENDED {fqn}").collect() if r.col_name}
        objects.append(LegacyObject(legacy_schema, t.tableName, info.get("Type", "UNKNOWN").upper(),
                                    info.get("Provider") or None, info.get("Location") or None))
    except Exception as e:  # noqa: BLE001 - record and continue; a broken table must not stop the inventory
        errors.append((fqn, str(e)[:300]))

# Path-based data found by the code scanner (legacy_code/ reads it by path, like a /mnt path)
objects.append(LegacyObject(legacy_schema, "sales_history", "PATH", "parquet",
                            f"/Volumes/{legacy}/{legacy_schema}/legacy_files/sales_history"))

print(f"{len(objects)} objects, {len(errors)} errors")
for e in errors:
    print("ERROR", e)

# COMMAND ----------

plan_rows = []
for o in objects:
    method, reason = choose_method(o)
    plan_rows.append((o.schema, o.name, o.object_type, o.provider, o.location, method, reason,
                      "wave1", "grp_phoenix_engineers"))

plan = spark.createDataFrame(plan_rows, "schema STRING, name STRING, object_type STRING, provider STRING, "
                                        "location STRING, method STRING, reason STRING, wave STRING, owner STRING")
plan.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(cfg.table("ops", "migration_plan"))
display(plan)
