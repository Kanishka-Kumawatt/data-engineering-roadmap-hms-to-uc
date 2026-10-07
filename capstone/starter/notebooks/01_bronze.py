# Databricks notebook source
# MAGIC %md
# MAGIC # 01 · Bronze: incremental file ingestion with Auto Loader
# MAGIC Append-only, raw as received + `_ingested_at` and `_source_file`. `availableNow` = process all new files, then stop.

# COMMAND ----------

import os
import sys

sys.path.append(os.path.abspath("../src"))

from pyspark.sql import functions as F

from phoenix.config import from_widgets

cfg = from_widgets(dbutils)

# COMMAND ----------

def autoload(fmt: str, source_dir: str, target: str, options: dict[str, str] | None = None) -> int:
    reader = (spark.readStream.format("cloudFiles")
              .option("cloudFiles.format", fmt)
              .option("cloudFiles.schemaLocation", f"{cfg.checkpoint_root}/{target}/_schema"))
    for k, v in (options or {}).items():
        reader = reader.option(k, v)
    query = (reader.load(source_dir)
             .select("*",
                     F.current_timestamp().alias("_ingested_at"),
                     F.col("_metadata.file_path").alias("_source_file"))
             .writeStream
             .option("checkpointLocation", f"{cfg.checkpoint_root}/{target}")
             .trigger(availableNow=True)
             .toTable(cfg.table("bronze", target)))
    query.awaitTermination()
    progress = query.lastProgress or {}
    rows = int(progress.get("numInputRows", 0)) if progress else 0
    print(f"bronze.{target}: last micro-batch rows={rows}")
    return rows

autoload("json", f"{cfg.landing_root}/pos_orders/", "pos_orders")
autoload("csv", f"{cfg.landing_root}/products/", "products", {"header": "true"})
autoload("csv", f"{cfg.landing_root}/stores/", "stores", {"header": "true"})

# COMMAND ----------

# TODO(learner): record a row in ops.pipeline_runs (task, rows, status, duration). See phoenix/ops.py.
display(spark.sql(f"SELECT _source_file, COUNT(*) AS n FROM {cfg.table('bronze', 'pos_orders')} GROUP BY 1 ORDER BY 1 DESC LIMIT 10"))
