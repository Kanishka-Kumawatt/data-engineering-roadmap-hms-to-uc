import json
from datetime import date

from generate_data import generate


def test_generator_produces_messy_but_parseable_data(tmp_path):
    generate(tmp_path, start=date(2026, 9, 1), days=3, orders_per_day=500, files_per_day=2, seed=1)

    assert (tmp_path / "stores" / "stores.csv").exists()
    assert len(list((tmp_path / "products").glob("*.csv"))) == 3

    records = []  # (delivery folder date, record)
    for f in (tmp_path / "pos_orders").rglob("*.json"):
        for line in f.read_text(encoding="utf-8").splitlines():
            try:
                records.append((f.parent.name, json.loads(line)))
            except json.JSONDecodeError:
                pass  # corrupt lines are intentional (Bronze/Silver must cope with them)

    ids = [r["order_id"] for _, r in records]
    assert len(ids) > len(set(ids)), "expected duplicates/updates for dedupe practice"
    assert any(r["store_id"] is None or r["quantity"] == 0 or r["status"] == "??" for _, r in records)
    assert any(r["order_ts"][:10] < folder for folder, r in records), "expected late-arriving orders"
    assert any(r["updated_at"] > r["order_ts"] for _, r in records), "expected order updates"
