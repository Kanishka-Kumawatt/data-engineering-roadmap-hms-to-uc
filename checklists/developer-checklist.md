# Data Engineer Development Checklist

Use it on every ticket. Copy the relevant sections into your PR description.

## 1. Before coding: understand
- [ ] I can restate the requirement in my own words, and the requester agreed
- [ ] Consumers, use case and **definition of done** are known
- [ ] Business definitions are written down (e.g. revenue, "day", time zone, cancelled/refunded)
- [ ] SLA / freshness requirement is known
- [ ] Source(s) identified: owner, format, frequency, volume, keys, lateness, history
- [ ] I profiled a sample of the source (counts, NULLs, duplicates, ranges)
- [ ] Open questions are asked and their answers recorded

## 2. Design
- [ ] Grain and keys of every output table are defined
- [ ] Layer chosen (Bronze/Silver/Gold), plus a target catalog/schema/table name following conventions
- [ ] Managed vs external decided (default: managed)
- [ ] Full vs incremental decided; **idempotency** strategy (MERGE / replaceWhere / checkpoint)
- [ ] Late-arriving and updated data handled
- [ ] Bad record handling decided (fail / quarantine / warn)
- [ ] DQ rules listed
- [ ] Security: who reads, who writes, PII? Grants planned for groups/SPs
- [ ] Design doc (for non-trivial work) reviewed

## 3. Build
- [ ] Branch created from up-to-date `main`, named after the ticket
- [ ] Logic in functions/modules; notebooks are thin entry points
- [ ] **Fully qualified 3-level names**, with the catalog from config/parameters
- [ ] No hard-coded environments, paths or credentials; secrets come from secret scopes
- [ ] Explicit schemas for file sources
- [ ] No `collect()`/`toPandas()` on large data; no unnecessary `count()`s
- [ ] Built-in functions instead of Python UDFs where possible
- [ ] Dedupe before every MERGE
- [ ] Meaningful logging (rows in/out, parameters, timings)
- [ ] Errors raised with context; no swallowed exceptions
- [ ] Table and column comments; tags for PII

## 4. Test
- [ ] Unit tests for transformations (incl. NULL, empty, duplicate, boundary/time-zone cases)
- [ ] Ran end to end in dev with realistic data
- [ ] **Re-ran the same input: same output** (idempotent)
- [ ] Late-data / update scenario tested
- [ ] Counts reconcile (source → bronze → silver → gold)
- [ ] DQ rules pass, and fail when they should
- [ ] Tested as the **run-as identity** (SP) in QA, not just as myself
- [ ] Performance acceptable on representative volume

## 5. Commit & review
- [ ] Small, focused commits with clear messages
- [ ] Lint/format passes; CI green
- [ ] PR description: what / why / how tested / risks / rollout
- [ ] No secrets, data files or notebook outputs with data committed
- [ ] Reviewer comments addressed

## 6. Deploy
- [ ] Deployed via bundle/CI, not manually
- [ ] Config/parameters correct per environment
- [ ] Grants for new objects applied (grants as code)
- [ ] Job: schedule/trigger, retries, timeout, max concurrent runs, notifications
- [ ] Backfill plan (if needed) executed and verified

## 7. Operate
- [ ] Monitoring: job alerts, freshness, volume, DQ results
- [ ] RUNBOOK updated (re-run, backfill, common failures, contacts)
- [ ] Stakeholders informed: what's live, where, and how to request access
- [ ] Ticket updated/closed with links (PR, job, dashboard)
