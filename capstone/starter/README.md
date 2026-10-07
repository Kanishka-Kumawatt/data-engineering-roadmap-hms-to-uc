# Project Phoenix: Capstone Starter

Starter code for the [capstone](../README.md). Some parts work out of the box; parts marked `TODO(learner)` are yours to build.

```
starter/
├── databricks.yml              Asset Bundle (dev / prod targets)
├── resources/phoenix_jobs.yml  2 jobs: daily sales pipeline, migration
├── notebooks/
│   ├── 00_setup_legacy_hms.py  creates target catalog + simulated legacy env + synthetic data
│   ├── 01_bronze.py            Auto Loader → bronze
│   ├── 02_silver.py            clean · quarantine · dedupe · MERGE
│   ├── 03_gold.py              fct_sales_daily via replaceWhere (idempotent, late-data safe)
│   ├── 04_dq_gate.py           rules → ops.dq_results; FAIL stops the job
│   ├── 10_migration_inventory.py  inventory + plan (planner.choose_method)
│   ├── 11_migration_execute.py    dry-run-first executor with audit log
│   └── 12_migration_validate.py   schema / count / row-hash validation
├── src/phoenix/                library code (pure, unit-tested)
│   ├── config.py  transforms.py  quality.py  ops.py
│   └── migration/planner.py  migration/scanner.py
├── sql/views.sql  sql/grants.sql   reviewed, version-controlled DDL/DCL
├── legacy_code/                HMS-era code to scan and convert
├── scripts/generate_data.py    messy synthetic data generator
└── tests/unit/                 pytest (pure-Python tests + local Spark tests)
```

## Run the tests locally

```powershell
cd capstone/starter
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
pytest -q                 # Spark tests auto-skip if Java 17 isn't installed
ruff check src tests
python -m phoenix.migration.scanner legacy_code/   # (after: pip install -e .)  lists what to fix
```

## Run on Databricks (Free Edition or dev)

1. **Git folder:** Workspace → Create → Git folder → your capstone repo URL.
2. Open `notebooks/00_setup_legacy_hms.py` and run it (widgets: `catalog=phoenix_dev`, `legacy_catalog=capstone_legacy`).
3. Run `01` → `02` → `03` (first time: `run_date=2026-09-30`, `lookback_days=30`) → `04`.
4. Migration: `10` → `11` (first with `dry_run=true`, read the audit; then `false`) → `12`.
5. Deploy as jobs: `databricks bundle deploy -t dev` then `databricks bundle run -t dev phoenix_daily_sales`.

> Using a real `hive_metastore` in a dev sandbox? Set `legacy_catalog=hive_metastore`. The planner will then pick
> `SYNC` for external tables, and `DEEP_CLONE` / `CTAS` for managed ones, just as on your project.

## Known simplifications (good discussion points for your ADRs)
- One product per order. Real POS data has order lines.
- Products are SCD1 in Silver; making them SCD2 is a stretch task.
- Gold joins to the *current* product category, not the category valid at order time.
- Grants use example group names. Create them, or adapt them to your workspace.
