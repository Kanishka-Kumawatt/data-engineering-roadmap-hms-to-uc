# Databricks notebook source
# MAGIC %md
# MAGIC # 00 · Setup: target catalog + simulated legacy (HMS-style) environment
# MAGIC
# MAGIC Creates (idempotently):
# MAGIC * **Target** `phoenix_<env>` catalog with schemas `bronze`, `silver`, `gold`, `ops`, `legacy` and volumes `bronze.landing`, `bronze.checkpoints`
# MAGIC * **Legacy** `capstone_legacy.retail`, standing in for `hive_metastore.retail`:
# MAGIC   * `customers`, `stores`: managed Delta tables (think "managed tables on DBFS root")
# MAGIC   * `/Volumes/capstone_legacy/retail/legacy_files/sales_history/`: Parquet files read by path (think "`/mnt/legacy/sales_history`")
# MAGIC   * `v_store_summary`: a view
# MAGIC * Synthetic landing data for the new pipeline (via `scripts/generate_data.py`)
# MAGIC
# MAGIC > If `CREATE CATALOG` is not allowed in your workspace, set both widgets to an existing catalog and the code will only create schemas.

# COMMAND ----------

import os
import sys

sys.path.append(os.path.abspath("../src"))
sys.path.append(os.path.abspath("../scripts"))

from phoenix.config import validate_identifier

dbutils.widgets.text("catalog", "phoenix_dev")
dbutils.widgets.text("legacy_catalog", "capstone_legacy")
dbutils.widgets.text("generate_days", "30")
catalog = validate_identifier(dbutils.widgets.get("catalog"))
legacy = validate_identifier(dbutils.widgets.get("legacy_catalog"))
generate_days = int(dbutils.widgets.get("generate_days"))

# COMMAND ----------

def run(sql: str) -> None:
    print(sql)
    spark.sql(sql)

for cat in (catalog, legacy):
    try:
        run(f"CREATE CATALOG IF NOT EXISTS {cat}")
    except Exception as e:  # noqa: BLE001 - informative fallback for restricted workspaces
        print(f"Could not create catalog {cat} ({e.__class__.__name__}); assuming it already exists")

for schema in ("bronze", "silver", "gold", "ops", "legacy"):
    run(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{schema}")
run(f"CREATE VOLUME IF NOT EXISTS {catalog}.bronze.landing")
run(f"CREATE VOLUME IF NOT EXISTS {catalog}.bronze.checkpoints")

run(f"CREATE SCHEMA IF NOT EXISTS {legacy}.retail")
run(f"CREATE VOLUME IF NOT EXISTS {legacy}.retail.legacy_files")

# COMMAND ----------

# MAGIC %md ## Legacy objects

# COMMAND ----------

from pyspark.sql import functions as F

customers = (spark.range(1, 5001).withColumnRenamed("id", "customer_id")
             .withColumn("name", F.concat(F.lit("Customer "), F.col("customer_id")))
             .withColumn("email", F.concat(F.lit("c"), F.col("customer_id"), F.lit("@example.com")))
             .withColumn("region", F.element_at(F.array(*[F.lit(r) for r in ("UAE", "KSA", "QAT", "OMN")]),
                                                (F.col("customer_id") % 4 + 1).cast("int")))
             .withColumn("signup_date", F.date_sub(F.lit("2026-09-01").cast("date"), (F.col("customer_id") % 900).cast("int"))))
customers.write.mode("overwrite").saveAsTable(f"{legacy}.retail.customers")

stores = spark.createDataFrame([(i, f"Store {i}", ("UAE", "KSA", "QAT", "OMN")[i % 4]) for i in range(1, 11)],
                               "store_id INT, store_name STRING, region STRING")
stores.write.mode("overwrite").saveAsTable(f"{legacy}.retail.stores")

# Path-based Parquet data, like an old job writing to /mnt/legacy/sales_history
sales_history = (spark.range(0, 200_000)
                 .withColumn("sale_date", F.date_sub(F.lit("2026-08-31").cast("date"), (F.col("id") % 365).cast("int")))
                 .withColumn("store_id", (F.col("id") % 10 + 1).cast("int"))
                 .withColumn("amount", (F.rand(seed=7) * 500).cast("double")))   # DOUBLE on purpose (see Phase 7 scenario 3)
sales_history.write.mode("overwrite").parquet(f"/Volumes/{legacy}/retail/legacy_files/sales_history")

run(f"""CREATE OR REPLACE VIEW {legacy}.retail.v_store_summary AS
        SELECT region, COUNT(*) AS stores FROM {legacy}.retail.stores GROUP BY region""")

display(spark.sql(f"SHOW TABLES IN {legacy}.retail"))

# COMMAND ----------

# MAGIC %md ## Synthetic landing data for the new pipeline

# COMMAND ----------

from datetime import date
from pathlib import Path

from generate_data import generate

landing = Path(f"/Volumes/{catalog}/bronze/landing")
generate(landing, start=date(2026, 9, 1), days=generate_days, orders_per_day=2000, files_per_day=4, seed=42)
display(dbutils.fs.ls(str(landing)))
