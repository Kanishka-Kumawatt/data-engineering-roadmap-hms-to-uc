"""A tiny data-quality rules engine. Each rule is a SQL query returning one integer: the number of violating rows."""

from __future__ import annotations

from dataclasses import dataclass

SEVERITIES = ("FAIL", "WARN")


@dataclass(frozen=True)
class Rule:
    name: str
    sql: str
    severity: str = "FAIL"

    def __post_init__(self) -> None:
        if self.severity not in SEVERITIES:
            raise ValueError(f"severity must be one of {SEVERITIES}, got {self.severity!r}")


@dataclass(frozen=True)
class RuleResult:
    rule: str
    severity: str
    violations: int
    status: str  # PASS | WARN | FAIL


def evaluate(rule: Rule, violations: int) -> RuleResult:
    """Pure: turn a violation count into a result."""
    status = "PASS" if violations == 0 else rule.severity
    return RuleResult(rule.name, rule.severity, int(violations), status)


def failures(results: list[RuleResult]) -> list[str]:
    return [f"{r.rule}: {r.violations} violating rows" for r in results if r.status == "FAIL"]


def run_rules(spark, rules: list[Rule], run_id: str, results_table: str) -> list[RuleResult]:  # pragma: no cover
    """Run every rule, persist the results, then raise if any FAIL-severity rule was violated."""
    results = [evaluate(r, spark.sql(r.sql).first()[0]) for r in rules]
    rows = [(run_id, r.rule, r.severity, r.violations, r.status) for r in results]
    (spark.createDataFrame(rows, "run_id STRING, rule STRING, severity STRING, violations BIGINT, status STRING")
          .write.mode("append").saveAsTable(results_table))
    failed = failures(results)
    if failed:
        raise RuntimeError("Data quality gate failed: " + "; ".join(failed))
    return results


def default_rules(gold_table: str, silver_table: str, quarantine_table: str) -> list[Rule]:
    """Starter rule set. Extend it: freshness, volume anomaly, referential integrity..."""
    return [
        Rule("silver_order_id_unique",
             f"SELECT COUNT(*) FROM (SELECT order_id FROM {silver_table} GROUP BY order_id HAVING COUNT(*) > 1)"),
        Rule("silver_order_id_not_null", f"SELECT COUNT(*) FROM {silver_table} WHERE order_id IS NULL"),
        Rule("gold_no_negative_revenue", f"SELECT COUNT(*) FROM {gold_table} WHERE revenue < 0"),
        Rule("gold_grain_unique",
             f"SELECT COUNT(*) FROM (SELECT order_date, store_id, category FROM {gold_table} "
             f"GROUP BY ALL HAVING COUNT(*) > 1)"),
        Rule("gold_not_empty", f"SELECT CASE WHEN COUNT(*) = 0 THEN 1 ELSE 0 END FROM {gold_table}"),
        Rule("quarantine_volume_today",
             f"SELECT CASE WHEN COUNT(*) > 1000 THEN COUNT(*) ELSE 0 END FROM {quarantine_table} "
             f"WHERE _ingested_at >= current_date()", severity="WARN"),
    ]
