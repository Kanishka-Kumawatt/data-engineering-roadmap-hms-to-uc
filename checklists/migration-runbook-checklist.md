# HMS → UC Migration Runbook (per schema / wave)

Copy this file per wave (`docs/migration-wave-<n>.md`), fill it in, and keep it in Git. Details: [Phase 7 §13](../phases/phase-07-hms-to-unity-catalog.md#13-the-data-engineers-playbook).

**Wave:** ____ · **Schema(s):** ____ · **Owner:** ____ · **Data owner(s):** ____ · **Target catalog:** ____
**Dev date:** ____ · **QA date:** ____ · **Prod cutover window:** ____ · **Rollback window ends:** ____

## A. Before
- [ ] Inventory complete (type, format, location, size, last modified, owner) → link: ____
- [ ] Each object has a method (SYNC / DEEP CLONE / CTAS / recreate / manual) + reason → plan link: ____
- [ ] Dependencies mapped: views (creation order), jobs, notebooks, dashboards, external consumers
- [ ] All writers identified (code search + jobs + audit/lineage), not just the readers
- [ ] Identities: account groups exist; workspace-local groups mapped; SPs for jobs exist
- [ ] Storage: every external path is covered by an external location; mounts resolved to cloud paths
- [ ] Location overlaps checked and resolved
- [ ] Compute: UC-capable clusters/policies ready for all affected jobs
- [ ] Code changes identified (scanner/UCX linter) and PRs ready
- [ ] Grants mapping (HMS → UC) reviewed by the data owner
- [ ] **Baselines captured:** counts, fingerprints, Delta versions, job durations
- [ ] Freeze window and comms agreed; go/no-go criteria and decision owner named

## B. During (dev → qa → prod)
- [ ] Catalog/schemas created with managed locations; owners set
- [ ] Tables migrated (SYNC dry run reviewed first); all statements logged to the audit table
- [ ] Views recreated in dependency order with 3-level names
- [ ] Functions recreated
- [ ] Grants applied (schema level where possible); ownership → groups
- [ ] Code PRs merged and deployed; jobs updated (names, paths, compute, run-as)
- [ ] Parallel run / comparison done (qa)
- [ ] **Prod cutover:** writers stopped → final incremental sync/clone → jobs switched → writers resumed on UC

## C. Validation
- [ ] Objects: all present, correct type/location/format
- [ ] Schemas match (or differences explained)
- [ ] Counts + fingerprints match; EXCEPT/hash for critical tables
- [ ] Views return the same results as before
- [ ] Permissions: positive and negative tests run as real principals
- [ ] Jobs green on UC; consumer dashboards verified
- [ ] Performance within baseline tolerance
- [ ] Validation report written and signed off → link: ____

## D. Troubleshooting log
| Time | Object | Symptom | Cause | Fix | Prevention |
|---|---|---|---|---|---|
| | | | | | |

## E. Post-migration
- [ ] HMS objects made read-only (revoke MODIFY / stop writers); marked as migrated
- [ ] Default catalog updated where appropriate
- [ ] Monitoring for 2–4 weeks: job failures, audit for HMS access, user tickets
- [ ] No VACUUM/DROP on HMS sources during the rollback window
- [ ] Decommission (after sign-off): drop HMS objects, remove mounts and keys, update docs
- [ ] Lessons learned recorded; runbook improved for the next wave

## Rollback plan (fill in per method used)
| Method | Rollback action | Data written after cutover | Owner |
|---|---|---|---|
| SYNC | Repoint consumers to HMS names; `RESTORE` to version ____ if a bad write occurred | Same files (already visible in HMS) | |
| DEEP CLONE / CTAS | Repoint consumers to HMS; redeploy previous release tag ____ | **Not** in HMS: back-fill plan: ____ | |
| Views / grants | Old HMS views still exist; re-apply the HMS grants export ____ | n/a | |
