# Data Engineering Roadmap — Learning Through an HMS → Unity Catalog Migration

> A project-based, mentor-style roadmap for an early-career Data Engineer who is **working on a real Hive Metastore (HMS) → Unity Catalog (UC) migration on Databricks** and wants to grow into someone who can **design, build, test, deploy, monitor and troubleshoot end-to-end data pipelines on their own**.

This is not a certification syllabus. Every topic is tied back to the migration you are working on now, and every phase ends with something you **build, break, debug and explain**.

```
Learn → Practice → Apply to the HMS→UC project → Build something → Debug it → Understand why it works → Next level
```

Split: **~30% theory / ~70% hands-on**. Duration: **16 weeks** at **~8–10 hours/week** on top of your project work. If a week runs long, add a week. Don't skip anything.

---

## Start here

1. Read [docs/00-how-to-learn-on-a-real-project.md](docs/00-how-to-learn-on-a-real-project.md). It covers practice environments, the engineering thought process, the error log and how to ask for help.
2. Open [schedule/16-week-roadmap.md](schedule/16-week-roadmap.md) and start Week 1.
3. Track yourself in [PROGRESS.md](PROGRESS.md) every Friday.

## How this repo is organised

| Folder | What's inside |
|---|---|
| [docs/](docs/) | How to learn on a real project, and [what you should be able to do after 3 months](docs/after-3-months.md) |
| [phases/](phases/) | 15 phases, from fundamentals to production troubleshooting. Each one covers what, why, the link to HMS→UC, practice, build, troubleshoot, explain, and beginner vs experienced |
| [schedule/](schedule/) | The [16-week roadmap](schedule/16-week-roadmap.md) and the [daily/weekly practice plan](schedule/daily-weekly-practice-plan.md) |
| [exercises/](exercises/) | [SQL](exercises/sql-exercises.md) · [PySpark](exercises/pyspark-exercises.md) · [Databricks](exercises/databricks-exercises.md) · [HMS→UC migration](exercises/hms-to-uc-migration-exercises.md) · [Hands-on projects](exercises/hands-on-projects.md) |
| [capstone/](capstone/) | The full [capstone project](capstone/README.md) (HMS→UC migration + a new medallion pipeline), with a runnable [starter codebase](capstone/starter/) |
| [checklists/](checklists/) | [Developer checklist](checklists/developer-checklist.md) · [Production-readiness checklist](checklists/production-readiness-checklist.md) · [Migration runbook](checklists/migration-runbook-checklist.md) |
| [reference/](reference/) | [Skill matrix](reference/skill-matrix.md) · [Interview questions](reference/interview-questions.md) · [Troubleshooting index](reference/troubleshooting-index.md) · [Resources](reference/resources.md) · [Glossary](reference/glossary.md) |

## The phases

| # | Phase | Weeks | Why it's here |
|---|---|---|---|
| 1 | [Data Engineering Fundamentals](phases/phase-01-fundamentals.md) | 1 | The vocabulary of every meeting you'll sit in |
| 2 | [SQL](phases/phase-02-sql.md) | 1–3 | The language most migration validation is written in |
| 3 | [Python for Data Engineers](phases/phase-03-python.md) | 2–4 | Automation, migration scripts, reusable pipeline code |
| 4 | [Apache Spark / PySpark](phases/phase-04-spark.md) | 4–6 | The engine under every Databricks job |
| 5 | [Databricks](phases/phase-05-databricks.md) | 5–7 | Where your project runs |
| 6 | [Delta Lake](phases/phase-06-delta-lake.md) | 6–7 | The table format you're migrating and building on |
| 7 | [**HMS → Unity Catalog Migration**](phases/phase-07-hms-to-unity-catalog.md) | 7–9 | **Your project. The most detailed phase** |
| 8 | [Data Pipeline Development](phases/phase-08-pipeline-development.md) | 9–11 | From business requirement to production pipeline |
| 9 | [Data Modeling](phases/phase-09-data-modeling.md) | 10 | Designing the Gold layer people actually query |
| 10 | [Git & Software Practices](phases/phase-10-git.md) | 2 → ongoing | How teams ship code together |
| 11 | [Testing & Data Quality](phases/phase-11-testing-data-quality.md) | 11–12 | How you prove a migration or pipeline is correct |
| 12 | [CI/CD & Deployment](phases/phase-12-cicd.md) | 12–13 | Dev → QA → Prod without manual clicking |
| 13 | [Performance Optimization](phases/phase-13-performance.md) | 13–14 | Investigating slow jobs, not memorising rules |
| 14 | [Production & Troubleshooting](phases/phase-14-troubleshooting.md) | 14–15 | Symptom → cause → investigation → fix → prevention |
| 15 | [What You Didn't Ask About (But Will Need)](phases/phase-15-what-you-didnt-ask-for.md) | spread across | Cloud storage & IAM, Auto Loader, streaming, Lakeflow pipelines, PII governance, system tables, cost, documentation, communication |

The **capstone** runs from week 13 to week 16, and you start building its pieces earlier.

## Topics added beyond the original brief

- **Cloud storage and identity basics** (ADLS/S3/GCS, IAM roles, managed identities). Most UC "permission denied" problems are really cloud-permission problems.
- **UCX (Databricks Labs)**, the tool Databricks provides for HMS→UC assessment, group migration, table migration and code linting.
- **Compute access modes** (Standard vs Dedicated) and why code that ran on HMS clusters breaks under UC.
- **DBFS mounts → External Locations / Volumes**, which is often where most of the code-change work in a migration ends up.
- **Workspace-local groups → account-level groups.**
- **Auto Loader, Structured Streaming and Lakeflow Declarative Pipelines (formerly DLT)**, at an intro level.
- **Databricks Asset Bundles** for deployment.
- **System tables** (audit, lineage, billing, job runs) for monitoring and migration validation.
- **Fine-grained governance**: row filters, column masks, tags, PII handling.
- **Cost awareness** for a Data Engineer.
- **Soft skills**: runbooks, status updates, asking good questions, estimating.
- **Using AI assistants responsibly.**

## Ground rules from your mentor

- **Never practise destructive commands on the client's environment.** Use Databricks Free Edition or local Spark (see [docs/00](docs/00-how-to-learn-on-a-real-project.md)). Practise `VACUUM`, `DROP` and `RESTORE` there.
- **Never paste client data, table names or credentials into public places**: this repo, public AI tools, Stack Overflow. Anonymise everything.
- **Keep an error log** (template in [docs/00](docs/00-how-to-learn-on-a-real-project.md)). It's the most valuable document you'll own after 3 months.
- **"I don't know yet, but here's how I'd find out"** is a senior-engineer answer. Use it.

---

## What should I be able to do after 3 months?

Full version: [docs/after-3-months.md](docs/after-3-months.md). In short:

- Explain **why** your organisation is moving from HMS to UC, and draw the architecture before and after from memory.
- Migrate a schema end to end: inventory, dependency mapping, choosing SYNC / CTAS / DEEP CLONE / UCX per table, permissions, code changes, validation and sign-off.
- Diagnose `TABLE_OR_VIEW_NOT_FOUND`, `PERMISSION_DENIED`, path/location errors, schema mismatches and failed MERGEs without help, using a repeatable investigation method.
- Build a Bronze → Silver → Gold pipeline from a written requirement: incremental, idempotent, parameterised, tested, version-controlled, deployed as a Databricks Job, and monitored.
- Read the Spark UI, find the slow stage and explain *why* it's slow.
- Write SQL and PySpark that a reviewer approves without big rewrites.
- Write a migration validation report that a lead can sign off on.
- Pick up a ticket, ask the right clarifying questions, estimate it, deliver it and demo it.
