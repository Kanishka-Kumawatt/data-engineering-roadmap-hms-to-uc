# Phase 14 — Production and Troubleshooting Skills

**Weeks:** 14–15 (and every day at work) · **Time:** ~12 h (2 h theory, 10 h drills)
**Goal:** Diagnose production problems calmly and systematically: **Symptom → Possible causes → Investigation → Fix → Prevention**.

> **Mentor note:** Troubleshooting skill is what most separates juniors from seniors. The method matters more than knowing every error. You can practise every scenario below: **break things on purpose in your sandbox, then fix them.** Ask a friend to break something for you without telling you what, and time yourself.

---

## The universal method

```
1. STABILISE   Is it urgent? Who's affected? Tell stakeholders "investigating, next update in 30 min".
2. READ        The full error. Bottom-up. Find "Caused by". Note the error class in [BRACKETS].
3. SCOPE       One table/job/user, or all? Since when? Did the last success differ? (time, code, data, infra)
4. LAYER       Which layer is failing?
                 name resolution → UC permission → cloud storage permission/network → file/format/schema
                 → data content → compute/resources → orchestration/dependency
5. REPRODUCE   Smallest failing case, in dev, with the same parameters and identity.
6. FIX         Root cause, not symptom. Through Git/PR when it's code.
7. RECOVER     Repair run / backfill / RESTORE. Verify outputs, not just job status.
8. PREVENT     Test, DQ rule, alert, grant-as-code, runbook entry. Write it in your error log.
9. COMMUNICATE What happened, impact, fix, prevention (a short post-incident note).
```

**"What changed?" questions:** `git log` / last deployment · `DESCRIBE HISTORY` on inputs · upstream job runs · `system.access.audit` (grant changes) · compute/DBR changes · new files in landing · calendar (month-end volumes, DST changes).

---

## Scenarios

### 1. Pipeline failed (generic)
- **Symptom:** Job run red; failure email.
- **Causes:** Code bug, data issue, permission, dependency, resource, transient cloud error.
- **Investigate:** Job run → failed task → error output + driver logs → first "Caused by" → was the *previous* run green? What changed between them?
- **Fix:** Depends on the layer. For transient errors (e.g. throttling) retry; otherwise fix the cause → repair run.
- **Prevent:** Retries for transient tasks, clear error messages in code, alerts with run links, a runbook.

### 2. Table not found
- **Symptom:** `[TABLE_OR_VIEW_NOT_FOUND] The table or view 'sales'.'orders' cannot be found`
- **Causes:** 2-level name resolving in the wrong catalog (very common after UC migration); table not yet migrated or renamed; typo; dropped; lacking `BROWSE`/`USE` privileges can make objects invisible; wrong workspace (catalog not bound to it).
- **Investigate:** `SELECT current_catalog(), current_schema()`; `SHOW TABLES IN <cat>.<schema> LIKE 'orders*'`; search Catalog Explorer; `system.information_schema.tables`; check `DESCRIBE HISTORY` / audit for DROP; catalog workspace bindings.
- **Fix:** Fully qualified name; parameterised catalog; migrate/restore (`UNDROP TABLE` for recently dropped managed tables).
- **Prevent:** Lint for 2-level names; integration tests per environment.

### 3. Permission denied
- **Symptom:** `[PERMISSION_DENIED]` / `[INSUFFICIENT_PERMISSIONS] User does not have SELECT on table ...` (or USE CATALOG / USE SCHEMA).
- **Causes:** Missing privilege at one of the three levels; grant to a person but the job runs as an SP; workspace-local group; revoked grant; ownership changed.
- **Investigate:** Who is the identity? (`SELECT current_user()` in the job) → `SHOW GRANTS \`<principal>\` ON CATALOG/SCHEMA/TABLE` → group membership → audit log for recent `updatePermissions`.
- **Fix:** Grant the minimal privileges to the right group/SP (through your grants-as-code process).
- **Prevent:** Grants as code; permission tests in QA run as the SP.

### 4. UC access issue (storage-level)
- **Symptom:** Grants look correct, but reading an external table/volume fails with a 403 / `AuthorizationPermissionMismatch` / "access denied" from cloud storage; or "no external location covers this path".
- **Causes:** Managed identity/IAM role lacks a storage role; storage firewall/private endpoint; the path isn't under an external location; the location uses the wrong credential; compute isn't UC-capable.
- **Investigate:** `DESCRIBE EXTERNAL LOCATION`; the "Test connection" button in Catalog Explorer; compare the table's location with external location URLs; check cluster access mode; ask the platform team to check cloud RBAC and network.
- **Fix:** Platform fix (RBAC/network), or create the right external location + grant `READ FILES`.
- **Prevent:** Storage readiness checks in the migration runbook; external location tests in CI/smoke tests.

### 5. Schema mismatch
- **Symptom:** `[DELTA_METADATA_MISMATCH]` / "A schema mismatch detected when writing to the Delta table"; or `CAST_INVALID_INPUT`; or new columns in `_rescued_data`.
- **Causes:** Source added/renamed/retyped a column; your code changed the output schema; CSV inference changed a type.
- **Investigate:** Compare `df.printSchema()` with `DESCRIBE TABLE`; look at the latest source files; check the source team's change notes.
- **Fix:** Decide: evolve (`mergeSchema` / `ALTER TABLE ADD COLUMNS`), cast, or reject. Never "just enable autoMerge everywhere".
- **Prevent:** Explicit schemas at ingestion; schema contracts with source owners; Auto Loader rescue mode; schema-change alerts.

### 6. Duplicate records
- **Symptom:** Uniqueness DQ check fails; dashboard totals too high.
- **Causes:** Re-run of a non-idempotent append; checkpoint deleted (files re-ingested); source resent data; join fan-out; MERGE condition on the wrong key.
- **Investigate:** `GROUP BY key HAVING COUNT(*) > 1` → look at `_ingested_at`/`_source_file` of the duplicates → `DESCRIBE HISTORY` to see which operation/run inserted them.
- **Fix:** Dedupe (window) + `RESTORE` or rebuild the affected partitions; fix the root cause (MERGE instead of append, restore the checkpoint).
- **Prevent:** Idempotent writes, a uniqueness DQ gate, never deleting checkpoints casually.

### 7. Job suddenly became slow
- **Symptom:** Duration 3× the baseline; SLA alert.
- **Causes:** Data growth/skew; small files; lost layout/filters (post-migration!); compute change; concurrency with other jobs; stale stats.
- **Investigate:** The [Phase 13 routine](phase-13-performance.md#1-the-investigation-routine). Compare the Spark UI of a fast run vs the slow run.
- **Fix/Prevent:** See Phase 13; add duration alerts and `OPTIMIZE`/predictive optimisation.

### 8. Data is missing
- **Symptom:** Yesterday's data is absent; a business user reports "no sales for store 42".
- **Causes:** Upstream didn't deliver; files landed in the wrong path; filter/join dropped rows (INNER JOIN to an incomplete dimension); late data outside the window; quarantine absorbed them; job succeeded on empty input.
- **Investigate:** Trace back by layer: Gold → Silver → Bronze → landing → source. Where does the record disappear? Check the quarantine table. Check Auto Loader-ingested files (`cloud_files_state`).
- **Fix:** Reprocess the window (backfill with `run_date`); fix the join (LEFT + unknown member).
- **Prevent:** Freshness and volume checks; "empty input = fail" for critical feeds; lineage awareness.

### 9. Wrong record counts
- **Symptom:** Gold count ≠ source report; migration counts differ.
- **Causes:** Different definitions (time zone day boundaries!); duplicates; filters; active writers during a migration copy; soft deletes counted differently.
- **Investigate:** Break down by date/partition to find *where* they differ → sample the differing keys → compare definitions.
- **Fix:** Correct the logic, or document it as an explained difference.
- **Prevent:** Agreed definitions in design docs; reconciliation checks.

### 10. Spark out-of-memory
- **Symptom:** `java.lang.OutOfMemoryError`, "Executor lost", "Driver is temporarily unavailable", `SparkOutOfMemoryError`.
- **Causes (driver):** `collect`/`toPandas`; broadcasting a large table; huge query plans (loops of `withColumn`/unions); listing millions of files.
- **Causes (executor):** skew; huge partitions; exploding joins; wide rows; too much caching.
- **Investigate:** Driver or executor? (Error text, driver logs, Spark UI executors tab.) Find the stage that failed; check spill and the max task.
- **Fix:** Remove the driver-side collects; fix skew; increase shuffle partitions; drop the broadcast hint; memory-optimised nodes as a *last* resort.
- **Prevent:** Code review checklist (no collect on big data), and testing with realistic volumes.

### 11. Failed MERGE
- **Symptom:** `[DELTA_MULTIPLE_SOURCE_ROW_MATCHING_TARGET_ROW_IN_MERGE]`; or `ConcurrentAppendException`; or a MERGE so slow it times out.
- **Causes:** Duplicate source keys; two jobs writing the same table/partitions at once; full-table scan of the target.
- **Investigate:** `SELECT key, COUNT(*) FROM source GROUP BY key HAVING COUNT(*) > 1`; check concurrent job schedules; MERGE metrics in `DESCRIBE HISTORY` (rows scanned/updated, files rewritten).
- **Fix:** Dedupe the source; serialise the writers or separate partitions; add a partition predicate to `ON`; cluster on the merge key.
- **Prevent:** Dedupe as a standard step before every MERGE; orchestrate writers.

### 12. Bad file / path
- **Symptom:** `[PATH_NOT_FOUND]`, `FileNotFoundException`, `MALFORMED_RECORD_IN_PARSING`, corrupted Parquet footer, Auto Loader failing on one file.
- **Causes:** Wrong path (e.g. `/mnt` after migration → Volumes); a file deleted or moved; a partial upload; a corrupt or empty file; the wrong format (`.csv` that's actually Excel).
- **Investigate:** `dbutils.fs.ls` / `LIST '/Volumes/...'`; open the file; check size and modification time; read it alone with `PERMISSIVE` + `_corrupt`.
- **Fix:** Correct the path/config; quarantine the bad file (move it to `/bad/`); ask the source to resend; `badRecordsPath`/rescue columns.
- **Prevent:** Landing-zone conventions (write to temp, then rename/complete marker); file validation step.

### 13. Dependency failure
- **Symptom:** Task skipped/failed because the upstream task/job failed; data stale because the upstream job didn't run.
- **Causes:** Upstream failure; schedule drift (upstream now finishes later); cross-job dependency implemented as "same time schedule".
- **Investigate:** Job DAG; upstream run history; `system.lakeflow.job_run_timeline`.
- **Fix:** Re-run upstream, then repair downstream.
- **Prevent:** Use real dependencies (task dependencies, job-run triggers, **table update triggers / file arrival triggers**) instead of time-based guessing; freshness checks before processing.

### 14. Bonus: migration-specific quick list
| Symptom | First thing to check |
|---|---|
| Works on old cluster, fails on new | Access mode (Standard vs Dedicated) + unsupported APIs |
| `/mnt/...` path not found | Mounts aren't for UC → Volume / external location path |
| View returns different results than in HMS | View rewritten with the wrong catalog/filter → compare SQL |
| Old job still writing to HMS | Audit logs / job list; revoke `MODIFY` on the HMS object |
| SYNC'd table changes "by itself" | Something is still writing via the HMS name to the same files |

Full index: [reference/troubleshooting-index.md](../reference/troubleshooting-index.md)

---

## Drills (do them in your sandbox)
For each scenario 1–13: **create the failure on purpose**, then fix it using the method above, writing an error-log entry each time. Then pair up: someone breaks one of your jobs without telling you how, and you time yourself.

## Post-incident note template
```markdown
## Incident: Gold sales missing for 2026-11-03
- Impact: Sales dashboard showed 0 revenue for 1 store-day, 07:00–10:30
- Detection: Business user report (gap: no freshness alert per store)
- Root cause: New store_id not in dim_store; INNER JOIN dropped its orders
- Fix: LEFT JOIN + unknown member; backfilled 2026-11-03
- Prevention: RI check dim_store vs silver.orders (WARN); store onboarding added to source contract
- Follow-ups: DE-311, DE-312
```

## After this phase you should be able to explain
- [ ] Your step-by-step troubleshooting method
- [ ] How to tell a UC permission problem from a cloud storage problem
- [ ] How to find "what changed"
- [ ] How you recover data after a bad run
- [ ] How you write up an incident

## Beginner vs experienced
| Beginner | Experienced |
|---|---|
| Googles the error message | Identifies the layer, forms a hypothesis, tests it with the smallest case |
| Fixes the symptom (re-run) | Fixes the root cause and adds prevention |
| Silent while fixing | Communicates impact and ETA early |

## Interview questions
1. Walk me through how you debug a failed pipeline.
2. A user says "the numbers are wrong". What do you do?
3. Your job fails with OOM. How do you investigate?
4. A MERGE fails with multiple source rows matching. Why, and how do you fix it?
5. Permission denied on a UC table, even though the user has SELECT. Why?
6. How do you find duplicates and their source?
7. Tell me about a production issue you resolved. (Prepare a real story from your project.)
