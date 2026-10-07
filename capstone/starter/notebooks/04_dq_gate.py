# Databricks notebook source
# MAGIC %md
# MAGIC # 04 · Data quality gate
# MAGIC Runs the rules, stores results in `ops.dq_results`, and **fails the job** if a FAIL-severity rule is violated.

# COMMAND ----------

import os
import sys

sys.path.append(os.path.abspath("../src"))

from phoenix.config import from_widgets
from phoenix.quality import default_rules, run_rules

cfg = from_widgets(dbutils)
dbutils.widgets.text("job_run_id", "manual")
run_id = dbutils.widgets.get("job_run_id")

rules = default_rules(
    gold_table=cfg.table("gold", "fct_sales_daily"),
    silver_table=cfg.table("silver", "orders"),
    quarantine_table=cfg.table("silver", "orders_quarantine"),
)
# TODO(learner): add freshness (MAX(order_date) >= yesterday), volume anomaly vs 7-day average,
#                and referential integrity (silver.orders.store_id must exist in silver.stores).

results = run_rules(spark, rules, run_id, cfg.table("ops", "dq_results"))
for r in results:
    print(f"{r.status:5} {r.rule} ({r.violations})")
