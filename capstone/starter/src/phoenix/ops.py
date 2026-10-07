"""Operational audit: one row per task run in ops.pipeline_runs (feeds the monitoring dashboard)."""

from __future__ import annotations

from datetime import datetime, timezone

RUNS_SCHEMA = ("run_id STRING, job STRING, task STRING, status STRING, rows_in BIGINT, rows_out BIGINT, "
               "started_at TIMESTAMP, finished_at TIMESTAMP, message STRING")


def run_record(run_id: str, job: str, task: str, status: str, started_at: datetime,
               rows_in: int | None = None, rows_out: int | None = None, message: str | None = None) -> tuple:
    """Pure: build the audit row (truncates long messages so a stack trace can't bloat the table)."""
    if status not in ("SUCCESS", "FAILED", "SKIPPED"):
        raise ValueError(f"Unknown status {status!r}")
    return (run_id, job, task, status, rows_in, rows_out, started_at,
            datetime.now(timezone.utc), (message or "")[:1000] or None)


def record_run(spark, table: str, record: tuple) -> None:  # pragma: no cover - needs Spark + UC
    spark.createDataFrame([record], RUNS_SCHEMA).write.mode("append").saveAsTable(table)
