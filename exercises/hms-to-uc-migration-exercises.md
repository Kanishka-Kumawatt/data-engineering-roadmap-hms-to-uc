# HMS → Unity Catalog Migration Exercises

> ⚠️ Do these in **local Spark**, **Free Edition**, or a **sandbox schema in dev with your lead's permission**. Never on prod, and never on project tables you don't own.

Where you can't use a real `hive_metastore` (e.g. Free Edition), **simulate it**: create a `legacy` catalog or schema with 2-level-style naming, external tables on a volume path, and "legacy" code. The capstone's [setup script](../capstone/starter/notebooks/00_setup_legacy_hms.py) does this for you.

## A. Understand HMS (Week 7)
- **M1.** Local Spark with Hive support: create a database, a managed table and an external table (with `LOCATION`). `DESCRIBE EXTENDED` both. Drop both. Which files survive? Why?
- **M2.** In local Spark, find the Derby `metastore_db` folder, and explain in 3 sentences what it stores and what it doesn't.
- **M3.** 🏢 Pick one HMS schema at work. For 10 tables, record: type, provider (format), location, whether it's on DBFS root / a mount / a direct cloud path, size, and last modified.

## B. Understand UC (Week 7)
- **M4.** Draw the UC hierarchy for your project's target design (catalogs, schemas, external locations, groups).
- **M5.** Free Edition: create a catalog/schema, a managed table and a volume; grant to a group; test the positive and negative cases.
- **M6.** 🏢 Trace one external location end to end: storage account/container → access connector/IAM role → storage credential → external location → grants.

## C. Plan (Week 8)
- **M7.** Write the HMS inventory script ([Phase 7 §11.1](../phases/phase-07-hms-to-unity-catalog.md#111-inventory-first)) and run it on a (sandbox/simulated) schema.
- **M8.** Classify every object with the decision matrix → `plan.csv` (`source, target, object_type, method, wave, owner, notes`).
- **M9.** Build a dependency list: for each view, parse its SQL (`SHOW CREATE TABLE`) and list the referenced tables. Produce a creation order (topological sort, in Python).
- **M10.** List all code locations (notebooks/jobs) that reference each table (scanner from Phase 3, P13).
- **M11.** Map a set of HMS grants (make up 10 realistic ones, e.g. `USAGE`, `SELECT`, `READ_METADATA`, `MODIFY`, `ANY FILE`) to UC grants. Note the ones that can't map 1:1.
- **M12.** Write a one-page **migration plan** for the schema: waves, methods, freeze window, validation, rollback, communication.

## D. Execute (Week 8)
- **M13.** `SYNC SCHEMA ... DRY RUN`, and read every status. (Simulated: register external tables in the target with `CREATE TABLE ... LOCATION`.)
- **M14.** Migrate an external Delta table in place. Then `DESCRIBE DETAIL` both: same location?
- **M15.** DEEP CLONE a managed Delta table. Compare `DESCRIBE HISTORY` on source and target. What happened to the history?
- **M16.** CTAS a Parquet/CSV table into a UC managed Delta table. Re-apply the comments and properties that were lost.
- **M17.** Recreate 3 views (one depending on another) with 3-level names, in dependency order.
- **M18.** Recreate a SQL UDF as a UC function; use it in a view.
- **M19.** Apply the grants from M11 at the schema level where possible; set ownership to a group.
- **M20.** Convert 3 "legacy" notebooks: 2-level names → parameterised 3-level; `/mnt/` → `/Volumes/`; `input_file_name()` → `_metadata.file_path`; an RDD operation → DataFrame.
- **M21.** Make the executor log every statement + status + error to `ops.migration_audit`.

## E. Validate (Week 9)
- **M22.** Object validation: plan vs `information_schema.tables` (missing, wrong type, wrong location).
- **M23.** Schema validation: column name/type/order diff between source and target, for every table.
- **M24.** Data validation: counts + fingerprints for all tables; `EXCEPT ALL` both ways for 2 critical tables; hash-by-partition for 1 big table.
- **M25.** Permission validation: positive (analyst can read gold) and negative (analyst cannot read PII) tests, run *as* the principal.
- **M26.** Produce a **validation report** (Markdown table: object, check, source, target, status, explanation). Include one "explained difference".

## F. Troubleshoot (Week 9) — reproduce and fix each
- **M27.** `TABLE_OR_VIEW_NOT_FOUND` caused by a 2-level name + a changed current catalog.
- **M28.** `PERMISSION_DENIED` caused by a missing `USE SCHEMA`.
- **M29.** A view that silently reads the *wrong* table (same 2-level name exists in two catalogs).
- **M30.** "Overlapping paths": two external tables where one path is nested in the other. What happens when you register both? Design a fix.
- **M31.** Counts drift: the source keeps receiving writes after your clone. Detect it with `DESCRIBE HISTORY`, then re-sync incrementally.
- **M32.** A job that works as you but fails as a service principal (or as a colleague).
- **M33.** An Auto Loader stream whose source path changed: observe the reprocessing, then design a safe cutover.

## G. Post-migration (Week 9)
- **M34.** Write the cutover checklist for your sandbox schema (freeze, final sync, switch, verify, communicate).
- **M35.** Write a query against `system.access.audit` (if available) that finds any access to `hive_metastore` in the last 7 days.
- **M36.** Write a rollback plan for each method you used (SYNC, CLONE, CTAS), including what happens to writes made after cutover.
- **M37.** Write a decommission checklist: drop HMS objects (after sign-off), remove mounts, remove keys from configs, update docs.
- **M38.** Present your sandbox migration (10 min) to a colleague: what you did, what broke, how you proved it worked.
