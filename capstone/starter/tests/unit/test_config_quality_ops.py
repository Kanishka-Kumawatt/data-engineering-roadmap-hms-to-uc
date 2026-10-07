from datetime import datetime, timezone

import pytest

from phoenix.config import PipelineConfig, validate_identifier
from phoenix.ops import run_record
from phoenix.quality import Rule, evaluate, failures


def test_table_builds_three_level_name():
    assert PipelineConfig("phoenix_dev").table("gold", "fct_sales_daily") == "phoenix_dev.gold.fct_sales_daily"


def test_paths_follow_catalog():
    cfg = PipelineConfig("phoenix_prod")
    assert cfg.landing_root == "/Volumes/phoenix_prod/bronze/landing"
    assert cfg.checkpoint_root.startswith("/Volumes/phoenix_prod/")


@pytest.mark.parametrize("bad", ["", "Phoenix", "a-b", "x; DROP TABLE y", "1abc", None])
def test_invalid_identifiers_rejected(bad):
    with pytest.raises(ValueError):
        validate_identifier(bad)


def test_lookback_bounds():
    with pytest.raises(ValueError):
        PipelineConfig("phoenix_dev", lookback_days=90)


def test_rule_evaluation_and_failures():
    fail_rule, warn_rule = Rule("unique", "SELECT 0"), Rule("volume", "SELECT 0", severity="WARN")
    results = [evaluate(fail_rule, 0), evaluate(fail_rule, 3), evaluate(warn_rule, 7)]
    assert [r.status for r in results] == ["PASS", "FAIL", "WARN"]
    assert failures(results) == ["unique: 3 violating rows"]


def test_rule_rejects_unknown_severity():
    with pytest.raises(ValueError):
        Rule("x", "SELECT 0", severity="INFO")


def test_run_record_truncates_message_and_validates_status():
    rec = run_record("r1", "daily_sales", "silver", "FAILED", datetime.now(timezone.utc), message="x" * 5000)
    assert len(rec[-1]) == 1000
    with pytest.raises(ValueError):
        run_record("r1", "j", "t", "OK", datetime.now(timezone.utc))
