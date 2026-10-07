# Hands-on Projects

These build on each other. Every project lives in your fork (or its own repo) with a README covering **what, why, how to run, how to test and what I learned**.

| # | Project | Week | Skills | Done when |
|---|---|---|---|---|
| 1 | **Platform Before & After** | 1 | Fundamentals, architecture | Two diagrams + explanation of your real project, reviewed by a senior |
| 2 | **SQL DQ report** | 2 | Joins, anti joins, aggregates | One query → `(check, failed_rows)` for 5 checks |
| 3 | **Monthly customer metrics + reconciliation** | 3 | CTEs, windows, full outer joins | Gold-style model + MATCH/MISMATCH/MISSING classifier |
| 4 | **Migration Statement Generator** | 4 | Python packaging, functions, tests, config | `pip install -e .`, CLI produces `plan.csv` + `.sql`, ≥10 tests pass |
| 5 | **Legacy code scanner** | 4 | Python files, regex, reporting | Report of `/mnt`, `dbfs:/`, 2-level names, RDD/`input_file_name` usages |
| 6 | **`orders_daily` PySpark job** | 6 | Spark I/O, windows, broadcast, Delta | Job + README explaining the stages/shuffles observed |
| 7 | **SCD2 customer dimension** | 7 | Delta MERGE, SCD2, tests | 3 batches applied; assertions: one current row per key, no overlaps |
| 8 | **Parameterised 4-task Databricks Job** | 7 | Jobs, widgets, task values, retries, alerts | Runs in dev & "prod" catalogs; RUNBOOK written; repair-run demonstrated |
| 9 | **Sandbox HMS→UC migration** | 8–9 | Everything in Phase 7 | Inventory → plan → execute → validation report → grants → rollback plan |
| 10 | **Daily Sales pipeline** | 10–11 | Pipeline dev, Auto Loader, MERGE, DQ, modeling | Bronze/Silver/Gold + star schema, idempotent, late-data aware, tested |
| 11 | **DQ framework + migration validator** | 12 | Testing, reconciliation | Reusable `run_rules` + `compare_tables`; results tables + report |
| 12 | **Bundle + CI** | 12–13 | DABs, GitHub Actions | `bundle deploy -t dev/prod`; PR checks run lint + unit tests |
| 13 | **Performance investigation write-up** | 13–14 | Spark UI, Delta layout | Before/after numbers for skew + small files; the method documented |
| 14 | **Troubleshooting drill book** | 14–15 | All | 13 scenarios reproduced, each with symptom → cause → fix → prevention |
| 15 | **Capstone** | 13–16 | Everything | See [capstone/README.md](../capstone/README.md) |

## Optional extras (after week 16)
- **API ingestion pipeline:** a public API (e.g. weather, exchange rates) → Bronze JSON → Silver → Gold, with retries, secrets and a daily job.
- **CDC pipeline:** simulate inserts/updates/deletes from a source table → Change Data Feed → downstream SCD2.
- **Declarative pipeline version** of the Daily Sales pipeline, with expectations.
- **Cost dashboard:** `system.billing.usage` per job/cluster, with an alert for spikes.
- **Governance demo:** PII tags + column masks + row filters + an audit query proving who accessed what.
