from datetime import date, datetime
from decimal import Decimal

import pytest

pytest.importorskip("pyspark")

RAW_SCHEMA = ("order_id STRING, store_id STRING, product_id STRING, quantity STRING, unit_price STRING, "
              "status STRING, order_ts STRING, updated_at STRING, _ingested_at TIMESTAMP, _source_file STRING")


def raw(order_id="1", store_id="5", product_id="10", quantity="2", unit_price="9.99", status="completed",
        order_ts="2026-10-01 10:00:00", updated_at="2026-10-01 10:00:00"):
    return (order_id, store_id, product_id, quantity, unit_price, status, order_ts, updated_at,
            datetime(2026, 10, 1, 12), "f.json")


def test_clean_orders_valid_row_has_no_issue_and_standardised_status(spark):
    from phoenix.transforms import clean_orders

    row = clean_orders(spark.createDataFrame([raw()], RAW_SCHEMA)).first()
    assert row["_dq_issue"] is None
    assert row["status"] == "COMPLETED"
    assert row["unit_price"] == Decimal("9.99")


@pytest.mark.parametrize("overrides, issue", [
    ({"order_id": None}, "NULL_ORDER_ID"),
    ({"store_id": None}, "NULL_STORE_ID"),
    ({"quantity": "0"}, "NON_POSITIVE_QTY"),
    ({"status": "??"}, "INVALID_STATUS"),
    ({"status": None}, "INVALID_STATUS"),
    ({"order_ts": "not-a-date"}, "BAD_ORDER_TS"),
])
def test_clean_orders_flags_invalid_rows(spark, overrides, issue):
    from phoenix.transforms import clean_orders

    spark.conf.set("spark.sql.ansi.enabled", "false")   # bad strings -> NULL instead of an exception
    row = clean_orders(spark.createDataFrame([raw(**overrides)], RAW_SCHEMA)).first()
    assert row["_dq_issue"] == issue


def test_order_date_uses_dubai_business_day(spark):
    from phoenix.transforms import clean_orders

    # 22:30 UTC on 1 Oct is 02:30 on 2 Oct in Dubai (UTC+4)
    row = clean_orders(spark.createDataFrame([raw(order_ts="2026-10-01 22:30:00")], RAW_SCHEMA)).first()
    assert row["order_date"] == date(2026, 10, 2)


def test_latest_per_key_keeps_newest_version(spark):
    from pyspark.testing import assertDataFrameEqual

    from phoenix.transforms import latest_per_key

    df = spark.createDataFrame([
        (1, datetime(2026, 10, 1, 10), datetime(2026, 10, 1, 10), "old"),
        (1, datetime(2026, 10, 1, 12), datetime(2026, 10, 1, 12), "new"),
        (2, datetime(2026, 10, 1, 9), datetime(2026, 10, 1, 9), "only"),
    ], "order_id INT, updated_at TIMESTAMP, _ingested_at TIMESTAMP, note STRING")
    result = latest_per_key(df).select("order_id", "note")
    expected = spark.createDataFrame([(1, "new"), (2, "only")], "order_id INT, note STRING")
    assertDataFrameEqual(result, expected)


def test_latest_per_key_exact_duplicates_collapse_to_one(spark):
    from phoenix.transforms import latest_per_key

    ts = datetime(2026, 10, 1, 10)
    df = spark.createDataFrame([(1, ts, ts), (1, ts, ts)], "order_id INT, updated_at TIMESTAMP, _ingested_at TIMESTAMP")
    assert latest_per_key(df).count() == 1


def test_build_daily_sales_counts_only_completed_and_maps_unknown_products(spark):
    from phoenix.transforms import build_daily_sales

    d = date(2026, 10, 1)
    orders = spark.createDataFrame([
        (1, d, 5, 10, 2, Decimal("10.00"), "COMPLETED"),
        (2, d, 5, 10, 1, Decimal("30.00"), "COMPLETED"),
        (3, d, 5, 10, 9, Decimal("99.00"), "CANCELLED"),   # excluded
        (4, d, 5, 99, 1, Decimal("5.00"), "COMPLETED"),    # product not in master -> UNKNOWN
    ], "order_id BIGINT, order_date DATE, store_id INT, product_id INT, quantity INT, unit_price DECIMAL(12,2), status STRING")
    products = spark.createDataFrame([(10, "Electronics")], "product_id INT, category STRING")

    rows = {r["category"]: r for r in build_daily_sales(orders, products).collect()}
    assert rows["Electronics"]["revenue"] == Decimal("50.00")
    assert rows["Electronics"]["orders"] == 2
    assert rows["Electronics"]["avg_order_value"] == Decimal("25.00")
    assert rows["UNKNOWN"]["revenue"] == Decimal("5.00")
