# Production-Readiness Checklist

A pipeline is **production-ready** only when every applicable item is ✅ or has a documented, accepted exception.

## Correctness
- [ ] Business definitions documented and signed off
- [ ] Output reconciled against a trusted source/report for ≥1 week (or a representative period)
- [ ] Idempotent: re-runs and retries don't duplicate or corrupt data
- [ ] Handles late, updated, deleted and duplicate source records as designed
- [ ] Schema changes from the source are detected (rescue column / alert) and never silently propagated

## Reliability
- [ ] Runs as a **service principal**, on job compute/serverless (not an all-purpose cluster)
- [ ] Retries on transient-failure tasks; timeouts on all tasks
- [ ] `max_concurrent_runs` set appropriately (usually 1 for MERGE pipelines)
- [ ] Real dependencies (task deps, table/file triggers), not time-based guesses
- [ ] Backfill procedure tested (`run_date`/window parameters)
- [ ] Recovery tested: repair run; Delta `RESTORE` to a known-good version

## Data quality
- [ ] FAIL rules: keys not NULL, keys unique, mandatory reference data present
- [ ] WARN rules: volume anomaly, quarantine rate, value ranges
- [ ] Freshness check against the SLA
- [ ] DQ results stored historically (`ops.dq_results`)

## Observability
- [ ] Failure notifications go to a monitored channel (not a person's inbox only)
- [ ] Duration threshold alert
- [ ] Run audit table (rows in/out, status, duration)
- [ ] Dashboard: runs, durations, DQ, freshness
- [ ] Logs are meaningful and contain no secrets or PII

## Security & governance
- [ ] Least-privilege grants to groups/SPs, managed as code
- [ ] Objects owned by a group/SP, not a person
- [ ] PII identified, tagged and masked/filtered where required
- [ ] Secrets only in secret scopes / CI secret stores
- [ ] Catalog bound to the right workspaces (where used)
- [ ] Table/column comments; lineage visible in UC

## Performance & cost
- [ ] Meets SLA at expected peak volume with headroom
- [ ] Table layout: clustering/partitioning appropriate; OPTIMIZE/predictive optimisation in place
- [ ] Compute right-sized; auto-termination; cluster policy compliant
- [ ] Cost per run known (system billing tables)

## Delivery
- [ ] Code in Git; deployed by CI/CD from a tagged release
- [ ] Unit tests in CI; integration test in QA
- [ ] Environment config separated; same artifact across environments
- [ ] Rollback plan for code **and** data documented

## Documentation & handover
- [ ] README (what/how), RUNBOOK (operate), design doc/ADRs (why)
- [ ] Owner and on-call/support contacts documented
- [ ] Consumers know where the data is, its SLA, and how to request access
- [ ] Known limitations listed

## Migration-specific (HMS → UC)
- [ ] All reads/writes use UC names; the scanner reports 0 legacy patterns
- [ ] Compute uses UC-capable access mode
- [ ] Validation report signed off (incl. explained differences)
- [ ] HMS sources read-only; retention/rollback window agreed; decommission date set
