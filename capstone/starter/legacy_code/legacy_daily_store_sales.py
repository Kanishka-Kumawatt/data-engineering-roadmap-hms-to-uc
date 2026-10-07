# Databricks notebook source
# LEGACY (HMS-era) notebook: DO NOT copy these patterns. Your task: convert it to UC-compatible code.
# Run the scanner to find the problems:  python -m phoenix.migration.scanner legacy_code/
# Things to fix: storage key in conf, /mnt paths, 2-level table names, input_file_name(), RDD usage.

from pyspark.sql import functions as F

spark.conf.set("fs.azure.account.key.contosolake.dfs.core.windows.net", dbutils.secrets.get("legacy", "lake-key"))

sales = (spark.read.parquet("/mnt/legacy/sales_history/")
         .withColumn("source_file", F.input_file_name()))

stores = spark.table("retail.stores")

store_ids = sc.parallelize([1, 2, 3]).collect()
filtered = sales.filter(F.col("store_id").isin(store_ids))

daily = (filtered.join(stores, "store_id")
         .groupBy("sale_date", "region")
         .agg(F.sum("amount").alias("revenue")))

daily.write.mode("overwrite").saveAsTable("retail.daily_store_sales")
