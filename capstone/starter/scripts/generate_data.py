"""Generate messy, realistic synthetic retail data for the capstone (pure Python, no Spark needed).

Produces:
  <out>/products/products_<date>.csv          daily product master snapshot (categories change over time)
  <out>/stores/stores.csv                      store reference data
  <out>/pos_orders/<date>/orders_<n>.json      JSON-lines order files, several per day, including:
       - updates (same order_id re-sent with newer updated_at and a new status)
       - duplicates (same record twice, same file or a later file)
       - late arrivals (orders up to 3 days old in today's files)
       - bad records (NULL store_id, zero quantity, bad status, corrupt JSON line)

Usage:
  python scripts/generate_data.py --out ./data --days 30 --start 2026-09-01
  # On Databricks, --out can be a volume path: /Volumes/phoenix_dev/bronze/landing
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

CATEGORIES = ["Electronics", "Furniture", "Grocery", "Apparel", "Stationery"]
STATUSES = ["COMPLETED"] * 8 + ["CANCELLED", "PENDING"]


def write_products(out: Path, day: date, rng: random.Random, n_products: int = 50) -> None:
    folder = out / "products"
    folder.mkdir(parents=True, exist_ok=True)
    with open(folder / f"products_{day:%Y%m%d}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["product_id", "product_name", "category", "unit_price", "snapshot_date"])
        for pid in range(1, n_products + 1):
            # Category drifts for a few products over time -> exercise for SCD2
            category = CATEGORIES[(pid + (day.toordinal() // 10 if pid % 7 == 0 else 0)) % len(CATEGORIES)]
            w.writerow([pid, f"Product {pid}", category, f"{5 + (pid * 13) % 495}.99", day.isoformat()])


def write_stores(out: Path, n_stores: int = 10) -> None:
    folder = out / "stores"
    folder.mkdir(parents=True, exist_ok=True)
    regions = ["UAE", "KSA", "QAT", "OMN"]
    with open(folder / "stores.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["store_id", "store_name", "region"])
        for sid in range(1, n_stores + 1):
            w.writerow([sid, f"Store {sid}", regions[sid % len(regions)]])


def make_order(order_id: int, day: date, rng: random.Random) -> dict:
    ts = datetime(day.year, day.month, day.day, tzinfo=timezone.utc) + timedelta(seconds=rng.randint(0, 86399))
    return {
        "order_id": order_id,
        "store_id": rng.randint(1, 10),
        "product_id": rng.randint(1, 55),          # 51-55 are NOT in the product master -> UNKNOWN category
        "quantity": rng.randint(1, 5),
        "unit_price": round(rng.uniform(5, 500), 2),
        "status": rng.choice(STATUSES),
        "order_ts": ts.strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at": ts.strftime("%Y-%m-%d %H:%M:%S"),
    }


def corrupt(record: dict, rng: random.Random) -> dict:
    kind = rng.choice(["null_store", "zero_qty", "bad_status"])
    r = dict(record)
    if kind == "null_store":
        r["store_id"] = None
    elif kind == "zero_qty":
        r["quantity"] = 0
    else:
        r["status"] = "??"
    return r


def generate(out: Path, start: date, days: int, orders_per_day: int, files_per_day: int, seed: int) -> None:
    rng = random.Random(seed)
    write_stores(out)
    history: list[dict] = []       # previously emitted orders, for updates/late data
    next_id = 1_000_000

    for d in range(days):
        day = start + timedelta(days=d)
        write_products(out, day, rng)
        records: list[dict] = []

        for _ in range(orders_per_day):
            rec = make_order(next_id, day, rng)
            next_id += 1
            records.append(corrupt(rec, rng) if rng.random() < 0.01 else rec)

        # Updates: some earlier orders change status (re-sent with newer updated_at)
        for old in rng.sample(history, k=min(len(history), orders_per_day // 20)):
            upd = dict(old)
            upd["status"] = rng.choice(["CANCELLED", "COMPLETED", "REFUNDED"])
            upd["updated_at"] = f"{day.isoformat()} {rng.randint(0, 23):02d}:{rng.randint(0, 59):02d}:00"
            records.append(upd)

        # Late arrivals: orders dated 1-3 days ago, arriving today
        for _ in range(orders_per_day // 50):
            late_day = day - timedelta(days=rng.randint(1, 3))
            records.append(make_order(next_id, late_day, rng))
            next_id += 1

        # Exact duplicates
        records.extend(rng.sample(records, k=max(1, orders_per_day // 100)))
        rng.shuffle(records)
        history.extend(r for r in records if r.get("store_id") is not None)

        folder = out / "pos_orders" / day.isoformat()
        folder.mkdir(parents=True, exist_ok=True)
        chunk = max(1, len(records) // files_per_day)
        for n in range(files_per_day):
            part = records[n * chunk:(n + 1) * chunk] if n < files_per_day - 1 else records[n * chunk:]
            with open(folder / f"orders_{n:03d}.json", "w", encoding="utf-8") as f:
                for r in part:
                    f.write(json.dumps(r) + "\n")
                if rng.random() < 0.05:
                    f.write('{"order_id": 123, "store_id": \n')   # corrupt JSON line

    print(f"Generated {days} day(s) of data under {out}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", default="./data")
    p.add_argument("--start", default="2026-09-01", type=date.fromisoformat)
    p.add_argument("--days", default=30, type=int)
    p.add_argument("--orders-per-day", default=2000, type=int)
    p.add_argument("--files-per-day", default=4, type=int)
    p.add_argument("--seed", default=42, type=int)
    a = p.parse_args()
    generate(Path(a.out), a.start, a.days, a.orders_per_day, a.files_per_day, a.seed)


if __name__ == "__main__":
    main()
