import pytest

from phoenix.migration import planner as p
from phoenix.migration.planner import LegacyObject, choose_method, creation_order, generate_sql


@pytest.mark.parametrize("obj, expected", [
    (LegacyObject("sales", "v", "VIEW"), p.RECREATE_VIEW),
    (LegacyObject("sales", "f", "FUNCTION"), p.RECREATE_FUNCTION),
    (LegacyObject("sales", "t", "MANAGED", "delta", "dbfs:/user/hive/warehouse/sales.db/t"), p.DEEP_CLONE),
    (LegacyObject("sales", "t", "MANAGED", "parquet", "dbfs:/user/hive/warehouse/sales.db/t"), p.CTAS),
    (LegacyObject("sales", "t", "EXTERNAL", "delta", "abfss://raw@acct.dfs.core.windows.net/sales/t"), p.SYNC),
    (LegacyObject("sales", "t", "EXTERNAL", "parquet", "s3://bucket/sales/t"), p.SYNC),
    (LegacyObject("sales", "t", "EXTERNAL", "delta", "dbfs:/mnt/raw/sales/t"), p.RESOLVE_MOUNT_THEN_SYNC),
    (LegacyObject("sales", "t", "EXTERNAL", "delta", "/mnt/raw/sales/t"), p.RESOLVE_MOUNT_THEN_SYNC),
    (LegacyObject("sales", "t", "EXTERNAL", "delta", "dbfs:/tmp/sales/t"), p.CTAS),
    (LegacyObject("sales", "t", "EXTERNAL", "hive", "abfss://raw@acct.dfs.core.windows.net/t"), p.CTAS),
    (LegacyObject("sales", "t", "EXTERNAL", "weird", "abfss://raw@acct.dfs.core.windows.net/t"), p.MANUAL),
    (LegacyObject("sales", "h", "PATH", "parquet", "/Volumes/x/y/z"), p.CTAS_FROM_PATH),
    (LegacyObject("sales", "t", "SOMETHING"), p.MANUAL),
])
def test_choose_method(obj, expected):
    method, reason = choose_method(obj)
    assert method == expected
    assert reason  # every decision must be explainable


def test_generate_sql_deep_clone():
    obj = LegacyObject("sales", "customers", "MANAGED", "delta")
    assert generate_sql(obj, p.DEEP_CLONE, "hive_metastore", "sales_prod") == \
        "CREATE TABLE IF NOT EXISTS sales_prod.sales.customers DEEP CLONE hive_metastore.sales.customers"


def test_generate_sql_sync_with_target_schema_override():
    obj = LegacyObject("sales", "orders", "EXTERNAL", "delta", "abfss://x")
    assert generate_sql(obj, p.SYNC, "hive_metastore", "cat", target_schema="legacy") == \
        "SYNC TABLE cat.legacy.orders FROM hive_metastore.sales.orders"


def test_generate_sql_ctas_from_path():
    obj = LegacyObject("retail", "sales_history", "PATH", "parquet", "/Volumes/l/retail/files/sales_history")
    sql = generate_sql(obj, p.CTAS_FROM_PATH, "legacy", "phoenix_dev", target_schema="legacy")
    assert sql == ("CREATE TABLE IF NOT EXISTS phoenix_dev.legacy.sales_history AS SELECT * FROM "
                   "parquet.`/Volumes/l/retail/files/sales_history`")


def test_generate_sql_returns_none_for_views():
    assert generate_sql(LegacyObject("s", "v", "VIEW"), p.RECREATE_VIEW, "a", "b") is None


def test_creation_order_puts_dependencies_first():
    deps = {"v_top": {"v_mid"}, "v_mid": {"orders", "customers"}, "orders": set(), "customers": set()}
    order = creation_order(deps)
    assert order.index("v_mid") > order.index("orders")
    assert order.index("v_mid") > order.index("customers")
    assert order.index("v_top") > order.index("v_mid")


def test_creation_order_detects_cycles():
    with pytest.raises(ValueError, match="Circular"):
        creation_order({"a": {"b"}, "b": {"a"}})
