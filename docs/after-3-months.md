# What Should I Be Able to Do After 3 Months?

> If you've followed the roadmap, done the exercises and finished the capstone, this is what you should be able to do. Use it as a final self-test. For each item, ask yourself: **"Could I do this on Monday, at work, with only the docs to help?"**

## 1. On the HMS → UC migration project
- [ ] **Explain** to a new joiner, in 5 minutes with a whiteboard, why the organisation is migrating, what HMS and UC are, and what the before/after architecture looks like.
- [ ] **Assess** a schema: produce the inventory, classify each object, map dependencies (views, jobs, writers) and spot blockers (mounts, DBFS root, overlaps, non-UC compute, legacy code).
- [ ] **Choose and justify** the method for each table (SYNC / DEEP CLONE / CTAS / recreate), including what it means for history, storage cost and rollback.
- [ ] **Execute** a wave in dev/qa: tables, views in dependency order, functions, grants, ownership, with every statement audited.
- [ ] **Convert code**: 3-level names, `/mnt` → Volumes/external paths, `_metadata`, no RDD/storage keys, and updated jobs with the right compute and run-as.
- [ ] **Validate**: object, schema, count, fingerprint and EXCEPT/hash checks, permission tests run as real principals, consumer checks, and a signed-off report with explained differences.
- [ ] **Troubleshoot** the common failures on your own: not found, permission denied, storage 403, location overlap, SYNC refusals, broken views, count drift, checkpoint issues.
- [ ] **Plan the cutover and rollback**, and know what happens to data written after cutover for each method.

## 2. As a pipeline developer
- [ ] Turn a vague ticket into a **1–2 page design** with definitions, grain, incremental strategy, DQ and security.
- [ ] Build **Bronze → Silver → Gold** that is incremental, idempotent, late-data aware, parameterised and quarantines bad records.
- [ ] Write **unit tests** for transformations, plus DQ gates that fail the job when they should.
- [ ] **Deploy** with an Asset Bundle to dev and prod; run CI on PRs.
- [ ] **Schedule and monitor**: retries, timeouts, alerts, run audit, freshness, a dashboard.
- [ ] **Backfill** a date range safely, and **recover** a bad run (repair run, `RESTORE`).

## 3. As an engineer on a team
- [ ] Work in Git with small PRs, good descriptions and test evidence. Resolve conflicts. Review others' code.
- [ ] Write a **runbook**, an **ADR**, a **status update** and a **post-incident note**.
- [ ] Ask clarifying questions that save rework, and estimate tasks honestly.
- [ ] Investigate a **slow job** with the Spark UI / query profile and explain the cause.
- [ ] Answer most questions in the [interview list](../reference/interview-questions.md) with examples from your own work.

## 4. What you're *not* expected to master yet (and that's fine)
- Designing a whole platform (networking, workspace topology, metastore setup), which is usually the platform team's job
- Complex streaming (stateful aggregations, exactly-once across systems)
- Deep Spark internals tuning (memory fractions, custom partitioners)
- Terraform for UC, or advanced CI/CD platform engineering
- Leading a migration programme alone

These are the **next 6–12 months**: take on more waves, own a production pipeline end to end, join incident rotations, and pair with the platform team.

## 5. Your evidence portfolio (bring it to reviews and interviews)
- This repo, with your solutions, notes, error log and PROGRESS.md history
- The capstone repo: green CI, a bundle, a validation report, a runbook, ADRs and a demo recording
- 3 anonymised STAR stories from the real project: one migration problem, one production issue, one improvement you proposed
- Your skill matrix ratings from week 1 to week 16

## 6. Next steps after week 16
1. Sit the **Databricks Certified Data Engineer Associate** exam (you'll be well prepared).
2. Volunteer to own a migration wave end to end.
3. Read *Designing Data-Intensive Applications*.
4. Add streaming depth: rebuild the capstone's Silver as a stateful streaming job with watermarks.
5. Learn the platform layer: how your project's metastore, external locations and workspaces were set up (Terraform).
6. Start mentoring the next beginner. Teaching is the fastest way to find the gaps in your own understanding.
