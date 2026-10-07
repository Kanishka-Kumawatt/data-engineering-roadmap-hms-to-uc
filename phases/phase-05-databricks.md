# Phase 5 — Databricks from a Developer's Perspective

**Weeks:** 5–7 · **Time:** ~18 h (4 h theory, 14 h hands-on)
**Goal:** Use Databricks the way a delivery team does: Git-backed code, parameterised jobs, secrets, environments, monitoring and debugging failed runs.

> **Mentor note:** Clicking around a notebook is easy. The professional skill is to make the same code run in dev, QA and prod **without editing it**, scheduled, monitored, and recoverable when it fails at 3 a.m. Learn each component by asking "how is this used in a real project?"
>
> *Naming note: Databricks renames products often. "Workflows" are now **Lakeflow Jobs**, "DLT" is now **Lakeflow Declarative Pipelines**, "Repos" are now **Git folders**, and "Shared"/"Single user" access modes are now **Standard**/**Dedicated**. You'll hear both sets of names at work.*

---

## Component tour, and how each is used in a real project

| Component | What it is | Real-project usage | Common mistake |
|---|---|---|---|
| **Workspace** | The web environment: folders, notebooks, jobs, compute | One workspace per environment (dev/qa/prod), or shared with catalogs per env | Personal code in `/Users/you/` running prod jobs |
| **Notebooks** | Cells of Python/SQL/Scala/Markdown | Exploration, thin "entry points" that call library code | 2,000-line notebooks nobody can test |
| **Compute: all-purpose clusters** | Interactive clusters you attach notebooks to | Development | Leaving them running all weekend (cost!) |
| **Compute: job clusters** | Created per job run, terminated afterwards | **Production jobs**: cheaper and isolated | Running prod jobs on all-purpose clusters |
| **Serverless compute** | Databricks-managed compute for notebooks/jobs/SQL | Fast start, no cluster tuning | Assuming every Spark config and API works (some don't) |
| **SQL warehouses** | Compute for SQL/BI | Dashboards, analysts, Databricks SQL, validation queries | — |
| **Access mode** | **Standard** (multi-user, UC-isolated) / **Dedicated** (single user or group) | **UC requires one of these**; "No isolation shared" can't access UC | Using a legacy cluster for UC tables → errors |
| **Jobs (Lakeflow Jobs)** | Orchestrated tasks with DAG, schedule, retries, alerts | Every production pipeline | No retries, no alerts, no timeout |
| **Git folders (Repos)** | Git-backed folders in the workspace | Develop on a branch, PR, merge | Editing directly on `main` |
| **Libraries** | PyPI packages, wheels, JARs | Your project's own wheel + dependencies | Installing JARs from DBFS (blocked under UC; use Volumes/allowlist) |
| **Secrets** | Secret scopes (Databricks or Key Vault-backed) | DB passwords, API tokens | Hard-coded passwords, or printing secrets |
| **Databricks SQL** | SQL editor, queries, dashboards, alerts | Validation, reporting, SQL-based Gold | — |
| **Catalog Explorer** | UI for UC objects, permissions, lineage | Discovery, grants, lineage checks | — |
| **Asset Bundles (DABs)** | YAML-defined jobs/pipelines deployed by CLI | CI/CD (Phase 12) | Clicking jobs together in the UI for prod |

## Key developer techniques

### Parameters (widgets / job parameters)
```python
dbutils.widgets.text("catalog", "learn_dev")
dbutils.widgets.text("run_date", "")
catalog  = dbutils.widgets.get("catalog")
run_date = dbutils.widgets.get("run_date") or str(datetime.date.today())
spark.sql(f"USE CATALOG {catalog}")
```
Same notebook; dev passes `learn_dev`, prod passes `learn_prod`. **That's the whole idea of environment promotion.**

### Secrets
```python
pwd = dbutils.secrets.get(scope="erp-jdbc", key="password")    # shows as [REDACTED] if printed
df = (spark.read.format("jdbc")
      .option("url", "jdbc:sqlserver://erp-host:1433;database=erp")
      .option("dbtable", "dbo.orders").option("user", "svc_reader").option("password", pwd).load())
```

### Passing values between job tasks
```python
dbutils.jobs.taskValues.set(key="rows_loaded", value=n)                  # task A
n = dbutils.jobs.taskValues.get(taskKey="ingest", key="rows_loaded")     # task B
```

### Notebook entry point calling library code (production pattern)
```python
# notebooks/run_silver_orders.py  (thin)
from retail_pipeline.silver import build_silver_orders
from retail_pipeline.config import load_config
cfg = load_config(dbutils.widgets.get("env"))
build_silver_orders(spark, cfg)
```

## Development vs production environments

```
DEV                         QA / TEST                      PROD
catalog: retail_dev         catalog: retail_qa             catalog: retail_prod
you + team can write        CI service principal writes    ONLY prod service principal writes
all-purpose clusters        job clusters                   job clusters / serverless
feature branches            release branch / main          main (tagged)
synthetic/sampled data      prod-like data                 real data
```
In UC, environments are usually **separate catalogs** (sometimes also separate workspaces), bound to workspaces with **workspace-catalog binding**. Prod jobs **run as a service principal**, not as a person.

## Monitoring jobs

- **Job run page:** status, duration, task DAG, per-task logs and output, repair run.
- **Notifications:** email/Slack/Teams/webhook on start/success/failure/**duration threshold**.
- **System tables:** `system.lakeflow.jobs`, `system.lakeflow.job_run_timeline`, `system.lakeflow.job_task_run_timeline` (query run history with SQL); `system.billing.usage` (cost).
- **Data-level monitoring:** row counts, freshness and quality results written to an audit table (Phase 8), and Lakehouse Monitoring / data quality monitoring.

## Debugging a failed job: the routine

1. **Open the failed run → the failed task → read the error from the bottom up.** Find the first meaningful exception ("Caused by").
2. **What changed?** Code (Git history), data (a new file or schema), permissions (UC grants), compute (DBR version, access mode), or upstream (dependency late/failed).
3. **Is it reproducible?** Re-run the notebook interactively in dev with the same parameters.
4. **Check the cluster driver logs** (stdout/stderr/log4j) for OOM, library conflicts and init-script failures.
5. **Fix → test in dev → PR → deploy → use "Repair run"** to re-run only failed tasks.
6. **Write it in your error log** and add prevention (a test, check or alert).

---

## How this connects to HMS→UC

- **Clusters must be upgraded:** UC-capable access mode + a supported DBR version. Old "No isolation shared" clusters and legacy Table ACL clusters are a migration item.
- **Jobs must be updated:** new table names (3-level), `/mnt` → Volumes/External Locations, run-as service principal, cluster policies.
- **Default catalog:** a workspace (or compute) has a default catalog. Unqualified 2-level names resolve against it, so a job that worked against `hive_metastore` may silently hit a different catalog afterwards.
- **Libraries/init scripts** stored on DBFS need to move to **Volumes** or workspace files, and JARs/init scripts on Standard access mode need to be on the **allowlist**.

## Hands-on

1. Free Edition: create catalog/schema/table, browse them in Catalog Explorer, and look at the lineage after a CTAS.
2. Connect a **Git folder** to your fork of this repo; create a branch, edit, commit and push from the UI.
3. Build a notebook with widgets `catalog` and `run_date`, and run it with different values.
4. Create a **multi-task job**: `ingest` → `silver` → `gold` → `quality_check`, with task values, a retry on `ingest`, a timeout and a failure email.
5. Break it on purpose (wrong table name), then fail → read the error → fix → **repair run**.
6. Query `system.lakeflow.job_run_timeline` (if available) for your job's run history.
7. Create a secret scope (via CLI, where allowed) and read a secret. Try printing it and see `[REDACTED]`.

## Build

A **parameterised 4-task Databricks Job** for the retail dataset, with code in a Git folder, notebooks as thin entry points, config by parameter, failure notification and retries, plus a `RUNBOOK.md` describing how to re-run it, backfill a date and handle common failures.

## Troubleshooting

| Problem | Investigate |
|---|---|
| Notebook can't see UC tables | Cluster access mode / DBR; `SELECT current_metastore()` |
| `ModuleNotFoundError` in a job but works interactively | Library installed on the interactive cluster but not on the job cluster / environment |
| Job works for you, fails as service principal | Grants given to you, not the SP. Check `SHOW GRANTS` |
| Job slow to start | Cluster start time → pools or serverless |
| Init script failed | Driver logs; script location must be supported (workspace files/Volumes) under UC |
| `dbutils` not defined | Running as a plain Python file outside Databricks → use `databricks-sdk` / DB Connect |

## After this phase you should be able to explain

- [ ] All-purpose vs job vs serverless compute, and when to use each
- [ ] Standard vs Dedicated access mode, and why UC needs them
- [ ] How the same code runs in dev and prod (parameters, catalogs, service principals)
- [ ] How secrets are stored and used
- [ ] How you debug and repair a failed multi-task job

## Beginner vs experienced

| Beginner | Experienced |
|---|---|
| Runs notebooks on an interactive cluster | Ships jobs via bundles, on job clusters/serverless, with policies, run as SPs |
| Re-runs the whole job on failure | Uses repair run, idempotent tasks and backfill parameters |
| Checks the UI when told something failed | Has alerts and system-table dashboards and notices first |

Exercises: [exercises/databricks-exercises.md](../exercises/databricks-exercises.md)

## Interview questions

1. Difference between an all-purpose cluster and a job cluster?
2. What access modes support Unity Catalog?
3. How do you parameterise a notebook for multiple environments?
4. How do you manage secrets in Databricks?
5. How would you design a multi-task job with retries and alerts?
6. A job fails only in prod. How do you investigate?
7. What are Databricks system tables, and what would you use them for?
