import os
import shutil

import pytest


def _java_available() -> bool:
    return bool(os.environ.get("JAVA_HOME")) or shutil.which("java") is not None


@pytest.fixture(scope="session")
def spark():
    """Local SparkSession for unit tests. Skips Spark tests (not the pure-Python ones) if Java/PySpark is missing."""
    pytest.importorskip("pyspark")
    if not _java_available():
        pytest.skip("Java not found: install JDK 17 to run Spark unit tests")
    from pyspark.sql import SparkSession

    session = (SparkSession.builder.master("local[1]").appName("phoenix-tests")
               .config("spark.sql.shuffle.partitions", "1")
               .config("spark.sql.session.timeZone", "UTC")
               .config("spark.ui.enabled", "false")
               .getOrCreate())
    yield session
    session.stop()
