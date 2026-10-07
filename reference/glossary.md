# Glossary

| Term | Plain-English meaning |
|---|---|
| **ACID** | Atomic, Consistent, Isolated, Durable: a write fully happens or not at all, and readers never see half a write |
| **Access mode** | How a Databricks cluster isolates users. **Standard** (multi-user, UC-isolated) or **Dedicated** (single user/group). UC needs one of these |
| **AQE** | Adaptive Query Execution: Spark re-optimises the plan at runtime (coalesce partitions, switch joins, split skew) |
| **Auto Loader** | Databricks feature (`cloudFiles`) that incrementally ingests new files exactly once |
| **Broadcast join** | Copying a small table to every executor so the big table needn't shuffle |
| **Bronze / Silver / Gold** | Raw / cleaned / business-ready layers of the medallion architecture |
| **Bundle (DAB)** | Databricks Asset Bundle: YAML describing jobs/pipelines, deployed per environment by the CLI |
| **Catalog** | Top level of the UC namespace (`catalog.schema.table`) |
| **CDF** | Change Data Feed: Delta's row-level change log between versions |
| **Checkpoint** | Where a streaming query stores its progress/state. Delete it and the stream starts over |
| **CTAS** | `CREATE TABLE ... AS SELECT`: create a table from a query (copies data) |
| **DBFS root** | The workspace's default storage; the HMS-era home of managed tables. Not a valid UC location |
| **DEEP / SHALLOW CLONE** | Copy a Delta table with data / with metadata only (pointing at the source files) |
| **Driver / Executor** | Spark's coordinator / workers |
| **External location** | UC object = cloud path + storage credential; the "door" users get access to |
| **External table** | Table whose files live at a path you manage; DROP keeps the files |
| **Grain** | What one row of a table represents |
| **HMS** | Hive Metastore: the legacy per-workspace catalog of table names → paths/schemas |
| **Idempotent** | Running it twice gives the same result as running it once |
| **Lakehouse** | Lake storage + open table format (Delta) + governance (UC) |
| **Lineage** | Which tables/jobs read from and write to which, captured automatically by UC |
| **Liquid clustering** | Delta's flexible data layout (`CLUSTER BY`), replacing partitioning + Z-ORDER for many tables |
| **Managed table** | UC manages its files in a managed location; DROP deletes the data (recoverable for a limited time) |
| **MERGE** | Upsert: update matching rows, insert new ones (and optionally delete) |
| **Metastore** | The catalog of metadata. In UC, one per region per account |
| **Mount** | HMS-era alias (`/mnt/x`) to cloud storage using a shared credential. Not supported for UC governance |
| **OPTIMIZE** | Compacts small files into larger ones (optionally clustering data) |
| **Partition (Spark)** | A chunk of data processed by one task |
| **Partition (table)** | A folder-level split of a table by column value (`PARTITIONED BY`) |
| **Predictive optimization** | Databricks automatically running OPTIMIZE/VACUUM/ANALYZE on UC managed tables |
| **Quarantine** | A table where invalid records go, with a reason, instead of being dropped silently |
| **SCD** | Slowly Changing Dimension: how a dimension handles attribute changes (Type 1 overwrite, Type 2 history) |
| **Schema (UC)** | Second level of the namespace; = HMS "database" |
| **Service principal (SP)** | A non-human identity that runs production jobs |
| **Shuffle** | Redistributing data across executors by key: expensive |
| **Skew** | Uneven data distribution: one task does most of the work |
| **Storage credential** | UC object wrapping a cloud identity (managed identity / IAM role / service account) |
| **Surrogate key** | Warehouse-generated meaningless key (vs the business key from the source) |
| **SYNC** | SQL command that registers HMS external tables in UC without copying data |
| **System tables** | `system.*` tables with audit, lineage, billing, job and compute history |
| **Time travel** | Querying a Delta table as of an older version/timestamp |
| **UCX** | Databricks Labs toolkit for HMS→UC assessment and migration |
| **VACUUM** | Deletes data files no longer referenced by recent Delta versions (limits time travel) |
| **Volume** | UC object governing access to non-tabular files (`/Volumes/cat/schema/vol/...`) |
| **Watermark** | (1) The high-water mark of what's been processed; (2) in streaming, how late data may arrive for stateful operations |
