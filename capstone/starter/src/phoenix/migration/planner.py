"""Decide HOW each legacy object migrates, and generate the SQL. See phases/phase-07 section 10 for the decision matrix.

Simplified on purpose: real projects add rules for partitioned tables, streaming tables, Hive SerDe options,
non-DBFS-root managed tables, etc. Extend the rules and the tests together.
"""

from __future__ import annotations

from dataclasses import dataclass
from graphlib import CycleError, TopologicalSorter

# Formats you expect SYNC to handle for EXTERNAL tables. Verify against current Databricks docs for your runtime.
SYNC_FORMATS = frozenset({"delta", "parquet", "csv", "json", "orc", "avro", "text"})

SYNC = "SYNC"
DEEP_CLONE = "DEEP_CLONE"
CTAS = "CTAS"
CTAS_FROM_PATH = "CTAS_FROM_PATH"
RECREATE_VIEW = "RECREATE_VIEW"
RECREATE_FUNCTION = "RECREATE_FUNCTION"
RESOLVE_MOUNT_THEN_SYNC = "RESOLVE_MOUNT_THEN_SYNC"
MANUAL = "MANUAL"


@dataclass(frozen=True)
class LegacyObject:
    schema: str
    name: str
    object_type: str            # MANAGED | EXTERNAL | VIEW | FUNCTION | PATH
    provider: str | None = None  # delta, parquet, hive, ...
    location: str | None = None

    @property
    def fqn_parts(self) -> tuple[str, str]:
        return self.schema, self.name


def _is_dbfs_root(location: str | None) -> bool:
    loc = (location or "").lower()
    return loc.startswith("dbfs:/") and not loc.startswith("dbfs:/mnt/")


def _is_mount(location: str | None) -> bool:
    loc = (location or "").lower()
    return loc.startswith("/mnt/") or loc.startswith("dbfs:/mnt/")


def choose_method(obj: LegacyObject) -> tuple[str, str]:
    """Return (method, reason) for one object."""
    otype = obj.object_type.upper()
    provider = (obj.provider or "").lower()

    if otype == "VIEW":
        return RECREATE_VIEW, "Views must be recreated with 3-level names after their base tables exist"
    if otype == "FUNCTION":
        return RECREATE_FUNCTION, "Recreate as a UC function; Hive/JAR UDFs need a rewrite"
    if otype == "PATH":
        return CTAS_FROM_PATH, "Path-based data (e.g. read from a mount) becomes a governed UC managed table"
    if otype == "MANAGED":
        if provider == "delta":
            return DEEP_CLONE, "Managed Delta (DBFS root is not a valid UC location): copy with DEEP CLONE"
        return CTAS, f"Managed non-Delta ({provider or 'unknown'}): copy with CTAS into Delta"
    if otype == "EXTERNAL":
        if _is_dbfs_root(obj.location):
            return CTAS, "External table on DBFS root cannot be registered in UC: copy with CTAS"
        if _is_mount(obj.location):
            return RESOLVE_MOUNT_THEN_SYNC, "Resolve the mount to its cloud path, ensure an external location, then SYNC"
        if provider in SYNC_FORMATS:
            return SYNC, "External table on cloud storage with a supported format: register in place with SYNC"
        if provider == "hive":
            return CTAS, "Hive SerDe table: convert to Delta with CTAS"
        return MANUAL, f"External table with unsupported/unknown format {provider!r}"
    return MANUAL, f"Unknown object type {obj.object_type!r}"


def generate_sql(obj: LegacyObject, method: str, source_catalog: str, target_catalog: str,
                 target_schema: str | None = None) -> str | None:
    """SQL for table-like methods. Views/functions/manual items return None (they need human-reviewed SQL)."""
    tgt = f"{target_catalog}.{target_schema or obj.schema}.{obj.name}"
    src = f"{source_catalog}.{obj.schema}.{obj.name}"
    if method == SYNC:
        return f"SYNC TABLE {tgt} FROM {src}"
    if method == DEEP_CLONE:
        return f"CREATE TABLE IF NOT EXISTS {tgt} DEEP CLONE {src}"
    if method == CTAS:
        return f"CREATE TABLE IF NOT EXISTS {tgt} AS SELECT * FROM {src}"
    if method == CTAS_FROM_PATH:
        fmt = (obj.provider or "parquet").lower()
        return f"CREATE TABLE IF NOT EXISTS {tgt} AS SELECT * FROM {fmt}.`{obj.location}`"
    return None


def creation_order(dependencies: dict[str, set[str]]) -> list[str]:
    """Topologically sort objects so every view is created after the objects it reads from.

    `dependencies` maps object -> set of objects it depends on. Raises ValueError on cycles.
    """
    try:
        return list(TopologicalSorter(dependencies).static_order())
    except CycleError as e:
        raise ValueError(f"Circular view dependency: {e.args[1]}") from e
