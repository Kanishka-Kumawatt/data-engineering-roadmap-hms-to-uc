# Phase 1 — Data Engineering Fundamentals

**Weeks:** 1 · **Time:** ~8 h (3 h theory, 5 h hands-on)
**Goal:** Understand the vocabulary used in every project meeting, and be able to draw your project's data flow on a whiteboard.

> **Mentor note:** You've probably heard "lakehouse", "Bronze layer" and "ELT" in stand-ups and nodded along. This week you stop nodding and start understanding. Don't over-study it. Fundamentals click properly once you build things, so aim to grasp about 70% now and pick up the rest along the way.

---

## 1. What Data Engineering actually is

**Simply:** Data Engineers build and run the plumbing that moves data from where it's created to where it's useful, and keep it **correct, timely, secure and affordable**.

**Real-world example:** An airline's booking system records every ticket sale. Finance wants daily revenue by route. A data scientist wants 3 years of history to predict demand. Neither of them should query the live booking database (that would slow down customers buying tickets). A Data Engineer builds pipelines that copy, clean, reshape and serve that data.

**What a Data Engineer does all week:**

| Activity | % of time (realistic) |
|---|---|
| Building/changing pipelines | 30–40% |
| Debugging failures and data issues | 20–30% |
| Meetings, requirements, clarifying | 15–20% |
| Testing, validation, reviews | 10–15% |
| Migration/platform work (like yours) | varies |

Notice how much time goes to debugging and clarifying. Those are skills, and this roadmap trains them deliberately.

**Data Engineer vs Data Analyst vs Data Scientist vs Platform Engineer**

| Role | Main output |
|---|---|
| Data Engineer | Reliable tables and pipelines |
| Analytics Engineer | Business-friendly models (often in SQL/dbt) on top of DE tables |
| Data Analyst | Reports, dashboards, answers |
| Data Scientist / ML Engineer | Models and predictions |
| Platform Engineer | Workspaces, clusters, networking, UC metastore setup, CI/CD infrastructure |

On an HMS→UC migration you sit between Data Engineering and Platform Engineering.

---

## 2. OLTP vs OLAP

| | OLTP (Online Transaction Processing) | OLAP (Online Analytical Processing) |
|---|---|---|
| Purpose | Run the business | Analyse the business |
| Example | Booking system, banking app | Revenue dashboard, data warehouse |
| Queries | Many tiny reads/writes ("insert this order") | Few huge reads ("sum revenue by month for 3 years") |
| Design | Normalised, row-oriented | Denormalised, column-oriented |
| Tech | PostgreSQL, MySQL, SQL Server, Oracle | Databricks SQL, Snowflake, BigQuery, Synapse |

**Why it matters:** Your sources are usually OLTP and your targets are OLAP. Pulling from OLTP has to be gentle (incremental, off-peak, read replicas).

**HMS→UC connection:** The Hive Metastore itself is backed by an OLTP-style relational database (often MySQL/PostgreSQL/Azure SQL) that stores table *definitions*. The data it describes is used for OLAP.

---

## 3. Warehouse vs Lake vs Lakehouse

```
DATA WAREHOUSE            DATA LAKE                    LAKEHOUSE
(structured, governed,    (cheap files, any format,    (lake storage + warehouse features:
 expensive, SQL)           flexible, often a "swamp")   ACID, schema, governance, SQL + Python)
┌─────────────┐           ┌─────────────┐              ┌─────────────────────────┐
│ Tables only │           │ CSV JSON    │              │ Unity Catalog (governance)│
│ Proprietary │           │ Parquet     │              │ Delta Lake (ACID tables) │
│ storage     │           │ images ...  │              │ Cloud object storage     │
└─────────────┘           └─────────────┘              └─────────────────────────┘
```

- **Data warehouse:** structured, reliable, fast SQL, but expensive and poor for unstructured data or ML.
- **Data lake:** cheap object storage (S3, ADLS, GCS) holding files in any format. Flexible, but on its own it has no transactions, no schema enforcement and weak governance, so it tends to become a "data swamp."
- **Lakehouse:** lake storage + an open table format (**Delta Lake**) for ACID and schema + a governance layer (**Unity Catalog**) for permissions, lineage and discovery.

**HMS→UC connection:** This is *why your project exists*. HMS gave the lake a basic catalog: names → paths. UC gives it real lakehouse governance: centralised permissions, lineage, auditing, and cross-workspace sharing. The migration upgrades a "lake with a catalog" into a governed lakehouse.

---

## 4. Structured, semi-structured, unstructured

| Type | Example | Typical handling |
|---|---|---|
| Structured | Tables, CSV with fixed columns | Direct load into Delta tables |
| Semi-structured | JSON, XML, Avro, nested API responses | Parse/flatten in Silver; `from_json`, `explode`, `VARIANT` type |
| Unstructured | PDFs, images, audio, logs | Store in **UC Volumes**, extract metadata/text |

**HMS→UC connection:** In HMS projects, unstructured files often live in **DBFS mounts** (`/mnt/raw/...`). UC doesn't support mounts for governed access. Those files move behind **External Locations** and **Volumes** (`/Volumes/catalog/schema/volume/...`). Expect to rewrite a lot of file paths.

---

## 5. ETL vs ELT

- **ETL:** Extract → Transform (on a separate engine) → Load the finished data into the warehouse.
- **ELT:** Extract → Load raw data into the lake/lakehouse → Transform *inside* the platform (Spark/SQL).

The lakehouse world is mostly **ELT**: land the raw data first (Bronze), then transform with Spark (Silver/Gold). Why? Storage is cheap, compute is elastic, and **keeping the raw data lets you re-process it when logic changes or bugs are found.**

---

## 6. Batch vs streaming

| | Batch | Streaming |
|---|---|---|
| When | Scheduled (hourly/daily) | Continuous / micro-batch (seconds–minutes) |
| Example | Nightly finance load | Fraud detection, live flight status |
| Complexity | Lower | Higher (state, late data, exactly-once) |
| Databricks tools | Jobs + Spark/SQL | Structured Streaming, Auto Loader, Lakeflow Declarative Pipelines |

**Mentor truth:** Most business pipelines are batch, or "streaming with `availableNow` triggers" (incremental batch). Learn batch well first.

---

## 7. Pipelines and workflows

- **Pipeline:** a piece of code that moves/transforms data from A to B (e.g. `orders_bronze_to_silver`).
- **Workflow / Job:** an orchestrated set of tasks with dependencies, schedule, retries and alerts (e.g. a Databricks Job: ingest → silver → gold → quality check → notify).

```
Source → Ingestion → Processing → Storage → Serving
  │          │            │           │          │
 OLTP DB   Auto Loader   Spark      Delta in    Databricks SQL,
 APIs      JDBC, Kafka   SQL        UC tables   dashboards, ML,
 Files     Fivetran                             APIs, Delta Sharing
```

### The medallion architecture (you'll hear this daily)

| Layer | Contains | Rules |
|---|---|---|
| **Bronze (raw)** | Data as received, plus ingestion metadata (`_ingested_at`, `_source_file`) | Append-only, minimal transformation, replayable |
| **Silver (cleaned)** | Deduplicated, typed, validated, conformed | Business keys enforced, quality checks |
| **Gold (curated)** | Business-level aggregates, facts and dimensions | Modeled for consumers, documented, SLA-backed |

---

## Hands-on (5 h)

1. **Draw your project's architecture** (1.5 h). On paper or in draw.io, draw your migration project: sources → storage accounts/buckets → HMS tables → jobs → consumers. Then draw the target UC state. Mark what you don't know with `?`, and ask a senior to fill in the gaps. **This is the most valuable exercise of the week.**
2. **Classify 10 real tables** from your project (1 h): OLTP- or OLAP-sourced? Bronze/Silver/Gold? Structured or semi-structured? Batch or streaming? Managed or external? (Use `DESCRIBE EXTENDED` in dev.)
3. **Local HMS lab** (1.5 h): follow [docs/00 §3A](../docs/00-how-to-learn-on-a-real-project.md). Create a database and two tables, one managed and one with `LOCATION`. Delete the managed table and see that its files disappear. Delete the external one and see that its files remain. Write down why.
4. **Glossary** (1 h): write a one-line definition, in your own words, for every bold term in this phase in `notes/glossary.md`.

## Build

A one-page **"Our Data Platform: Before & After"** document (Markdown, in your fork) with your two diagrams and a short explanation of what changes for each component.

## Troubleshoot / understand

- Why do people say "data swamp"? What problems does UC solve that a plain lake has?
- Why do we keep raw Bronze data when Silver is "better"?

## After this phase you should be able to explain

- [ ] What a Data Engineer does, in 2 minutes, to a non-technical person
- [ ] OLTP vs OLAP with an example from your project
- [ ] Lake vs warehouse vs lakehouse, and where Delta and UC fit
- [ ] ETL vs ELT, and why lakehouses favour ELT
- [ ] Bronze/Silver/Gold, with what goes in each
- [ ] Your project's data flow, end to end, drawn from memory

## Beginner vs experienced

| Beginner | Experienced |
|---|---|
| Can define the terms | Can pick between batch/streaming, ETL/ELT, managed/external for a given requirement and justify the cost/latency/complexity trade-offs |
| Knows the medallion layers | Knows when **not** to use all three layers (e.g. small reference data) |

## Interview questions

1. What's the difference between a data lake and a lakehouse?
2. Why would you choose ELT over ETL on Databricks?
3. Explain the medallion architecture. What goes into Bronze?
4. When would you choose streaming over batch? What extra complexity does streaming add?
5. Describe a data pipeline you've worked on, from source to consumer.
