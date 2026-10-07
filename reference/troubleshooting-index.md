# Troubleshooting Index

A quick lookup from symptom to where to read. Full method: [Phase 14](../phases/phase-14-troubleshooting.md).

| Symptom / error (paraphrased) | First checks | Read |
|---|---|---|
| `TABLE_OR_VIEW_NOT_FOUND` | `current_catalog()`, 3-level name, migrated yet?, workspace binding | Phase 14 §2, Phase 7 §15 |
| `PERMISSION_DENIED` / `INSUFFICIENT_PERMISSIONS` | Identity (`current_user()`), `USE CATALOG` + `USE SCHEMA` + object privilege, group type | Phase 14 §3, Phase 7 §8 |
| 403 / access denied from storage | External location coverage, credential, cloud RBAC, firewall | Phase 14 §4, Phase 15 §1 |
| Location overlap | Other tables/volumes on parent/child paths | Phase 7 §7, §15, scenario 5 |
| SYNC status not OK | Managed vs external, mount path, format | Phase 7 §11.2, scenario 2 |
| View broken after migration | 2-level names inside the view SQL | Phase 7 §11.5 |
| `input_file_name` / `sparkContext` not supported | Access mode; use `_metadata`, the DataFrame API | Phase 7 §12 |
| Schema mismatch on write | Source change vs code change; evolve/cast/reject | Phase 14 §5, Phase 6 §3 |
| `DELTA_MULTIPLE_SOURCE_ROW_MATCHING_TARGET_ROW_IN_MERGE` | Duplicate source keys → dedupe | Phase 14 §11, Phase 6 §3 |
| `ConcurrentAppendException` | Concurrent writers to the same table/partitions | Phase 14 §11 |
| Duplicates in Silver/Gold | Non-idempotent append, deleted checkpoint, fan-out | Phase 14 §6 |
| Missing data | Trace Gold → Silver → Bronze → landing; quarantine; INNER joins | Phase 14 §8 |
| Counts differ | Definitions/time zones; writers during the copy | Phase 14 §9, Phase 7 scenarios 3 & 6 |
| Driver OOM | `collect`, `toPandas`, big broadcast, huge plans | Phase 14 §10, Phase 4 §10 |
| Executor OOM / lost | Skew, big partitions, exploding joins | Phase 14 §10, Phase 13 §2 |
| Job suddenly slow | What changed? Spark UI fast vs slow run | Phase 13 §1, §5 |
| One task much slower than the rest | Skew | Phase 4 §6, Phase 13 §2 |
| Many tiny files / slow listing | Small files → OPTIMIZE/clustering | Phase 6 §3, Phase 13 §4 |
| `PATH_NOT_FOUND` / `/mnt` fails | Mount not usable under UC → Volume/external path | Phase 14 §12 |
| Stream reprocessed everything | Checkpoint/source path changed | Phase 7 scenario 7, Phase 15 §2 |
| Works for me, fails in the job | Run-as SP lacks grants; library missing on job compute | Phase 5 troubleshooting, Phase 7 scenario 4 |
| `ModuleNotFoundError` | Library not on the job's compute/environment; `sys.path` | Phase 3 §6, Phase 5 |
| `Py4JJavaError` | Scroll to "Caused by" | Phase 4 troubleshooting |
