# 16-Week Learning Roadmap

**Budget:** ~8–10 h/week outside project hours (≈30% theory, 70% hands-on) + 10 min/day of reflection at work.
**Rule:** If a week takes longer, **stretch it, don't skip**. Weeks 7–9 (HMS→UC) are the most important. Give them extra time if your project needs it.

```
Weeks  1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16
Fund   ██
SQL    ██ ██ ██
Python    ██ ██ ██
Git       ██ ── ── ── ── ── ── ── ── ── ── ── ── ── ──   (continuous)
Spark           ██ ██ ██
DBX                ██ ██ ██
Delta                 ██ ██
HMS→UC                   ██ ██ ██
Pipeline                       ██ ██ ██
Model                             ██
Test/DQ                              ██ ██
CI/CD                                   ██ ██
Perf                                       ██ ██
Trouble                                       ██ ██
Capstone                                   ██ ██ ██ ██
```

---

## Week 1 — Foundations & environment
| | |
|---|---|
| **Topics** | [Phase 1](../phases/phase-01-fundamentals.md) all; [Phase 2](../phases/phase-02-sql.md) Level 1; [docs/00](../docs/00-how-to-learn-on-a-real-project.md) setup |
| **Concepts** | OLTP/OLAP, lake/warehouse/lakehouse, ETL/ELT, batch/stream, medallion; SELECT/WHERE/GROUP BY/HAVING; logical query order; metadata vs data |
| **Hands-on** | Install local PySpark + Delta; create the Free Edition workspace; create the SQL practice dataset; SQL exercises 1–10; local HMS lab (managed vs external drop) |
| **Mini-project** | "Our Data Platform: Before & After" doc with 2 diagrams of your project |
| **Project link** | Draw the real HMS architecture; classify 10 real tables (type, format, layer) |
| **Expected outcome** | You can explain your project's purpose and data flow; the environments work |
| **Time** | Theory 3 h · Hands-on 6 h |
| **Interview Qs** | Lake vs lakehouse? ETL vs ELT? Medallion architecture? WHERE vs HAVING? |

## Week 2 — SQL joins & CTEs · Python basics · Git basics
| | |
|---|---|
| **Topics** | Phase 2 Levels 2–3; [Phase 3](../phases/phase-03-python.md) §1–2 (data structures, loops, functions); [Phase 10](../phases/phase-10-git.md) §1–4 |
| **Concepts** | Join types, anti/semi joins, grain, fan-out; CTEs, CASE, NULL handling, dates; list/dict/set/tuple; functions; clone/branch/commit/push |
| **Hands-on** | SQL exercises 11–25; Python warm-ups P1–P8; fork this repo, set up `notes/`, first PR to your own main |
| **Mini-project** | **DQ report SQL** (duplicates, orphans, NULLs, no-item orders) |
| **Project link** | Write a row-count + orphan check for 2 real dev tables |
| **Expected outcome** | You can join safely (checking grain first), and commit work through PRs |
| **Time** | Theory 2.5 h · Hands-on 7 h |
| **Interview Qs** | Find records in A not in B? Why did a LEFT JOIN lose rows? list vs tuple? |

## Week 3 — Window functions & debugging SQL · Python for real work
| | |
|---|---|
| **Topics** | Phase 2 Levels 4–5; Phase 3 exceptions, files, logging, config |
| **Concepts** | ROW_NUMBER/RANK/LAG/running totals, QUALIFY; debugging complex SQL; production-quality SQL; try/except; logging; YAML config; dataclasses |
| **Hands-on** | SQL exercises 26–40; reconciliation query (MATCH/MISMATCH/MISSING); Python P9–P15 |
| **Mini-project** | **Monthly customer metrics** Gold-style SQL model + **reconciliation query** |
| **Project link** | Take one real (complex) SQL from the project, break it into CTEs, and explain it to a colleague |
| **Expected outcome** | You can dedupe with windows and reconcile two tables in SQL |
| **Time** | Theory 2 h · Hands-on 7.5 h |
| **Interview Qs** | ROW_NUMBER vs RANK vs DENSE_RANK? Prove two tables are identical? Exceptions in pipelines: fail or continue? |

## Week 4 — Python projects · Spark architecture
| | |
|---|---|
| **Topics** | Phase 3 Projects A & B, APIs, packaging, pytest; [Phase 4](../phases/phase-04-spark.md) §1–4 |
| **Concepts** | Modules/packages, pure functions, tests; driver/executor, job/stage/task, lazy evaluation, DataFrames vs RDDs |
| **Hands-on** | Build the **Migration Statement Generator** with 5+ tests; build the **code scanner**; first PySpark notebook + Spark UI tour |
| **Mini-project** | Migration Statement Generator (CSV inventory → plan + SQL) |
| **Project link** | Run the scanner over (a copy of / anonymised) project notebooks: count `/mnt`, 2-level names, RDD usage |
| **Expected outcome** | You've written a small, tested Python package; you can explain Spark's execution model |
| **Time** | Theory 2.5 h · Hands-on 7 h |
| **Interview Qs** | How do you make code reusable across notebooks? Explain lazy evaluation. Driver vs executor? |

## Week 5 — Spark internals · Databricks basics
| | |
|---|---|
| **Topics** | Phase 4 §5–8; [Phase 5](../phases/phase-05-databricks.md) component tour, compute & access modes, Git folders |
| **Concepts** | Partitions, shuffles, narrow vs wide, broadcast vs sort-merge, skew, caching; workspace, clusters/serverless, access modes, Git folders |
| **Hands-on** | PySpark exercises 1–15; broadcast vs no broadcast; the skew experiment; Git folder connected to your fork |
| **Mini-project** | Spark UI write-up: "what I saw for 3 queries" (stages, shuffles, skew) |
| **Project link** | Ask: which access mode do our clusters use? Which DBR? Why? |
| **Expected outcome** | You can read a physical plan and spot a shuffle and a skewed task |
| **Time** | Theory 2.5 h · Hands-on 7 h |
| **Interview Qs** | What triggers a shuffle? repartition vs coalesce? Which access modes support UC? |

## Week 6 — Spark I/O & debugging · Delta Lake core
| | |
|---|---|
| **Topics** | Phase 4 §9–10; [Phase 6](../phases/phase-06-delta-lake.md) §1–3 (log, ACID, history, time travel, schema enforcement/evolution) |
| **Concepts** | Explicit schemas, read modes, `_metadata`; Spark UI debugging; transaction log, time travel, RESTORE, enforcement vs evolution |
| **Hands-on** | PySpark exercises 16–25; open `_delta_log` JSONs; corrupt + RESTORE a table; trigger a schema mismatch |
| **Mini-project** | **`orders_daily` PySpark job** (Phase 4 Build) with a README of the stages observed |
| **Project link** | `DESCRIBE DETAIL` / `DESCRIBE HISTORY` on 5 project tables: format, size, files, last writes |
| **Expected outcome** | You understand Delta at the file level, and can read and write data properly |
| **Time** | Theory 2.5 h · Hands-on 7 h |
| **Interview Qs** | What is `_delta_log`? Schema enforcement vs evolution? Driver OOM causes? |

## Week 7 — Delta advanced · Databricks jobs · UC concepts (pass 1) · Cloud IAM
| | |
|---|---|
| **Topics** | Phase 6 MERGE/OPTIMIZE/VACUUM/CLONE/SCD/CDF; Phase 5 jobs/parameters/secrets/monitoring; [Phase 7](../phases/phase-07-hms-to-unity-catalog.md) §1–9; [Phase 15](../phases/phase-15-what-you-didnt-ask-for.md) §1 |
| **Concepts** | MERGE + dedupe, OPTIMIZE vs VACUUM, DEEP vs SHALLOW CLONE; multi-task jobs, widgets, task values; HMS vs UC, hierarchy, managed/external, storage credential/external location, privileges, ownership; cloud identities |
| **Hands-on** | Delta exercises (MERGE failure, OPTIMIZE, CLONE); 4-task parameterised job with retries + failure email + repair run; UC lab in Free Edition (catalog/schema/grants/lineage) |
| **Mini-project** | **SCD2 customer dimension** + the 4-task job |
| **Project link** | Map one real external location end to end (storage → credential → location → grants). List which HMS tables are managed vs external in one schema |
| **Expected outcome** | You can explain UC's security model and why the project needs it |
| **Time** | Theory 3.5 h · Hands-on 7 h *(heavy week; stretch it if needed)* |
| **Interview Qs** | How does MERGE fail? OPTIMIZE vs VACUUM? HMS vs UC? Storage credential vs external location? |

## Week 8 — HMS→UC (pass 2): strategies, methods, permissions
| | |
|---|---|
| **Topics** | Phase 7 §10–12 (strategies, UCX, decision matrix, SYNC/DEEP CLONE/CTAS, views, functions, paths, grants, code & compute changes) |
| **Concepts** | In-place vs copy; phased waves; history & rollback implications of each method; HMS→UC grant mapping; workspace→account groups; code patterns that break |
| **Hands-on** | Migration exercises M1–M12 in your sandbox: inventory script, plan, SYNC DRY RUN, DEEP CLONE, CTAS, recreate views in order, map & apply grants, code conversion of 3 notebooks |
| **Mini-project** | Extend the generator into a **planner + executor (dry run by default)** that logs to an audit table |
| **Project link** | Read your project's UCX assessment (or inventory). Can you explain the method chosen for 10 tables? |
| **Expected outcome** | You can choose and justify the migration method for any table |
| **Time** | Theory 2.5 h · Hands-on 7.5 h |
| **Interview Qs** | How do you migrate an external Delta table? A DBFS-root managed table? What does SYNC do? Why recreate views? |

## Week 9 — HMS→UC (pass 3): validation, failures, rollback · Governance
| | |
|---|---|
| **Topics** | Phase 7 §13–16 (playbook, validation, rollback, failures, scenarios); Phase 15 §4 (masks, row filters, tags) |
| **Concepts** | Object/schema/data/permission/consumer validation; explained differences; rollback per method; scenarios 1–7; column masks & row filters |
| **Hands-on** | Migration exercises M13–M25: validation fingerprints, EXCEPT, hash-by-partition, permission positive/negative tests, the 7 scenarios reproduced, mask + row filter |
| **Mini-project** | **Validator + validation report** for your sandbox migration |
| **Project link** | Offer to run or review validation for one wave at work. Write the runbook steps for one schema |
| **Expected outcome** | You can migrate *and prove* a schema migration end to end |
| **Time** | Theory 2 h · Hands-on 8 h |
| **Interview Qs** | How do you validate a migration? Rollback plan? Who still uses HMS after cutover? |

## Week 10 — Pipeline development (1) · Data modeling · Auto Loader
| | |
|---|---|
| **Topics** | [Phase 8](../phases/phase-08-pipeline-development.md) steps 0–3 + Bronze; [Phase 9](../phases/phase-09-data-modeling.md); Phase 15 §2 |
| **Concepts** | Requirement questions, source profiling, design doc; facts/dims/grain, star schema, keys, SCDs; Auto Loader, checkpoints, `availableNow` |
| **Hands-on** | Write the DE-142 design doc; generate data with the capstone generator; build Bronze with Auto Loader; design the star schema + `dim_date` |
| **Mini-project** | **Design doc + Bronze layer + ERD** |
| **Project link** | Read the design doc (if any) of a pipeline you're migrating. What questions would you have asked? |
| **Expected outcome** | You can turn a vague ticket into a design |
| **Time** | Theory 3 h · Hands-on 7 h |
| **Interview Qs** | Walk through building a pipeline from a requirement. Fact vs dimension? Surrogate keys? Grain? |

## Week 11 — Pipeline development (2) · Unit testing · Declarative pipelines
| | |
|---|---|
| **Topics** | Phase 8 Silver/Gold/DQ/logging/audit; [Phase 11](../phases/phase-11-testing-data-quality.md) §1–2; Phase 15 §3 |
| **Concepts** | Pure transforms, MERGE with dedupe, quarantine, affected-date Gold rebuild, idempotency; pytest for PySpark; expectations |
| **Hands-on** | Build Silver & Gold; 8+ unit tests; idempotency test (run twice); late-data test; optional: Bronze→Silver as a declarative pipeline |
| **Mini-project** | **Working Daily Sales pipeline** (Bronze→Silver→Gold) with tests |
| **Project link** | Identify which migrated pipelines are *not* idempotent. Raise it with your lead |
| **Expected outcome** | An incremental, idempotent, tested pipeline that you built from scratch |
| **Time** | Theory 2 h · Hands-on 8 h |
| **Interview Qs** | Late-arriving data? Idempotency? Testing PySpark? Bad records? |

## Week 12 — Data quality · Migration test suite · CI/CD intro · System tables
| | |
|---|---|
| **Topics** | Phase 11 §3–5; [Phase 12](../phases/phase-12-cicd.md) §1–3; Phase 15 §5 |
| **Concepts** | DQ rules (fail vs warn), constraints, reconciliation, regression; lifecycle, CI vs CD, Asset Bundles; system tables |
| **Hands-on** | `run_rules` framework + 8 rules + a DQ gate task; parameterise the migration validator; `databricks bundle init/validate/deploy -t dev`; query job & lineage system tables |
| **Mini-project** | Pipeline packaged as a **bundle** with a DQ gate |
| **Project link** | Ask how your project deploys jobs (bundles? Terraform? manual?). Draw the release flow |
| **Expected outcome** | Automated quality gates; deploy with one command |
| **Time** | Theory 2.5 h · Hands-on 7.5 h |
| **Interview Qs** | Which DQ checks would you add? CI vs CD? What are Asset Bundles? |

## Week 13 — CI/CD (2) · Performance (1) · Capstone kickoff
| | |
|---|---|
| **Topics** | Phase 12 §4–7; [Phase 13](../phases/phase-13-performance.md) §1–3; Phase 15 §6; [Capstone](../capstone/README.md) |
| **Concepts** | GitHub Actions, environments, secrets/OIDC, promotion, code vs data rollback; the investigation routine, symptom→cause table; cost |
| **Hands-on** | CI workflow (lint + tests) on your capstone repo; dev/prod bundle targets; rollback drill; skew & small-file experiments |
| **Mini-project** | **Capstone part 1:** repo set up, CI green, legacy "HMS" environment built (see capstone) |
| **Project link** | Capture performance baselines for 3 jobs before they're migrated |
| **Expected outcome** | You can ship through CI/CD and start investigating slow jobs |
| **Time** | Theory 2 h · Hands-on 8 h |
| **Interview Qs** | Roll back a bad deploy that wrote bad data? A job is 5× slower: how do you investigate? |

## Week 14 — Performance (2) · Troubleshooting (1) · Capstone build
| | |
|---|---|
| **Topics** | Phase 13 §4–5; [Phase 14](../phases/phase-14-troubleshooting.md) method + scenarios 1–7 |
| **Concepts** | File layout, liquid clustering, MERGE optimisation; the universal troubleshooting method |
| **Hands-on** | Phase 13 hands-on 2–5; drills for scenarios 1–7 (break → fix → log) |
| **Mini-project** | **Capstone part 2:** migrate the legacy environment to UC (toolkit: inventory → plan → execute → validate → grants) |
| **Project link** | Volunteer for the next production issue triage (shadow a senior) |
| **Expected outcome** | You troubleshoot with a method rather than by guessing |
| **Time** | Theory 1.5 h · Hands-on 8.5 h |
| **Interview Qs** | Debug a failed pipeline? Permission denied with SELECT granted? Small files? |

## Week 15 — Troubleshooting (2) · Capstone build
| | |
|---|---|
| **Topics** | Phase 14 scenarios 8–14; post-incident notes; Phase 15 §7–8 |
| **Concepts** | Missing data, wrong counts, OOM, failed MERGE, bad files, dependencies; communication |
| **Hands-on** | Drills 8–13; "break my job" session with a peer; write 2 post-incident notes |
| **Mini-project** | **Capstone part 3:** new Daily Sales pipeline on UC with DQ, monitoring dashboard, alerts, grants |
| **Project link** | Write (or improve) a runbook for one migrated job |
| **Expected outcome** | You can recover from failures, and communicate about them |
| **Time** | Theory 1.5 h · Hands-on 8.5 h |
| **Interview Qs** | User says numbers are wrong: what do you do? OOM? Failed MERGE? Tell me about an incident |

## Week 16 — Capstone finish · Review · Interview prep
| | |
|---|---|
| **Topics** | Capstone docs & demo; [skill matrix](../reference/skill-matrix.md) self-assessment; [interview questions](../reference/interview-questions.md) |
| **Concepts** | Bringing it all together; explaining trade-offs |
| **Hands-on** | Finish the capstone (README, RUNBOOK, ADRs, validation report); record a 15-min demo; mock interview with a colleague |
| **Mini-project** | **Capstone demo** + "What I'd do differently" retrospective |
| **Project link** | Present a lessons-learned summary from the migration to your team (anonymise it for the repo) |
| **Expected outcome** | See [What should I be able to do after 3 months?](../docs/after-3-months.md) |
| **Time** | Theory 1 h · Hands-on 9 h |
| **Interview Qs** | The full list, especially "walk me through your capstone/migration project" |

---

## If you only have 12 weeks
Merge weeks 2+3 (SQL), 5+6 (Spark), 12+13 (DQ + CI/CD), and 14+15 (perf + troubleshooting). Keep weeks 7–9 (HMS→UC) and the capstone intact.
