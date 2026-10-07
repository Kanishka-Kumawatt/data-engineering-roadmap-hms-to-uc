"""Pure DataFrame transformations: no reads, no writes, so they can be unit tested locally."""

from __future__ import annotations

from pyspark.sql import DataFrame, Window
from pyspark.sql import functions as F

BUSINESS_TZ = "Asia/Dubai"
VALID_STATUSES = ("COMPLETED", "CANCELLED", "PENDING", "REFUNDED")


def clean_orders(df: DataFrame) -> DataFrame:
    """Cast raw Bronze order columns, standardise values and flag invalid rows in `_dq_issue`.

    Timestamps in the source are UTC; the business day is defined in Dubai time.
    """
    typed = df.select(
        F.col("order_id").cast("bigint").alias("order_id"),
        F.col("store_id").cast("int").alias("store_id"),
        F.col("product_id").cast("int").alias("product_id"),
        F.col("quantity").cast("int").alias("quantity"),
        F.col("unit_price").cast("decimal(12,2)").alias("unit_price"),
        F.upper(F.trim(F.col("status"))).alias("status"),
        F.to_timestamp("order_ts").alias("order_ts"),
        F.to_timestamp("updated_at").alias("updated_at"),
        F.col("_ingested_at"),
        F.col("_source_file"),
    )
    return typed.withColumn(
        "order_date", F.to_date(F.from_utc_timestamp("order_ts", BUSINESS_TZ))
    ).withColumn(
        "_dq_issue",
        F.when(F.col("order_id").isNull(), F.lit("NULL_ORDER_ID"))
        .when(F.col("order_ts").isNull(), F.lit("BAD_ORDER_TS"))
        .when(F.col("store_id").isNull(), F.lit("NULL_STORE_ID"))
        .when(F.col("quantity").isNull() | (F.col("quantity") <= 0), F.lit("NON_POSITIVE_QTY"))
        .when(F.col("status").isNull() | ~F.col("status").isin(*VALID_STATUSES), F.lit("INVALID_STATUS"))
        .otherwise(F.lit(None).cast("string")),
    )


def latest_per_key(df: DataFrame, key: str = "order_id", order_col: str = "updated_at") -> DataFrame:
    """Keep exactly one row per key: the latest by `order_col`, ties broken by `_ingested_at`.

    Always run this before a MERGE so no two source rows match the same target row.
    """
    w = Window.partitionBy(key).orderBy(F.col(order_col).desc_nulls_last(), F.col("_ingested_at").desc_nulls_last())
    return df.withColumn("_rn", F.row_number().over(w)).filter(F.col("_rn") == 1).drop("_rn")


def build_daily_sales(orders: DataFrame, products: DataFrame) -> DataFrame:
    """Gold fct_sales_daily. Grain: order_date x store_id x category.

    Simplification: one product per order. Products missing from the master map to 'UNKNOWN'
    instead of being dropped by an inner join.
    """
    completed = orders.filter(F.col("status") == "COMPLETED")
    joined = completed.join(F.broadcast(products.select("product_id", "category")), "product_id", "left")
    return (
        joined.withColumn("category", F.coalesce(F.col("category"), F.lit("UNKNOWN")))
        .withColumn("line_amount", F.col("quantity") * F.col("unit_price"))
        .groupBy("order_date", "store_id", "category")
        .agg(
            F.sum("line_amount").cast("decimal(18,2)").alias("revenue"),
            F.countDistinct("order_id").alias("orders"),
        )
        .withColumn("avg_order_value", (F.col("revenue") / F.col("orders")).cast("decimal(18,2)"))
    )
