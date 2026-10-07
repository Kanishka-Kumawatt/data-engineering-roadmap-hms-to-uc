from pathlib import Path

from phoenix.migration.scanner import scan_path, scan_text


def rules(text: str) -> set[str]:
    return {f.rule for f in scan_text(text)}


def test_detects_mount_and_dbfs_paths():
    assert "MOUNT_PATH" in rules('spark.read.parquet("/mnt/raw/sales")')
    assert "MOUNT_PATH" in rules("spark.read.load('dbfs:/mnt/raw/x')")
    assert "DBFS_PATH" in rules('df.write.save("dbfs:/FileStore/out")')
    assert "DBFS_PATH" in rules("SELECT * FROM parquet.`dbfs:/FileStore/x/`")


def test_detects_legacy_apis_and_keys():
    assert "INPUT_FILE_NAME" in rules("df.withColumn('f', F.input_file_name())")
    assert "SPARK_CONTEXT_OR_RDD" in rules("sc.parallelize([1, 2])")
    assert "SPARK_CONTEXT_OR_RDD" in rules("df.rdd.map(lambda r: r)")
    assert "STORAGE_KEY_IN_CONF" in rules('spark.conf.set("fs.azure.account.key.acct.dfs.core.windows.net", k)')


def test_two_level_names_flagged_but_three_level_and_imports_are_not():
    assert "TWO_LEVEL_NAME" in rules("SELECT * FROM sales.orders")
    assert "TWO_LEVEL_NAME" in rules('spark.table("sales.orders")')
    assert "TWO_LEVEL_NAME" in rules('df.write.saveAsTable("sales.orders")')
    assert "TWO_LEVEL_NAME" in rules("CREATE OR REPLACE VIEW sales.v_orders AS SELECT 1")
    assert "TWO_LEVEL_NAME" not in rules("SELECT * FROM prod.sales.orders")
    assert "TWO_LEVEL_NAME" not in rules("from pyspark.sql import functions as F")
    assert "TWO_LEVEL_NAME" not in rules('spark.table(f"{catalog}.sales.orders")')


def test_legacy_code_folder_has_findings_to_fix():
    legacy = Path(__file__).resolve().parents[2] / "legacy_code"
    found = {f.rule for f in scan_path(legacy)}
    assert {"MOUNT_PATH", "DBFS_PATH", "INPUT_FILE_NAME", "SPARK_CONTEXT_OR_RDD",
            "STORAGE_KEY_IN_CONF", "TWO_LEVEL_NAME"} <= found
