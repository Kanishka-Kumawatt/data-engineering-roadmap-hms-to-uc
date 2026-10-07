# Phase 7 — Hive Metastore → Unity Catalog Migration

**Weeks:** 7–9 (and ongoing at work) · **Time:** ~30 h (8 h theory, 22 h hands-on)
**Goal:** Understand the migration well enough to **plan, execute, validate and troubleshoot** a schema migration yourself, and explain every decision.

> **Mentor note:** This is your project, so this phase gets the most depth. Read it in three passes. **Pass 1** (week 7): concepts, sections 1–9. **Pass 2** (week 8): strategies and the Data Engineer's playbook, sections 10–13. **Pass 3** (week 9): failures, scenarios and exercises, sections 14–17. After each pass, go to work and **look for what you just read** in the real environment.
>
> *Databricks evolves UC quickly. Before relying on a specific command option or limitation, check the current docs ([reference/resources.md](../reference/resources.md)). The concepts here are stable; the details move.*

---

## Contents

1. [What Hive Metastore is and how it works](#1-what-hive-metastore-is-and-how-it-works)
2. [What Unity Catalog is](#2-what-unity-catalog-is)
3. [Why organisations migrate](#3-why-organisations-migrate)
4. [HMS vs UC architecture](#4-hms-vs-uc-architecture)
5. [The object hierarchy](#5-the-object-hierarchy)
6. [Managed vs external tables](#6-managed-vs-external-tables)
7. [Storage credentials and external locations](#7-storage-credentials-and-external-locations)
8. [Identities, access control, grants and ownership](#8-identities-access-control-grants-and-ownership)
9. [Discovery, lineage, audit, governance and cross-workspace access](#9-discovery-lineage-audit-governance-and-cross-workspace-access)
10. [Migration strategies and tools](#10-migration-strategies-and-tools)
11. [Per-object migration: tables, views, functions, paths](#11-per-object-migration)
12. [Code and compute changes](#12-code-and-compute-changes)
13. [The Data Engineer's playbook: Before → During → Validation → Troubleshooting → Post](#13-the-data-engineers-playbook)
14. [Rollback considerations](#14-rollback-considerations)
15. [Common migration failures](#15-common-migration-failures)
16. [Realistic scenarios](#16-realistic-migration-scenarios)
17. [Practice, build, explain, interview](#17-practice-build-explain-interview)

---

## 1. What Hive Metastore is and how it works

**Simply:** A metastore is a **phone book for data**. It doesn't hold the data. It maps a name (`sales.orders`) to *where the files are*, *what format they're in* and *what the columns are*.

**Real-world:** A library catalogue card says "*Database Systems*, shelf 4B, hardcover, 600 pages." The book is on the shelf. Throw away the card and the book still exists, but nobody can find it. Burn the book and the card points at nothing.

**Technical:**
```
spark.sql("SELECT * FROM sales.orders")
        │
        ▼
 ┌─────────────────────┐     "sales.orders?"     ┌────────────────────────────────┐
 │ Spark (cluster)     │ ──────────────────────▶ │ Hive Metastore service         │
 │                     │ ◀────────────────────── │ backed by an RDBMS (MySQL/      │
 └─────────┬───────────┘  location=dbfs:/user/  │ Azure SQL/Postgres): tables     │
           │              hive/warehouse/sales.db│ DBS, TBLS, SDS, COLUMNS_V2,     │
           │              /orders, format=delta  │ PARTITIONS ...                  │
           ▼                                     └────────────────────────────────┘
 ┌──────────────────────────────────────────────┐
 │ Cloud storage: the actual Parquet/Delta files │
 └──────────────────────────────────────────────┘
```

**HMS in Databricks:**
- Each **workspace** has its own built-in HMS (or is pointed at an external HMS). In UC-enabled workspaces it appears as the catalog **`hive_metastore`**.
- Names are **2-level**: `database.table` (database = schema).
- **Managed tables** default to the **DBFS root** (`dbfs:/user/hive/warehouse/<db>.db/<table>`), a storage account the workspace owns.
- **External tables** use `LOCATION`, often a **mount** (`/mnt/raw/...`) or a direct `abfss://`/`s3://` path.
- **Security** was workspace-local and patchy:
  - *Table ACLs* (legacy): only enforced on specific clusters with table access control enabled. On other clusters, anyone could read the files directly.
  - *Mounts* used one service principal/key for **everyone** using the workspace. Whoever can run a notebook can read the mount.
  - *Credential passthrough* (legacy, deprecated) and storage keys in Spark config.
- **No built-in lineage, no central audit of data access, and no sharing across workspaces** without an external HMS.

> **Lab:** In local Spark ([docs/00 §3A](../docs/00-how-to-learn-on-a-real-project.md)), open `metastore_db` with a Derby/SQL client, or just run `DESCRIBE EXTENDED`, and see that HMS rows store the location, format and schema. That's all HMS is.

---

## 2. What Unity Catalog is

**Simply:** Unity Catalog is a **single, account-level governance layer** for all data and AI assets across all workspaces: one place for names, permissions, audit, lineage and discovery.

**Key properties:**
- **One metastore per region per account**, attached to many workspaces.
- **3-level names:** `catalog.schema.table`.
- **Identities from the account** (users, groups, service principals synced via SCIM from Entra ID/Okta), not per-workspace.
- **Permissions enforced on every UC-capable compute**, with no "unsafe cluster" back door.
- **Cloud credentials owned by UC** (storage credentials). Users never see keys.
- **Lineage** (table and column level), **audit logs**, **system tables**, **tags**, **row filters / column masks**.
- Governs more than tables: **views, volumes (files), functions, ML models, connections (federation), shares (Delta Sharing)**.

---

## 3. Why organisations migrate

| Driver | HMS reality | UC benefit |
|---|---|---|
| **Security** | Mounts expose storage to every user; ACLs only on some clusters | Fine-grained, centrally enforced permissions; no shared keys |
| **Governance & compliance** | No central audit; hard to answer "who accessed PII?" | Audit logs + `system.access.audit`; tags; masks; row filters |
| **Multi-workspace** | Each workspace is a silo; duplicated tables and grants | One metastore, many workspaces; workspace-catalog binding |
| **Lineage** | Manual or third-party | Automatic table/column lineage |
| **Discovery** | Tribal knowledge | Catalog Explorer, search, comments, tags |
| **Platform direction** | HMS, DBFS root/mounts, table ACLs and passthrough are **legacy** | New features (serverless, predictive optimisation, Lakeflow, sharing, AI/BI, many governance features) need UC |
| **Identity** | Workspace-local groups | Account-level groups/SPs, managed once |

**What to tell a stakeholder in one sentence:** *"We're moving from a per-workspace catalog with weak, inconsistent security to one governed catalog where every data access is permissioned, audited and traceable, and which the platform's new features depend on."*

---

## 4. HMS vs UC architecture

```
 BEFORE (HMS)                                         AFTER (Unity Catalog)
 ─────────────                                        ──────────────────────
 Workspace A           Workspace B                    ┌──────── Databricks Account ────────┐
 ┌──────────────┐      ┌──────────────┐               │ Identities: users/groups/SPs (SCIM)│
 │ HMS (local)  │      │ HMS (local)  │               │ ┌─────── UC Metastore (region) ───┐│
 │ sales.orders │      │ sales.orders │ ← duplicated  │ │ catalogs ▸ schemas ▸ tables     ││
 │ table ACLs?  │      │ different    │               │ │ storage creds, ext. locations   ││
 │ local groups │      │ grants       │               │ │ grants, lineage, audit, tags    ││
 └──────┬───────┘      └──────┬───────┘               │ └───────────────┬─────────────────┘│
        │ /mnt (shared key)   │                       └─────────────────┼──────────────────┘
        ▼                     ▼                          attached to    │
 ┌───────────────────────────────────┐               ┌──────────┐ ┌─────▼────┐ ┌──────────┐
 │ Cloud storage (+ DBFS root)       │               │ WS dev   │ │ WS qa    │ │ WS prod  │
 └───────────────────────────────────┘               └────┬─────┘ └────┬─────┘ └────┬─────┘
                                                          └─────── UC-capable compute ┘
                                                                        │ (UC vends short-lived
                                                                        ▼  credentials)
                                                     ┌──────────────────────────────────┐
                                                     │ Cloud storage: managed locations │
                                                     │ + external locations             │
                                                     └──────────────────────────────────┘
```

| Aspect | HMS | Unity Catalog |
|---|---|---|
| Scope | Workspace | Account (per region), many workspaces |
| Namespace | `schema.table` | `catalog.schema.table` |
| Identity | Workspace users/groups | Account users/groups/service principals |
| Storage access | Mounts, keys in conf, instance profiles | Storage credentials + external locations (UC-vended) |
| Managed table storage | DBFS root | Metastore/catalog/schema **managed location** |
| Permission enforcement | Only on table-ACL clusters | All UC-capable compute (Standard/Dedicated, SQL warehouses, serverless) |
| Lineage / audit | No / limited | Yes (system tables) |
| Files governance | None (DBFS) | **Volumes** |
| Cross-workspace | External HMS hacks | Native |

---

## 5. The object hierarchy

```
Metastore (one per region)
 ├── Storage credentials, External locations, Connections, Shares/Recipients  (metastore-level)
 └── Catalog            e.g. sales_prod         ← often = environment × domain
      └── Schema        e.g. sales_prod.orders  ← = HMS "database"
           ├── Table    sales_prod.orders.fct_orders     (managed or external; Delta preferred)
           ├── View     sales_prod.orders.v_daily_sales
           ├── Materialized view / streaming table
           ├── Volume   /Volumes/sales_prod/orders/landing   (files: managed or external)
           ├── Function sales_prod.orders.mask_email
           └── Model    sales_prod.orders.churn_model
```

**Catalog design: the decision you'll hear debated.** Common patterns:
- **By environment:** `dev`, `qa`, `prod` → `prod.sales.orders`. Simple.
- **By environment × domain:** `sales_dev`, `sales_prod`, `finance_prod`. Good isolation and ownership. The most common.
- **By layer:** `bronze`, `silver`, `gold`. Sometimes used, and combined with env (`prod_bronze`).

Ask your lead which pattern your project uses, and *why*. That's a great learning conversation.

---

## 6. Managed vs external tables

| | **Managed** (UC) | **External** (UC) |
|---|---|---|
| Who manages files | UC, in the catalog/schema/metastore **managed location** | You, at a path inside an **external location** |
| `DROP TABLE` | Deletes data (recoverable for a limited time with `UNDROP`) | Removes metadata only; files stay |
| Path in DDL | None | `LOCATION 'abfss://...'` |
| Format | Delta (or Iceberg) | Delta, Parquet, CSV, JSON, Avro, ORC, text… |
| Optimisations | **Predictive optimisation**, automatic features | Fewer automatic features |
| Recommended for | **New tables by default** | Data shared with non-Databricks tools, or data you can't move |

**Migration nuance:**
- HMS **managed tables on DBFS root** *cannot stay where they are*. DBFS root isn't a valid UC location, so the data **must be copied** (DEEP CLONE/CTAS).
- HMS **external tables** on cloud storage can usually be **registered in place** (SYNC) once an external location covers their path.
- Many teams migrate external tables in place first (fast, low risk), and later convert them to managed tables when convenient.

---

## 7. Storage credentials and external locations

**Simply:** A **storage credential** is *the key* (a cloud identity). An **external location** is *a key + a specific door* (a cloud path). Users get permission on the *door*, never the key.

| Cloud | Storage credential is backed by |
|---|---|
| Azure | **Access Connector for Azure Databricks** (managed identity), granted *Storage Blob Data Contributor* on the storage account/container |
| AWS | **IAM role** with a trust policy for UC, plus S3 permissions |
| GCP | **Service account** with GCS permissions |

```sql
-- Storage credentials are usually created by the platform team (Catalog Explorer, CLI, Terraform)
SHOW STORAGE CREDENTIALS;

CREATE EXTERNAL LOCATION IF NOT EXISTS sales_raw
  URL 'abfss://raw@contosodatalake.dfs.core.windows.net/sales'
  WITH (STORAGE CREDENTIAL sales_cred)
  COMMENT 'Raw sales landing + legacy HMS external tables';

GRANT READ FILES, CREATE EXTERNAL TABLE ON EXTERNAL LOCATION sales_raw TO `grp_sales_engineers`;
SHOW EXTERNAL LOCATIONS;
DESCRIBE EXTERNAL LOCATION sales_raw;
```

**Rules that bite during migrations:**
- A table's path must be **under an external location**, or you can't register it.
- **Path overlap:** UC doesn't allow two tables/volumes to claim overlapping paths, and a given path should map to one external location. HMS was often messy here (tables nested inside other tables' folders, two tables on one path). Expect to untangle that.
- **Cloud-side permission is separate from UC permission.** The UC grant can be perfect while the managed identity lacks the role on the storage account → access errors. Or the firewall/private endpoint blocks Databricks.
- **Mounts don't exist in UC.** For each `/mnt/x`, find the real path (`dbutils.fs.mounts()`), create an external location for it, and rewrite the code.

---

## 8. Identities, access control, grants and ownership

### Identities
- **Users**, **groups** and **service principals** live at the **account** level (usually synced from your IdP via SCIM).
- **Workspace-local groups can't be used in UC grants.** A migration usually includes **migrating workspace-local groups to account groups** (UCX automates this).
- **Service principals** run production jobs. Grants go to SPs/groups, **never to individual people** for production.

### Privileges (the ones you'll use 95% of the time)

| Privilege | On | Meaning |
|---|---|---|
| `USE CATALOG` | catalog | Required to access *anything* inside |
| `USE SCHEMA` | schema | Required to access objects inside |
| `SELECT` | table/view (or schema/catalog, inherited) | Read |
| `MODIFY` | table | Insert/update/delete/merge |
| `CREATE TABLE`, `CREATE VIEW`, `CREATE FUNCTION`, `CREATE VOLUME` | schema | Create objects |
| `CREATE SCHEMA` | catalog | Create schemas |
| `READ VOLUME`, `WRITE VOLUME` | volume | Files access |
| `READ FILES`, `WRITE FILES`, `CREATE EXTERNAL TABLE` | external location | Path-level access |
| `BROWSE` | catalog | See metadata without data access (discovery) |
| `MANAGE` | object | Manage grants/ownership without being the owner |
| `EXECUTE` | function | Call a function |
| `ALL PRIVILEGES` | any | Everything (except ownership-only actions) |

**Inheritance:** grants flow **down**. `SELECT` on a schema = `SELECT` on all current *and future* tables in it. **To read one table you need all three:** `USE CATALOG` + `USE SCHEMA` + `SELECT`. Forgetting `USE CATALOG`/`USE SCHEMA` is the #1 "permission denied" cause after migration.

```sql
GRANT USE CATALOG ON CATALOG sales_prod TO `grp_sales_analysts`;
GRANT USE SCHEMA, SELECT ON SCHEMA sales_prod.orders TO `grp_sales_analysts`;
GRANT USE SCHEMA, SELECT, MODIFY, CREATE TABLE ON SCHEMA sales_prod.orders TO `sp_sales_pipeline_prod`;
REVOKE SELECT ON TABLE sales_prod.orders.customers_pii FROM `grp_sales_analysts`;

SHOW GRANTS ON SCHEMA sales_prod.orders;
SHOW GRANTS `grp_sales_analysts` ON CATALOG sales_prod;
```

### Ownership
- Every object has **one owner** (user, SP or group). The owner can do everything, including grant.
- **Best practice:** owners are **groups** (e.g. `grp_sales_data_owners`) or a deployment SP, **not people**. When a person leaves, objects they own become an operational problem.
- After a migration the owner is often **whoever ran the migration**. **Fix ownership as part of the migration.**
```sql
ALTER TABLE  sales_prod.orders.fct_orders OWNER TO `grp_sales_data_owners`;
ALTER SCHEMA sales_prod.orders           OWNER TO `grp_sales_data_owners`;
```

### Mapping HMS legacy table ACLs → UC

| HMS (legacy) | UC equivalent |
|---|---|
| `USAGE` on database | `USE SCHEMA` (+ `USE CATALOG` on the catalog) |
| `SELECT` | `SELECT` |
| `MODIFY` | `MODIFY` |
| `READ_METADATA` | `BROWSE` (roughly) |
| `CREATE` on database | `CREATE TABLE` / `CREATE VIEW` … |
| `ANY FILE` | `READ FILES`/`WRITE FILES` on specific external locations (much narrower, which is a good thing) |
| `OWN` | Ownership |
| "Everyone on cluster X can read mount Y" | **Nothing**. It must become explicit grants, and you'll discover who actually needs access |

---

## 9. Discovery, lineage, audit, governance and cross-workspace access

- **Discovery:** Catalog Explorer search, `COMMENT ON TABLE`, column comments, **tags** (`ALTER TABLE t SET TAGS ('pii'='true')`), `information_schema` in every catalog, and `system.information_schema` across all of them.
- **Lineage:** captured automatically for queries run on UC compute. Query `system.access.table_lineage` / `system.access.column_lineage`. **Great for migration:** after migrating, lineage shows which jobs and notebooks read each table.
- **Audit:** `system.access.audit`. Who did what, when, from where. You can use it to find **remaining HMS usage** after cutover.
- **Fine-grained governance:** **row filters** and **column masks** (SQL UDFs attached to tables), dynamic views, and ABAC policies based on tags.
- **Cross-workspace:** one metastore serves many workspaces. **Workspace-catalog binding** restricts a catalog to specific workspaces (e.g. `prod` catalog visible only in the prod workspace).
- **Beyond the workspace:** **Delta Sharing** (share tables with other accounts/orgs) and **Lakehouse Federation** (query external DBs, *and* a **federated Hive Metastore** as a foreign catalog, which is useful for gradual migrations).

```sql
-- Who reads this table? (lineage)
SELECT source_table_full_name, target_table_full_name, entity_type, entity_id, event_time
FROM system.access.table_lineage
WHERE source_table_full_name = 'sales_prod.orders.fct_orders'
ORDER BY event_time DESC LIMIT 100;

-- Is anyone still using hive_metastore after cutover? (audit; adapt fields to your schema)
SELECT event_time, user_identity.email, action_name, request_params
FROM system.access.audit
WHERE event_date >= current_date() - 7
  AND service_name = 'unityCatalog'
  AND request_params::string ILIKE '%hive_metastore%'
LIMIT 100;
```

---

## 10. Migration strategies and tools

### Strategy dimensions

| Dimension | Options | Trade-off |
|---|---|---|
| **Scope / sequencing** | Big bang vs **phased by domain/schema/consumer** | Phased = lower risk and more learning, but a longer dual-run |
| **Data movement** | **In place** (register existing files) vs **copy** (clone/CTAS) | In place = fast, no storage cost, shared files; copy = clean separation, easy rollback, costs time and storage |
| **Cutover** | Hard cutover (freeze → migrate → switch) vs **parallel run** (both, compare, then switch) | Parallel is safer for critical pipelines |
| **Direction of dependencies** | Upstream first (sources → consumers) | Migrate tables before the views and jobs that read them |

**Typical phased plan:** pilot one low-risk schema → refine runbook → migrate by domain waves → critical/complex last → decommission.

### Tools

| Tool | What it does | When |
|---|---|---|
| **UCX (Databricks Labs)** | **Assessment** (inventory of tables, jobs, clusters, mounts, grants, compatibility issues, with a dashboard), **group migration**, **table migration workflows** (SYNC / clone / CTAS by table type), **code linting** for UC incompatibilities, and assisted code migration | Most large migrations. Ask whether your project uses it, and read its assessment output |
| **`SYNC` SQL command** | Registers HMS **external** tables in UC (metadata only). Has `DRY RUN`. Sets an `upgraded_to` property on the source table | External tables on supported paths |
| **`DEEP CLONE`** | Copies Delta data + metadata into a UC table. Incremental on re-run | HMS managed Delta tables (esp. on DBFS root) |
| **`CREATE TABLE ... AS SELECT`** | Copies data, can change the format to Delta | Non-Delta managed tables, Hive SerDe tables, restructuring |
| **Catalog Explorer "Upgrade"** | UI wizard for upgrading HMS tables | Small numbers of tables |
| **HMS federation** | Exposes HMS as a foreign catalog *governed* by UC | Gradual migrations, governing HMS data before moving it |
| **Databricks SDK / CLI / Terraform** | Automating catalogs, schemas, grants, jobs | Infrastructure-as-code projects |

### Decision matrix (per table)

```
                         ┌─ Is it a VIEW? ──────────────▶ Recreate with 3-level names, after its base tables
                         │
HMS object ──────────────┼─ MANAGED table on DBFS root?
                         │      ├─ Delta  ──────────────▶ DEEP CLONE → UC managed table
                         │      └─ Non-Delta ───────────▶ CTAS (… USING DELTA) → UC managed table
                         │
                         ├─ EXTERNAL table on cloud path / mount?
                         │      ├─ Path under an External Location? No ─▶ create one (platform team) first
                         │      ├─ Supported format ────▶ SYNC (in place) → UC external table
                         │      │                          (optionally convert to managed later)
                         │      └─ Hive SerDe / unsupported ─▶ CTAS to Delta
                         │
                         └─ FUNCTION?  SQL UDF ─▶ recreate as UC function; Hive/JAR UDF ─▶ rewrite (Python/SQL UC function)
```

---

## 11. Per-object migration

### 11.1 Inventory first
```python
# Minimal HMS inventory script (UCX does this far more completely, but write this once to understand it)
rows = []
for db in [r.databaseName for r in spark.sql("SHOW DATABASES IN hive_metastore").collect()]:
    for t in spark.sql(f"SHOW TABLES IN hive_metastore.{db}").filter("isTemporary = false").collect():
        fqn = f"hive_metastore.{db}.{t.tableName}"
        try:
            info = {r.col_name: r.data_type for r in spark.sql(f"DESCRIBE TABLE EXTENDED {fqn}").collect()}
            rows.append((db, t.tableName, info.get("Type"), info.get("Provider"), info.get("Location"), None))
        except Exception as e:
            rows.append((db, t.tableName, None, None, None, str(e)[:300]))

inv = spark.createDataFrame(rows, "schema STRING, table STRING, type STRING, provider STRING, location STRING, error STRING")
inv.write.mode("overwrite").saveAsTable("migration_sandbox.audit.hms_inventory")   # adapt target
display(inv.groupBy("type", "provider").count())
```
(The column name returned by `SHOW DATABASES` can vary by runtime: `databaseName` or `namespace`. Check it and adjust. This kind of small difference is normal.)

### 11.2 External tables: SYNC
```sql
-- Preview: shows status per table without changing anything
SYNC SCHEMA sales_prod.orders FROM hive_metastore.orders DRY RUN;

-- Execute
SYNC SCHEMA sales_prod.orders FROM hive_metastore.orders;
-- or one table:
SYNC TABLE sales_prod.orders.raw_orders FROM hive_metastore.orders.raw_orders;

-- Check what happened
DESCRIBE TABLE EXTENDED hive_metastore.orders.raw_orders;   -- property upgraded_to = sales_prod.orders.raw_orders
DESCRIBE DETAIL sales_prod.orders.raw_orders;              -- same location as source
```
**Read the status column of the SYNC output.** It tells you per table whether it succeeded or why not (e.g. it's a managed table, the location isn't covered, or the format isn't supported).

⚠️ **After SYNC, HMS and UC point at the same files.** A write via either name changes the data seen by both. Plan which side is the writer, and switch writers deliberately.

### 11.3 Managed Delta tables: DEEP CLONE
```sql
CREATE TABLE IF NOT EXISTS sales_prod.orders.customers
  DEEP CLONE hive_metastore.orders.customers;

-- Before cutover: re-run to copy only what changed since the first clone (incremental)
CREATE OR REPLACE TABLE sales_prod.orders.customers DEEP CLONE hive_metastore.orders.customers;
```
Remember: the clone gets **its own history** (starts fresh). Time travel to pre-migration versions happens on the HMS source.

### 11.4 Non-Delta or SerDe tables: CTAS
```sql
CREATE TABLE sales_prod.orders.legacy_events
  COMMENT 'Migrated from hive_metastore.orders.legacy_events (Parquet) on 2026-10-20'
  CLUSTER BY (event_date)
AS SELECT * FROM hive_metastore.orders.legacy_events;
```
Watch for: partition columns, column types (e.g. `TIMESTAMP` interpretation and `DECIMAL` precision), comments and table properties, which CTAS doesn't copy (re-apply them).

### 11.5 Views, in dependency order
HMS view SQL references 2-level names (`orders.customers`). In UC that resolves against the **current catalog**, so it may point at the wrong place or fail. **Recreate every view with 3-level names**, after its base tables exist.
```sql
SHOW CREATE TABLE hive_metastore.orders.v_active_customers;   -- get the original SQL
CREATE OR REPLACE VIEW sales_prod.orders.v_active_customers AS
SELECT c.customer_id, c.name FROM sales_prod.orders.customers c WHERE c.is_active;
```
Views on views → build a **dependency graph** (parse view SQL for referenced tables) and create them in **topological order**.

### 11.6 Functions
- Permanent SQL UDFs → recreate as UC SQL functions (`CREATE FUNCTION sales_prod.orders.f(...) RETURNS ... RETURN ...`).
- Hive UDFs from JARs → generally rewrite as UC SQL/Python functions or built-ins.

### 11.7 Locations and paths
- `/mnt/...` → resolve with `dbutils.fs.mounts()` to the real `abfss://`/`s3://` path → needs an external location.
- `dbfs:/FileStore`, `dbfs:/tmp`, `dbfs:/user/...` data files → move to **Volumes**.
- Streaming **checkpoints** on mounts/DBFS → plan new checkpoint locations in Volumes/external locations. A checkpoint is tied to the source/sink it was created for. Changing the table can mean resetting the checkpoint with a controlled starting position.
- **Overlapping paths** → decide which table owns the path, and restructure the others.

### 11.8 Permissions
1. Export HMS grants (`SHOW GRANTS ON TABLE/SCHEMA ...` per object, or UCX's grant crawler).
2. Map legacy → UC privileges (table in §8), workspace groups → account groups.
3. Apply at the **schema** level where possible (fewer grants, and future tables are covered).
4. Add access that was **implicit** before (mount users) as explicit grants, with the data owner's approval.
5. Set ownership to groups/SPs.
6. Validate by **testing as the principal** (a member of the group runs a query), not only with `SHOW GRANTS`.

---

## 12. Code and compute changes

Migrating metadata is half the job. **Code that reads and writes those tables has to change too.**

| Legacy pattern | UC replacement |
|---|---|
| `spark.table("sales.orders")` / `FROM sales.orders` | `spark.table(f"{catalog}.sales.orders")`, fully qualified, catalog parameterised |
| `saveAsTable("sales.orders")` | `saveAsTable(f"{catalog}.sales.orders")` |
| `spark.read.load("/mnt/raw/sales/")` | `spark.read.load("/Volumes/sales_prod/raw/landing/sales/")` or the `abfss://` path under an external location |
| `dbfs:/FileStore/...`, `%fs ls dbfs:/...` | Volumes |
| `spark.conf.set("fs.azure.account.key...", key)` | Remove. UC credentials handle access |
| `input_file_name()` | `_metadata.file_path` |
| `sc.parallelize`, `rdd.*`, `spark.sparkContext` | DataFrame API, or Dedicated access mode |
| `CREATE DATABASE x LOCATION '/mnt/...'` | `CREATE SCHEMA cat.x MANAGED LOCATION 'abfss://...'` (or inherit the catalog's) |
| Hive SerDe `ROW FORMAT ...` tables | Delta via CTAS |
| Init scripts / JARs on DBFS | Workspace files / Volumes + allowlist for Standard access mode |
| Jobs running as a person | Run as a **service principal** |
| `USE sales` | `USE CATALOG sales_prod; USE SCHEMA sales` |

**Compute:** clusters must use **Standard** or **Dedicated** access mode on a UC-supported DBR (or serverless / SQL warehouses). "No isolation shared" and legacy table-ACL clusters can't access UC securely. Use **cluster policies** to enforce this.

**Finding the code to change:** UCX's linter, plus your own scanner (Phase 3, Project B), plus `system.access.table_lineage` to find who reads which tables.

---

## 13. The Data Engineer's playbook

This is what you **actually do** on the project. Use [checklists/migration-runbook-checklist.md](../checklists/migration-runbook-checklist.md) as the working document.

### Phase A — Before migration (assessment and readiness)

| # | Task | Output | How |
|---|---|---|---|
| A1 | **Inventory** all HMS objects | Table list with type, format, location, size, last-modified, owner | UCX assessment or the inventory script (§11.1) + `DESCRIBE DETAIL` |
| A2 | **Classify** each object → migration method | Plan CSV: `source, target, method, wave, owner` | Decision matrix (§10) |
| A3 | **Find dependencies** | Table → views, jobs, notebooks, dashboards, external consumers | Code scan, job definitions (API), view SQL parsing, query history, interviews |
| A4 | **Identify owners & consumers** | RACI per schema | Ask! Usually the hardest part |
| A5 | **Check identity readiness** | Workspace groups mapped to account groups | UCX group migration; confirm with the platform team |
| A6 | **Check storage readiness** | Storage credentials + external locations for every path; mounts resolved | `dbutils.fs.mounts()`, `SHOW EXTERNAL LOCATIONS`, path coverage report |
| A7 | **Check compute readiness** | Clusters/policies with UC access modes, supported DBR | Cluster inventory |
| A8 | **Flag code issues** | List of notebooks/jobs needing changes | UCX linter + scanner |
| A9 | **Design target** | Catalog/schema naming, managed locations, grants model | Agreed with architect |
| A10 | **Plan waves, cutover, freeze, rollback** | Runbook + calendar + comms | — |
| A11 | **Capture baselines** | Row counts, aggregates, Delta versions, job durations | Validation queries **before** migration |

### Phase B — During migration (per wave, dev → qa → prod)

1. Create catalog/schemas with managed locations; apply ownership.
2. Migrate tables: **SYNC (dry run → run)**, DEEP CLONE, CTAS per the plan. Log every statement and its result to an audit table.
3. Recreate views in dependency order; recreate functions.
4. Apply grants (schema-level first); set owners.
5. Update code: 3-level names, paths, `_metadata`, configs. One PR per pipeline. Parameterise the catalog.
6. Update jobs: compute (access mode/policy), run-as SP, parameters.
7. **Run the jobs in dev/qa against UC**, compare outputs with HMS (parallel run).
8. Freeze window for prod: stop writers → final incremental clone/sync → switch jobs → resume.

### Phase C — Validation (prove it)

| Level | Checks |
|---|---|
| **Object** | Every planned object exists in UC; type (managed/external/view) is correct; location is correct; format; comments/properties/tags re-applied |
| **Schema** | Same columns, order, types, nullability, partition/cluster columns |
| **Data** | Row counts; aggregate fingerprints (SUM/MIN/MAX/COUNT DISTINCT on key columns); full `EXCEPT` in both directions or a row-hash comparison for critical tables; partition-level counts for big tables |
| **Permissions** | `SHOW GRANTS` matches the mapped plan; **positive and negative tests** as real principals (analyst can read; analyst cannot read PII) |
| **Consumer** | Jobs succeed on UC; dashboards render; downstream counts match the parallel run |
| **Performance** | Job durations comparable to the baseline |
| **Lineage/audit** | Lineage shows expected readers; no unexpected HMS access |

```python
# Validation helper: compare HMS vs UC for a list of table pairs and write a report
from pyspark.sql import functions as F

def fingerprint(fqn: str, key_cols: list[str], num_cols: list[str]) -> dict:
    df = spark.table(fqn)
    aggs = [F.count("*").alias("rows")] + \
           [F.countDistinct(*key_cols).alias("distinct_keys")] + \
           [F.sum(c).cast("decimal(38,4)").alias(f"sum_{c}") for c in num_cols]
    return df.agg(*aggs).first().asDict()

def compare(src: str, tgt: str, key_cols, num_cols) -> dict:
    s, t = fingerprint(src, key_cols, num_cols), fingerprint(tgt, key_cols, num_cols)
    diffs = {k: (s[k], t[k]) for k in s if s[k] != t[k]}
    return {"source": src, "target": tgt, "status": "PASS" if not diffs else "FAIL", "diffs": str(diffs)}

results = [compare("hive_metastore.orders.customers", "sales_prod.orders.customers", ["customer_id"], []),
           compare("hive_metastore.orders.raw_orders", "sales_prod.orders.raw_orders", ["order_id"], ["amount"])]
display(spark.createDataFrame(results))
```

### Phase D — Troubleshooting during migration
Go to §15 and to [Phase 14](phase-14-troubleshooting.md). Always: **read the exact error → identify the layer (name resolution / UC permission / cloud permission / path / format / compute) → test the smallest possible case → fix → document.**

### Phase E — Post-migration

1. **Cutover:** all writers point at UC. Set the **workspace default catalog** to the UC catalog where appropriate.
2. **Make HMS read-only** for migrated objects (revoke write grants / stop writer jobs), and **mark** them (comments/properties such as `upgraded_to`).
3. **Monitor** for 2–4 weeks: job failures, audit logs for lingering HMS access, user tickets.
4. **Retain** HMS objects for the agreed rollback window. **No VACUUM/DROP** on sources.
5. **Decommission:** drop HMS objects (after sign-off), remove mounts, remove storage keys from configs, disable legacy features at workspace level once nothing depends on them.
6. **Hand over:** documentation, a validation report, an updated data catalog (comments/tags), and runbooks.
7. **Improve:** convert external → managed where appropriate, enable predictive optimisation, adopt liquid clustering, add row filters/masks for PII.

---

## 14. Rollback considerations

| Method used | What rollback means | Gotchas |
|---|---|---|
| **SYNC (in place)** | Point consumers back at HMS names. The data is the same files | **Writes made through UC are in the same files**, so there's no data rollback here. If a bad write happened, use Delta `RESTORE` to a version recorded *before* cutover |
| **DEEP CLONE / CTAS (copy)** | Point consumers back at the HMS source, which is untouched | Writes made to UC after cutover **aren't in HMS**. You'll have to back-fill them or accept the loss. Keep the dual-run short |
| **Views/functions** | Old HMS versions still exist | Don't drop them until sign-off |
| **Grants** | Keep the HMS grants export | Restoring legacy ACLs is manual |
| **Code** | Revert the PR / redeploy the previous release tag | This is why every code change goes through Git with releases |

**Rollback prerequisites (put them in the runbook):** recorded Delta versions at cutover (`DESCRIBE HISTORY`), the HMS grants export, previous release tags for all jobs, a defined **rollback window** (e.g. 2 weeks), a **decision owner** and **go/no-go criteria**.

---

## 15. Common migration failures

| Symptom / error (paraphrased; read your exact message) | Likely causes | Investigation | Fix |
|---|---|---|---|
| `TABLE_OR_VIEW_NOT_FOUND` after migration | 2-level name resolving against the wrong default catalog; table not migrated yet; typo; schema name differs in UC | `SELECT current_catalog(), current_schema()`; `SHOW TABLES IN cat.sch` | Use 3-level names; parameterise the catalog; migrate the missing object |
| `PERMISSION_DENIED` / `INSUFFICIENT_PERMISSIONS` | Missing `USE CATALOG`/`USE SCHEMA`; grant given to a person not the SP; workspace-local group | `SHOW GRANTS <principal> ON ...` at each level; who is the job's run-as? | Grant at the right levels to account groups/SPs |
| Cloud storage "access denied" / 403 on an external table even though grants are fine | Managed identity/IAM role lacks the storage role; firewall/private endpoint; wrong container | `DESCRIBE EXTERNAL LOCATION`; the location's "Test connection"; cloud IAM | Platform team fixes the cloud RBAC/network |
| "Location not covered by external location" / SYNC status shows the location is unsupported | No external location for that path; path is a mount | Resolve the mount; compare the table path with `SHOW EXTERNAL LOCATIONS` | Create an external location (platform team), then retry |
| Location overlap error | Another UC table/volume already uses that path or a parent/child path; nested HMS tables | Query `information_schema.tables` for `storage_path`-like fields / `DESCRIBE DETAIL` on suspects | Restructure paths; migrate one; CTAS the other to a managed table |
| SYNC refuses a table | It's **managed** (SYNC is for external), on DBFS root, or an unsupported format | SYNC DRY RUN status, `DESCRIBE EXTENDED` | DEEP CLONE / CTAS instead |
| View fails in UC | References 2-level names or HMS-only objects, or the base table isn't migrated yet | `SHOW CREATE TABLE` the view | Recreate with 3-level names, in dependency order |
| Job fails: `input_file_name` not supported / `sparkContext` not allowed | Legacy APIs on Standard access mode | Error text; UCX linter | `_metadata.file_path`; DataFrame API; Dedicated mode if unavoidable |
| `UC not enabled` / tables invisible in notebook | Cluster access mode/DBR not UC-capable; workspace not attached to the metastore | Cluster config; `SELECT current_metastore()` | Use UC-capable compute |
| Row counts differ HMS vs UC | Writers still writing to HMS after the clone; clone taken mid-write; filter in CTAS; corrupt records | Compare Delta versions/timestamps; check for active writers | Freeze writers; re-run the incremental clone; re-validate |
| Schema differs (types/nullability/comments) | CTAS type inference; DECIMAL/TIMESTAMP semantics; properties not copied | `DESCRIBE` both sides; diff | Explicit casts / DDL then INSERT; re-apply comments/properties |
| Streaming job restarts from scratch or fails | Checkpoint tied to the old table/path | Checkpoint location, source identity | Plan the checkpoint migration; set a starting position |
| Wrong owner / can't grant | The migrator owns the objects | `DESCRIBE TABLE EXTENDED` → Owner | `ALTER ... OWNER TO` group |

---

## 16. Realistic migration scenarios

Work through each one **on paper first** (what would you check, in what order?), then reproduce what you can in your sandbox.

### Scenario 1 — "The dashboard is empty since the weekend"
Monday morning, the finance dashboard shows zero rows. Over the weekend, `finance` was migrated with DEEP CLONE, and the dashboard's SQL was updated to `fin_prod.finance.gl_daily`.
**Investigate:** Does the table have data? (`SELECT COUNT(*)`) → It does. Does the dashboard's warehouse identity have `USE CATALOG` on `fin_prod`? → No. Only `SELECT` on the schema was granted.
**Lesson:** Grants need all three levels. **Prevention:** a permission test per consumer group in the validation checklist.

### Scenario 2 — "SYNC dry run says half the schema can't be migrated"
Dry run on `marketing`: 12 OK, 9 failures.
**Investigate:** Group the failures by status: 5 are managed tables (→ DEEP CLONE), 3 are on `/mnt/mkt-legacy` (→ resolve the mount, which points at a container with no external location → request one), 1 is a Hive SerDe CSV table (→ CTAS).
**Lesson:** The dry run **is** your work plan. Classify, don't panic.

### Scenario 3 — "Counts match but numbers don't"
`sales.orders` (CTAS from Parquet): counts are equal, but `SUM(amount)` differs in the 6th decimal place.
**Investigate:** The source `amount` was `DOUBLE`; the target DDL forced `DECIMAL(18,2)` → rounding.
**Fix:** Agree with the business on the correct type. Most likely DECIMAL is right and this "difference" is the fix. Document it as an **accepted, explained difference** in the validation report.
**Lesson:** Not every difference is a bug, but every difference needs an explanation.

### Scenario 4 — "Job works when I run it, fails in the schedule"
**Investigate:** Interactive = you, with broad grants. Scheduled = run-as `sp_sales_prod`, which lacks `MODIFY` on the target schema and `READ FILES` on the landing external location.
**Lesson:** Test as the run-as identity in QA. **Prevention:** grants as code (Terraform/SQL scripts in Git) for SPs.

### Scenario 5 — "Two tables, one folder"
SYNC for `events` and `events_archive` fails with an overlap: HMS had `events` at `.../events/` and `events_archive` at `.../events/archive/`.
**Fix options:** Move the archive files to a sibling path and register them there, *or* CTAS the archive to a managed table and leave `events` in place. Choose with the data owner, record the decision.

### Scenario 6 — "Row counts drift after cutover"
After the final DEEP CLONE and cutover, UC `orders` has 1,200 fewer rows than HMS by Tuesday.
**Investigate:** `DESCRIBE HISTORY` on the HMS table → there are writes *after* the cutover timestamp → an old job (not in the inventory) still writes to HMS.
**Fix:** Find it via audit logs / job list → repoint it → incremental clone of the gap → validate.
**Prevention:** Revoke `MODIFY` on HMS objects at cutover, and include *all* writers (from audit/lineage) in the dependency analysis.

### Scenario 7 — "Streaming pipeline reprocessed 2 years of files"
After switching an Auto Loader stream's target to UC and changing the source path from `/mnt/landing` to `/Volumes/...`, the stream reprocessed everything.
**Why:** The checkpoint (and the file-tracking state) belongs to the old source path. A new path = new state.
**Prevention:** Plan checkpoint migration: use a start-from option (e.g. `modifiedAfter`/`includeExistingFiles=false` for Auto Loader) and dedupe the target, and test in QA.

---

## 17. Practice, build, explain, interview

### Hands-on (in your sandbox / dev with permission)
1. **Local HMS lab:** create managed and external tables in local Spark; inspect `DESCRIBE EXTENDED`; drop each and observe the files.
2. **UC lab (Free Edition):** create catalog → schema → managed table, external volume (if possible), grants to a group, `SHOW GRANTS`, lineage after a CTAS.
3. **Inventory:** run the §11.1 script against a dev HMS schema; produce counts by type/format.
4. **Plan:** turn the inventory into a migration plan CSV using the decision matrix (reuse your Phase 3 generator).
5. **Migrate a sandbox schema:** SYNC DRY RUN → SYNC; DEEP CLONE a managed table; CTAS a Parquet table; recreate a view.
6. **Validate:** run the fingerprint comparison; write a validation report table.
7. **Permissions:** map a set of HMS grants to UC grants; apply; test with a colleague (or SP) both positive and negative.
8. **Break it:** remove `USE SCHEMA` and observe the error; query with 2-level names after changing the current catalog; try SYNC on a managed table.
9. **Code migration:** take 3 legacy notebooks (or write them), scan them, and convert them to UC-compatible code.

All the exercises: [exercises/hms-to-uc-migration-exercises.md](../exercises/hms-to-uc-migration-exercises.md)

### Build
**Migration toolkit** (part of the capstone): `inventory.py` → `planner.py` → `executor.py` (dry-run default, logs every statement to an audit table) → `validator.py` (fingerprints + EXCEPT for critical tables) → `grants.py` (mapping + apply) → `report.py` (validation report as a Markdown/HTML table). See [capstone/README.md](../capstone/README.md).

### After this phase you should be able to explain
- [ ] What HMS is and stores, and why metadata ≠ data
- [ ] The UC hierarchy, and why a 3-level namespace matters
- [ ] Managed vs external tables in UC, and what `DROP` does to each
- [ ] Storage credential vs external location, and why cloud IAM can still block you
- [ ] Why you need `USE CATALOG` + `USE SCHEMA` + `SELECT`
- [ ] Why ownership should be a group
- [ ] When to use SYNC vs DEEP CLONE vs CTAS, and what each does to history and rollback
- [ ] Why views must be recreated, and in what order
- [ ] The code changes UC typically requires
- [ ] Your project's migration process end to end, including validation and rollback

### Beginner vs experienced

| Beginner | Experienced |
|---|---|
| Runs migration scripts from a runbook | Writes the runbook; chooses the method per table and defends it |
| Checks row counts | Designs multi-level validation (object/schema/data/permission/consumer) and signs off with explained differences |
| Fixes permission errors one by one | Designs the grants model (groups, schema-level, SP run-as, ownership) to prevent them |
| Migrates tables | Migrates the *system*: tables + code + jobs + identities + compute + consumers + decommissioning |

### Interview questions
1. What is the Hive Metastore? What does it store?
2. What is Unity Catalog? How is it different from HMS?
3. Why would an organisation migrate from HMS to UC?
4. Explain the UC object hierarchy.
5. Managed vs external tables in UC. What happens on `DROP`?
6. What are storage credentials and external locations?
7. A user has `SELECT` on a table but gets permission denied. Why?
8. How would you migrate an external Delta table? A managed table on DBFS root? A Parquet table?
9. What does SYNC do? What are its limitations?
10. DEEP CLONE vs CTAS for migration: history, cost, rollback?
11. How do you validate a migration?
12. How do you handle views during migration?
13. What code changes are typically required for UC?
14. What are access modes, and which support UC?
15. What's your rollback plan if a migrated pipeline produces wrong data?
16. How do you find who still uses HMS tables after cutover?
17. What is UCX, and what does its assessment produce?
