# Databricks Exercises

Use **Databricks Free Edition** unless stated otherwise. Items marked 🏢 need your project's dev workspace (ask permission first, and use a sandbox schema).

## Workspace & compute
- **D1.** Tour the workspace: Catalog Explorer, Workspace, Jobs & Pipelines, SQL Editor, Compute. Write one line on what each is for.
- **D2.** Find the compute your notebook runs on. What access mode? What runtime? (🏢 compare 3 project clusters: which are UC-capable?)
- **D3.** `SELECT current_metastore(), current_catalog(), current_schema(), current_user()`. Explain each result.

## Unity Catalog objects
- **D4.** Create `learn_dev` and `learn_prod` catalogs (or schemas if you can't create catalogs), each with `bronze`, `silver`, `gold` schemas.
- **D5.** Create a managed table, then a managed **volume**; upload a CSV to the volume; read it with `/Volumes/...`.
- **D6.** CTAS from bronze to silver; open **Lineage** in Catalog Explorer.
- **D7.** Add a table comment, column comments and a tag; find the table with search.
- **D8.** Create a group (if allowed) or use a colleague's account; grant `USE CATALOG`, `USE SCHEMA`, `SELECT`; test access; then remove `USE SCHEMA` and observe the error.
- **D9.** `SHOW GRANTS` at the catalog/schema/table level; explain inheritance.
- **D10.** `DROP` a managed table, then `UNDROP` it.

## Notebooks, Git & code
- **D11.** Connect a **Git folder** to your fork; create a branch; edit; commit; push; open a PR on GitHub.
- **D12.** Create `src/` Python modules in the Git folder and import them from a notebook (thin entry-point pattern).
- **D13.** Widgets: `catalog`, `run_date`; run the same notebook against `learn_dev` and `learn_prod`.

## Jobs & orchestration
- **D14.** Create a 4-task job (`ingest → silver → gold → dq_check`) with job parameters, a retry on `ingest`, a timeout, and failure notifications.
- **D15.** Pass a row count from `ingest` to `dq_check` with task values.
- **D16.** Break `silver` (wrong table name). Read the error from the run page. Fix it. Use **Repair run**.
- **D17.** Add a **file arrival** or **table update trigger** (if available) instead of a schedule.
- **D18.** Query the job's history from `system.lakeflow.job_run_timeline` (if enabled).

## Secrets & config
- **D19.** With the CLI: create a secret scope and a secret; read it with `dbutils.secrets.get`; try printing it.
- **D20.** Move all environment-specific values from your notebooks into job parameters or a config file.

## Databricks SQL
- **D21.** Write the Phase 2 DQ report as a saved query; build a small dashboard from it.
- **D22.** Create a SQL alert that fires when the DQ failures are > 0.
- **D23.** Open a query's **profile**; find the scan, join and files read/pruned.

## Delta in Databricks
- **D24.** `DESCRIBE HISTORY`/`DETAIL`; time travel; `RESTORE`; `OPTIMIZE` with clustering; `VACUUM` (dry run first).
- **D25.** `DEEP CLONE` and `SHALLOW CLONE` a table into another schema; compare `DESCRIBE DETAIL`.

## Deployment
- **D26.** Install the Databricks CLI; `databricks auth login`; `databricks bundle init`; `validate`; `deploy -t dev`; `run`.
- **D27.** Add a `prod` target pointing at `learn_prod`; deploy both targets from the same code.

## 🏢 Project (read-only unless authorised)
- **D28.** List the jobs that read a given HMS table (lineage, or code search).
- **D29.** Find all clusters/job clusters that aren't UC-capable (cluster list, or `system.compute.clusters`).
- **D30.** List the mounts (`dbutils.fs.mounts()`), and for each, the external location that will replace it.
