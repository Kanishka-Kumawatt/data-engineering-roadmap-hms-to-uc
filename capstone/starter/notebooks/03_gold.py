# Databricks notebook source
# MAGIC %md
# MAGIC # 03 · Gold: fct_sales_daily (grain: order_date × store_id × category)
# MAGIC Rebuilds the window `[run_date - lookback_days, run_date]` with `replaceWhere`. Re-running gives the same result
# MAGIC (idempotent), and late orders within the look-back window are picked up.
# MAGIC
# MAGIC First run on the generated data: `run_date = 2026-09-30`, `lookback_days = 30`.

# COMMAND ----------

import datetime as dt
import os
import sys

sys.path.append(os.path.abspath("../src"))

from pyspark.sql import functions as F

from phoenix.config import from_widgets
from phoenix.transforms import build_daily_sales

cfg = from_widgets(dbutils)
dbutils.widgets.text("run_date", "")
run_date = dt.date.fromisoformat(dbutils.widgets.get("run_date") or dt.date.today().isoformat())
start_date = run_date - dt.timedelta(days=cfg.lookback_days)
gold = cfg.table("gold", "fct_sales_daily")
print(f"Rebuilding {gold} for {start_date}..{run_date}")

spark.sql(f"""
CREATE TABLE IF NOT EXISTS {gold} (
  order_date DATE NOT NULL COMMENT 'Business day (Asia/Dubai)',
  store_id INT, category STRING,
  revenue DECIMAL(18,2) COMMENT 'Sum of quantity*unit_price for COMPLETED orders',
  orders BIGINT COMMENT 'Distinct completed orders',
  avg_order_value DECIMAL(18,2)
) CLUSTER BY (order_date)
COMMENT 'Grain: order_date x store_id x category. Owner: grp_phoenix_engineers. Ticket DE-142'
""")

# COMMAND ----------

orders = spark.table(cfg.table("silver", "orders")).filter(F.col("order_date").between(start_date, run_date))
daily = build_daily_sales(orders, spark.table(cfg.table("silver", "products")))

(daily.write.mode("overwrite")
      .option("replaceWhere", f"order_date >= '{start_date}' AND order_date <= '{run_date}'")
      .saveAsTable(gold))

display(spark.table(gold).filter(F.col("order_date").between(start_date, run_date)).orderBy("order_date", "store_id"))

# COMMAND ----------

# TODO(learner): build dim_date, dim_store, dim_product (SCD2 stretch) and add informational PK/FK constraints.
