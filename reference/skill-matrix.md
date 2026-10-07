# Skill Matrix: Beginner → Intermediate → Production Ready

Rate yourself monthly (B / I / P), commit the ratings, and watch the trend. "Production ready" means *you can do it unsupervised on a real project, and explain the trade-offs.*

| Area | Beginner | Intermediate | Production Ready | Wk1 | Wk4 | Wk8 | Wk12 | Wk16 |
|---|---|---|---|---|---|---|---|---|
| **DE fundamentals** | Defines lake/warehouse/lakehouse, ETL/ELT, medallion | Places a real system's components in the architecture | Chooses architecture patterns for a requirement and justifies the trade-offs | | | | | |
| **SQL** | SELECT/JOIN/GROUP BY on clean data | Windows, CTEs, anti joins; dedupe; reconciliation | Reads plans; writes modular, performant, reviewed SQL; anticipates NULLs/fan-out | | | | | |
| **Python** | Scripts in notebooks | Functions, modules, config, logging, tests | Typed, packaged, tested, config-driven code others reuse | | | | | |
| **Spark** | Writes DataFrame code | Explains jobs/stages/shuffles; uses broadcast; reads the Spark UI | Diagnoses skew/spill/OOM and fixes the root cause | | | | | |
| **Databricks** | Runs notebooks on a cluster | Multi-task jobs, parameters, secrets, Git folders | Bundles, SP run-as, policies, monitoring via system tables | | | | | |
| **Delta Lake** | Creates/queries Delta tables | MERGE, time travel, OPTIMIZE/VACUUM, schema evolution | Designs incremental, idempotent, well-laid-out tables; recovers from incidents | | | | | |
| **Unity Catalog** | Explains the 3-level namespace | Grants, ownership, external locations, volumes | Designs catalog/grant models; diagnoses UC vs cloud permission issues | | | | | |
| **HMS→UC migration** | Runs provided scripts | Chooses SYNC/CLONE/CTAS per table; recreates views; maps grants | Plans waves, validates, handles rollback/cutover, converts code, signs off | | | | | |
| **Pipeline development** | Builds a full-load notebook | Bronze/Silver/Gold, incremental, DQ, parameterised | Requirement → design → delivered, monitored, documented pipeline | | | | | |
| **Data modeling** | Knows fact vs dim | Star schema, SCD2, surrogate keys | Conformed dimensions; grain discipline; models for consumers | | | | | |
| **Git** | clone/commit/push | Branches, PRs, conflicts | Small reviewable PRs; reviews others; release tags | | | | | |
| **Testing & DQ** | Manual checks | Unit tests, DQ rules | Layered tests + DQ gates + reconciliation in CI and in jobs | | | | | |
| **CI/CD** | Knows what CI/CD is | Runs bundle deploy; CI runs tests | Multi-env promotion, approvals, code + data rollback | | | | | |
| **Performance** | "Add nodes" | Spots skew/small files | Systematic investigation; layout + code fixes; measures | | | | | |
| **Troubleshooting** | Googles errors | Identifies the failing layer | Root cause + recovery + prevention + clear comms | | | | | |
| **Communication** | Answers questions | Status updates, good questions | Design docs, runbooks, incident notes, demos | | | | | |

**Target by week 16:** Intermediate everywhere; **Production Ready** in SQL, HMS→UC migration, Delta Lake and troubleshooting, the skills your project uses daily.
