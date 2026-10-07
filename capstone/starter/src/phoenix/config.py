"""Environment-aware configuration. The same code runs in dev and prod; only the catalog differs."""

from __future__ import annotations

import re
from dataclasses import dataclass

_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]{0,254}$")


def validate_identifier(name: str) -> str:
    """Reject anything that is not a simple lower-case identifier (protects f-string SQL from injection/typos)."""
    if not isinstance(name, str) or not _IDENTIFIER.match(name):
        raise ValueError(f"Invalid identifier: {name!r} (expected lower-case letters, digits, underscores)")
    return name


@dataclass(frozen=True)
class PipelineConfig:
    catalog: str
    lookback_days: int = 3

    def __post_init__(self) -> None:
        validate_identifier(self.catalog)
        if not 0 <= self.lookback_days <= 31:
            raise ValueError("lookback_days must be between 0 and 31")

    def table(self, schema: str, name: str) -> str:
        """Fully qualified 3-level name. Never use 2-level names in pipeline code."""
        return f"{self.catalog}.{validate_identifier(schema)}.{validate_identifier(name)}"

    @property
    def landing_root(self) -> str:
        return f"/Volumes/{self.catalog}/bronze/landing"

    @property
    def checkpoint_root(self) -> str:
        return f"/Volumes/{self.catalog}/bronze/checkpoints"


def from_widgets(dbutils) -> PipelineConfig:  # pragma: no cover - needs Databricks
    """Build config from job parameters / notebook widgets."""
    dbutils.widgets.text("catalog", "phoenix_dev")
    dbutils.widgets.text("lookback_days", "3")
    return PipelineConfig(
        catalog=dbutils.widgets.get("catalog"),
        lookback_days=int(dbutils.widgets.get("lookback_days")),
    )
