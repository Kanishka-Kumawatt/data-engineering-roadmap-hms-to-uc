# Databricks notebook source
# MAGIC %md
# MAGIC # 02 · Silver: clean, quarantine, dedupe, MERGE
# MAGIC * Orders: incremental from Bronze (Delta stream + `foreachBatch`), MERGE on `order_id` guarded by `updated_at`
# MAGIC * Products / stores: latest snapshot (SCD1). **Stretch:** make products SCD2 (Phase 6 §4)

# COMMAND ----------

import os
import sys

sys.path.append(os.path.abspath("../src"))

from delta.tables import DeltaTable
from pyspark.sql import functions as F

from phoenix.config import from_widgets
from phoenix.transforms import clean_orders, latest_per_key

cfg = from_widgets(dbutils)
silver_orders = cfg.table("silver", "orders")
quarantine = cfg.table("silver", "orders_quarantine")

spark.sql(f"""
CREATE TABLE IF NOT EXISTS {silver_orders} (
  order_id BIGINT NOT NULL, store_id INT, product_id INT, quantity INT, unit_price DECIMAL(12,2),
  status STRING, order_ts TIMESTAMP, updated_at TIMESTAMP, _ingested_at TIMESTAMP, _source_file STRING,
  order_date DATE
) CLUSTER BY (order_date)
COMMENT 'Grain: one row per order (latest version). Source: bronze.pos_orders'
""")

# COMMAND ----------

def upsert_orders(batch_df, batch_id: int) -> None:
    cleaned = clean_orders(batch_df)
    (cleaned.filter("_dq_issue IS NOT NULL")
            .withColumn("_batch_id", F.lit(batch_id))
            .write.mode("append").option("mergeSchema", "true").saveAsTable(quarantine))
    good = latest_per_key(cleaned.filter("_dq_issue IS NULL")).drop("_dq_issue")
    (DeltaTable.forName(batch_df.sparkSession, silver_orders).alias("t")
        .merge(good.alias("s"), "t.order_id = s.order_id")
        .whenMatchedUpdateAll(condition="s.updated_at > t.updated_at")
        .whenNotMatchedInsertAll()
        .execute())

(spark.readStream.table(cfg.table("bronze", "pos_orders"))
      .writeStream
      .foreachBatch(upsert_orders)
      .option("checkpointLocation", f"{cfg.checkpoint_root}/silver_orders")
      .trigger(availableNow=True)
      .start()
      .awaitTermination())

# COMMAND ----------

# Products & stores: keep the latest snapshot per key (SCD1)
from pyspark.sql import Window

products = (spark.table(cfg.table("bronze", "products"))
            .withColumn("_rn", F.row_number().over(
                Window.partitionBy("product_id").orderBy(F.col("snapshot_date").desc(), F.col("_ingested_at").desc())))
            .filter("_rn = 1")
            .select(F.col("product_id").cast("int"), "product_name", "category",
                    F.col("unit_price").cast("decimal(12,2)").alias("list_price"),
                    F.col("snapshot_date").cast("date")))
products.write.mode("overwrite").saveAsTable(cfg.table("silver", "products"))

stores = (spark.table(cfg.table("bronze", "stores"))
          .select(F.col("store_id").cast("int"), "store_name", "region").dropDuplicates(["store_id"]))
stores.write.mode("overwrite").saveAsTable(cfg.table("silver", "stores"))

display(spark.sql(f"SELECT _dq_issue, COUNT(*) FROM {quarantine} GROUP BY 1"))
