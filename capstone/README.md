# Capstone — "Project Phoenix": Migrate a Legacy Retail Platform to Unity Catalog and Build Its First Governed Pipeline

**Weeks:** 13–16 (prep work starts earlier) · **Effort:** ~35–40 h
**Starter code:** [capstone/starter/](starter/)

> **Mentor note:** This capstone deliberately mirrors your real project. You inherit a legacy, HMS-style environment, migrate it to Unity Catalog properly, then build a new production-grade pipeline on the governed platform. When you're done, you'll have a story for every interview question in this repo: "In my capstone, I…".

---

## 1. The scenario

**Contoso Retail** runs its analytics on a Databricks workspace that still uses the Hive Metastore. The platform team has created a Unity Catalog metastore. Your squad has been asked to:

1. **Migrate** the `retail` legacy schema (managed tables, path-based Parquet data on a mount, a view, legacy notebooks) to UC, with validated data, correct permissions and updated code.
2. **Build** a new **Daily Sales Performance** pipeline (ticket DE-142, see [Phase 8](../phases/phase-08-pipeline-development.md)) on UC: Bronze → Silver → Gold, incremental, tested, deployed with CI/CD, monitored and documented.

### Business requirement (you'll refine it in your design doc)
> Sales leadership needs daily revenue, orders and average order value by store and product category, ready by 07:00 Dubai time, accessible to the BI group. Orders arrive as JSON files every 15 minutes, can be updated (status changes), and can arrive up to 3 days late. The product master arrives as a daily CSV.

### Environment

| Real project | Capstone simulation (Free Edition) |
|---|---|
| `hive_metastore.retail` | `capstone_legacy.retail` (created by [00_setup_legacy_hms.py](starter/notebooks/00_setup_legacy_hms.py)) |
| DBFS-root managed tables | Managed Delta tables in the legacy catalog → migrate with **DEEP CLONE** |
| External Parquet on `/mnt/...` | Parquet files in a legacy volume → migrate with **CTAS** |
| View with legacy names | `v_store_summary` → **recreate** with 3-level names |
| Legacy notebooks | [starter/legacy_code/](starter/legacy_code/) → scan and **convert** |
| Workspace groups | Account groups you create (or simulate with your user + a colleague) |

If you have a **dev sandbox with a real `hive_metastore`**, set the `legacy_catalog` parameter to `hive_metastore` and do the migration for real. SYNC then becomes available for external tables.

---

## 2. Target architecture

```
                     ┌──────────────────────── Unity Catalog ────────────────────────┐
 Legacy (HMS-style)  │  phoenix_<env>                                                │
 capstone_legacy     │   ├── bronze   pos_orders (Auto Loader) · products · stores    │
  .retail  ──migrate─┼─▶ ├── legacy   migrated tables (customers, stores, sales_hist) │
                     │   ├── silver   orders (MERGE) · orders_quarantine · products   │
 JSON/CSV files ─────┼─▶ ├── gold     fct_sales_daily · dim_store · dim_product · dim_date│
 (landing volume)    │   └── ops      pipeline_runs · dq_results · migration_*        │
                     └──────────────────────────────────────────────────────────────┘
 Grants: grp_phoenix_engineers (dev: ALL on catalog) · sp/job identity (MODIFY bronze/silver/gold/ops)
         grp_phoenix_bi (USE CATALOG + USE SCHEMA + SELECT on gold only)
 Deploy: Git → PR → CI (ruff + pytest) → bundle deploy -t dev / prod
 Job:    bronze → silver → gold → dq_gate  (05:30 Asia/Dubai, retries, timeout, failure alerts)
```

---

## 3. Deliverables & acceptance criteria

### Part A — Foundations (week 13)
| # | Deliverable | Acceptance |
|---|---|---|
| A1 | Repo from [starter/](starter/), your own GitHub repo | README explains what/why/how to run |
| A2 | CI on PRs | GitHub Actions runs `ruff` + `pytest`; a deliberately failing PR is blocked |
| A3 | Environment setup | `00_setup_legacy_hms` creates legacy + `phoenix_dev` objects; idempotent (safe to re-run) |
| A4 | Synthetic data | `scripts/generate_data.py` produces 30 days of orders with duplicates, updates, late and bad records |

### Part B — Migration (week 14)
| # | Deliverable | Acceptance |
|---|---|---|
| B1 | **Inventory** (`10_migration_inventory`) | `ops.migration_inventory` lists every legacy object with type, format, location |
| B2 | **Plan** | `ops.migration_plan` with method per object (via `planner.choose_method`), wave, owner; planner unit-tested |
| B3 | **Execute** (`11_migration_execute`) | Dry run by default; every statement + result logged to `ops.migration_audit`; re-runnable |
| B4 | **Views & functions** | Recreated with 3-level names, in dependency order (`planner.creation_order`) |
| B5 | **Grants & ownership** | Grants as a version-controlled SQL file; objects owned by a group; positive and negative access tests documented |
| B6 | **Code conversion** | `legacy_code/` notebooks converted (no `/mnt`, no 2-level names, no `input_file_name`, no RDD); the scanner reports 0 findings |
| B7 | **Validation** (`12_migration_validate`) | Object, schema, count and fingerprint checks for all tables; EXCEPT for 1 critical table; report in `docs/validation-report.md` with ≥1 explained difference |
| B8 | **Runbook + rollback plan** | `docs/migration-runbook.md` from [the checklist](../checklists/migration-runbook-checklist.md), including rollback for each method used |

### Part C — New pipeline (weeks 15–16)
| # | Deliverable | Acceptance |
|---|---|---|
| C1 | **Design doc** | Definitions, sources, grain/keys per table, incremental strategy, DQ rules, security, SLA |
| C2 | **Bronze** | Auto Loader `availableNow`; `_ingested_at`, `_source_file`; checkpoint in a volume |
| C3 | **Silver** | Typed, cleaned, deduped, MERGE on `order_id` with `updated_at` guard; quarantine with a reason |
| C4 | **Gold** | `fct_sales_daily` (grain: date × store × category) rebuilt for a look-back window with `replaceWhere`; `dim_date`; **stretch:** `dim_product` SCD2 |
| C5 | **Idempotency & late data** | Running the job twice gives the same Gold; a 3-day-late order updates the right date only (tested) |
| C6 | **Tests** | ≥12 unit tests (transforms, planner, quality, config); 1 integration test notebook |
| C7 | **DQ gate** | ≥6 rules (FAIL/WARN) → `ops.dq_results`; a FAIL stops the job |
| C8 | **Deployment** | `databricks.yml` with `dev` and `prod` targets; deploys and runs from the CLI |
| C9 | **Orchestration** | 4-task job, scheduled, retries, timeout, failure notification, `run_date` / `lookback_days` parameters for backfill |
| C10 | **Monitoring** | `ops.pipeline_runs`; a Databricks SQL dashboard (runs, durations, rows, DQ, freshness); 1 SQL alert |
| C11 | **Governance** | Comments on all Gold tables/columns; PII tag on any PII column; BI group can read Gold only |
| C12 | **Docs** | README, RUNBOOK (re-run, backfill, top 5 failures), 2+ ADRs, ERD |

### Part D — Demo (week 16)
A 15-minute recorded or live demo: architecture → migration (plan, validation report) → pipeline run → break something live (e.g. a duplicate source key) and show how you detect and fix it → what you'd improve.

---

## 4. Suggested sequence

1. **Set up the repo** (copy `starter/` into a new GitHub repo, push, enable CI).
2. **Run `00_setup_legacy_hms`** in Free Edition (Git folder). Explore the legacy objects as if you'd just joined the project.
3. **Migration, Phase A (before):** inventory → plan → dependencies → grants mapping → runbook draft → baselines.
4. **Migration, Phase B (during):** execute dry run → review → execute → views → grants → code conversion.
5. **Migration, Phase C (validate):** run the validator → fix → report.
6. **Pipeline:** design doc → generate data → Bronze → Silver (+ tests) → Gold (+ tests) → DQ gate → bundle → job → dashboard and alert.
7. **Break it** (at least 5 scenarios from [Phase 14](../phases/phase-14-troubleshooting.md)) and write error-log entries.
8. **Docs and demo.**

## 5. Break-it list (prove your pipeline is robust)
- [ ] Same file delivered twice → no duplicates in Silver/Gold
- [ ] One batch contains the same `order_id` twice → MERGE still succeeds
- [ ] A file with a new column → lands in `_rescued_data`; documented decision
- [ ] A file with corrupt JSON lines → bad records handled, job continues or fails as designed
- [ ] An order 3 days late → only that date's Gold row changes
- [ ] Revoke the BI group's `USE SCHEMA` → the dashboard fails → fix it → add a permission test
- [ ] Run the job with `run_date` = 10 days ago → backfill works
- [ ] Remove the dedupe step → watch the MERGE fail → restore it

## 6. Grading yourself (rubric)

| Area | Needs work | Good | Production-ready |
|---|---|---|---|
| Migration | Tables copied | Methods justified, validated | Runbook, rollback, audit trail, explained differences, code converted |
| Pipeline | Runs once | Incremental and tested | Idempotent, late-data safe, DQ gate, monitored, backfillable |
| Code quality | Notebook scripts | Modules + tests | Typed, logged, config-driven, CI-enforced |
| Governance | Default permissions | Group-based grants | Least privilege, ownership, tags/comments, permission tests |
| Docs | README only | README + runbook | Design doc, ADRs, validation report, demo |

## 7. Stretch goals
- Rebuild Bronze/Silver as a **Lakeflow Declarative Pipeline** with expectations and `AUTO CDC` (SCD2).
- Row filter by store region + column mask on customer emails.
- Cost query per job run from `system.billing.usage`.
- A `preflight` task that checks grants and external locations before the job runs.
- Use **UCX** in a real dev workspace and compare its assessment with your inventory.
