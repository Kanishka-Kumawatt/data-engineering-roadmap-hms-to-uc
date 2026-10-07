# Phase 15 — What You Didn't Ask About (But Will Need)

**Weeks:** Spread across the plan (see the schedule) · **Time:** ~12 h total
**Goal:** Fill the gaps that commonly trip up engineers on real Databricks/UC projects.

> **Mentor note:** None of these needs to be mastered in 3 months. Each section gives you enough to recognise the topic, ask good questions and not be surprised. Several (cloud IAM, Auto Loader, system tables) come up in HMS→UC work almost immediately.

---

## 1. Cloud storage and identity basics (week 7, ~3 h)

**Why:** UC permissions sit on top of cloud permissions. Half of "UC access issues" are really cloud IAM or network issues.

| Concept | Azure | AWS | GCP |
|---|---|---|---|
| Object storage | ADLS Gen2 (`abfss://container@account.dfs.core.windows.net/path`) | S3 (`s3://bucket/path`) | GCS (`gs://bucket/path`) |
| Identity used by UC | Access Connector (managed identity) | IAM role | Service account |
| Typical role | Storage Blob Data Contributor/Reader | S3 read/write policy | Storage Object Admin/Viewer |
| Network controls | Storage firewall, private endpoints, VNet injection | Bucket policies, VPC endpoints | VPC-SC |
| Secrets store | Key Vault | Secrets Manager | Secret Manager |

**Learn:** the path formats, what hierarchical namespace means (ADLS), the difference between RBAC and ACLs on ADLS, and why private networking causes "it works from my laptop but not from Databricks" issues.
**Practice:** In a free cloud account (or with the platform team), read through how one external location on your project is set up end to end: storage account → container → access connector → role assignment → storage credential → external location → grant.

## 2. Auto Loader and Structured Streaming (week 10, ~3 h)

- **Structured Streaming:** treats a stream as an unbounded table. Key ideas: **checkpoint** (tracks progress and state), **trigger** (`availableNow=True` for incremental batch, `processingTime='1 minute'` for continuous), **output mode** (append/update/complete), **watermarks** for late data in stateful operations.
- **Auto Loader (`cloudFiles`):** incrementally ingests new files from cloud storage, exactly once, with schema inference/evolution and a `_rescued_data` column. The standard Bronze ingestion tool. Example in [Phase 8](phase-08-pipeline-development.md).
- **Migration relevance:** checkpoints and schema locations on `/mnt` or DBFS must move, and the source path change matters (Phase 7, scenario 7).
- **Practice:** Ingest files with Auto Loader in `availableNow` mode; add files; re-run; add a file with a new column; delete the checkpoint and observe the reprocessing.

## 3. Lakeflow Declarative Pipelines (formerly Delta Live Tables) (week 11, ~2 h)

A declarative way to build pipelines: you define tables (`CREATE OR REFRESH STREAMING TABLE`, `MATERIALIZED VIEW`), and Databricks handles orchestration, retries, dependencies, data-quality **expectations** and CDC (`AUTO CDC ... STORED AS SCD TYPE 2`).
- **When teams use it:** standardised medallion pipelines with built-in quality, and less orchestration code.
- **Trade-off:** less control and some platform-specific constructs. You should understand both the "plain jobs + notebooks" way (this roadmap's default) and the declarative way.
- **Practice:** Rebuild your Bronze → Silver of the capstone as a declarative pipeline with 2 expectations.

## 4. Fine-grained governance and PII (week 9, ~2 h)

```sql
-- Column mask: only the HR group sees full emails
CREATE FUNCTION gov.masks.mask_email(email STRING) RETURN
  CASE WHEN is_account_group_member('grp_hr') THEN email
       ELSE concat('***@', split(email, '@')[1]) END;
ALTER TABLE hr_prod.core.employees ALTER COLUMN email SET MASK gov.masks.mask_email;

-- Row filter: users see only their region
CREATE FUNCTION gov.filters.region_filter(region STRING) RETURN
  is_account_group_member('grp_admins') OR is_account_group_member(concat('grp_region_', region));
ALTER TABLE sales_prod.orders.fct_orders SET ROW FILTER gov.filters.region_filter ON (region);

-- Tags for discovery & policy
ALTER TABLE hr_prod.core.employees ALTER COLUMN email SET TAGS ('pii' = 'email');
```
Learn: PII classification, least privilege, GDPR/"right to be forgotten" (DELETE + VACUUM so deleted data is actually removed from storage), and tag-based (ABAC) policies.
**Migration relevance:** HMS projects often implemented masking with **dynamic views**. In UC you can keep those, or move to masks/filters.

## 5. System tables for operations (week 12, ~1.5 h)

| Table | Use |
|---|---|
| `system.access.audit` | Who did what (grants, reads, failures) |
| `system.access.table_lineage` / `column_lineage` | Dependencies, impact analysis, who reads a table |
| `system.lakeflow.jobs`, `job_run_timeline`, `job_task_run_timeline` | Job history, durations, failures |
| `system.billing.usage` + `system.billing.list_prices` | Cost per job/workspace/SKU |
| `system.compute.clusters` | Cluster configs (find non-UC access modes!) |
| `system.query.history` | SQL warehouse queries |
| `system.information_schema.*` | Objects across catalogs |

(Availability depends on your account; system schemas may need to be enabled by an admin.)

```sql
-- Most expensive jobs last 30 days (approximate list-price cost)
SELECT u.usage_metadata.job_id, SUM(u.usage_quantity * p.pricing.default) AS approx_cost
FROM system.billing.usage u
JOIN system.billing.list_prices p
  ON u.sku_name = p.sku_name AND u.usage_start_time >= p.price_start_time
 AND (p.price_end_time IS NULL OR u.usage_start_time < p.price_end_time)
WHERE u.usage_date >= current_date() - 30 AND u.usage_metadata.job_id IS NOT NULL
GROUP BY 1 ORDER BY 2 DESC LIMIT 20;
```

## 6. Cost awareness (week 13, ~1 h)

- All-purpose compute is more expensive than job compute. Don't run prod on interactive clusters.
- Auto-termination on dev clusters (e.g. 30–60 min). Use cluster policies.
- Right-size: measure before scaling up. Spot/preemptible workers for fault-tolerant jobs.
- Serverless: no idle cost, fast start. Compare per job.
- Storage: VACUUM old versions, and drop unused tables (after confirming via lineage/audit).
- **Migration:** DEEP CLONE/CTAS duplicates storage until HMS is decommissioned, so plan the cleanup.

## 7. Documentation and communication (continuous)

| Artifact | When |
|---|---|
| **Design doc** (1–2 pages) | Before building anything non-trivial |
| **README** | Every repo: what, how to run/test/deploy |
| **RUNBOOK** | Every production job: re-run, backfill, common failures, contacts |
| **ADR** (architecture decision record) | Important choices: "Why DEEP CLONE for X" |
| **Table/column comments & tags** | Every Gold table (and Silver where possible) |
| **Validation report** | Every migration wave |
| **Status update** | Weekly / on blockers |

**Status update template (3 lines):**
> **Done:** Wave 2 (finance, 46 tables) migrated to QA; validation 44/46 PASS.
> **Next:** Fix 2 FAILs (DOUBLE→DECIMAL explained; 1 view with a lost filter), then prod plan review on Thursday.
> **Blocked/Risk:** External location for `fin-archive` container is pending with the platform team (ticket PLAT-88), which blocks 6 tables.

**Estimating:** break the work into tasks of ≤1 day; add time for unknowns (30–50% on migrations); re-estimate when you learn more, and say so early.

## 8. Working with people (continuous)
- Clarify before you build. Repeat the requirement back in your own words.
- Over-communicate during incidents and cutovers.
- Ask for code reviews of your work, *and* review others'.
- Keep a "brag document": what you delivered, problems you solved, and their impact. It helps with reviews, interviews and confidence.

## 9. Things to be aware of (no deep dive yet)
dbt (SQL modeling framework), Apache Iceberg (open table format; UC supports it), Kafka/Event Hubs (event streaming sources), Airflow (external orchestrator), Terraform (infrastructure as code), Delta Sharing (sharing data across orgs), Lakehouse Federation (query external DBs), Databricks Apps & AI/BI dashboards, vector search / AI functions (`ai_query`). You'll hear these names. Know what each one is for.
