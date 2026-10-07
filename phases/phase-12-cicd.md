# Phase 12 — CI/CD and Deployment

**Weeks:** 12–13 · **Time:** ~12 h (3 h theory, 9 h hands-on)
**Goal:** Understand how code goes from your branch to production automatically and safely, and be able to set up a basic pipeline for a Databricks project.

> **Mentor note:** You may not own the CI/CD platform on your project, but you must understand it. When your PR "fails CI" or a deployment to QA breaks, you need to know where to look. Keep it simple: **CI = automatically check every change; CD = automatically deploy approved changes.**

---

## 1. The lifecycle

```
 Developer laptop / dev workspace         CI (on every PR)            CD (on merge / tag)
 ┌──────────────────────────┐   push    ┌──────────────────┐  merge  ┌──────────────┐ approve ┌──────────────┐
 │ feature branch           │ ────────▶ │ lint · unit tests│ ──────▶ │ deploy → QA  │ ──────▶ │ deploy → PROD│
 │ run in dev catalog       │           │ bundle validate  │         │ integration  │  (gate) │ smoke test   │
 └──────────────────────────┘           └──────────────────┘         │ tests        │         └──────────────┘
                                                                     └──────────────┘
```

| Environment | Purpose | Who deploys | Data |
|---|---|---|---|
| **Dev** | Build and experiment | You (bundle `-t dev`, deploys into *your* user space) | Samples / synthetic |
| **QA/Test** | Integration tests, UAT | CI/CD service principal | Prod-like |
| **Prod** | Real consumers | CI/CD SP, after approval | Real |

## 2. CI fundamentals
On every PR: **lint** (`ruff`, `sqlfluff`), **unit tests** (`pytest`), **bundle validate**, and optionally a build of the wheel. The PR can't merge unless they pass (**branch protection**).

## 3. Databricks Asset Bundles (DABs)

A bundle describes your jobs, pipelines and code as YAML, and deploys them to any target with one command.

```yaml
# databricks.yml
bundle:
  name: retail_pipeline

include:
  - resources/*.yml

variables:
  catalog:
    description: Target UC catalog
  run_as_sp:
    description: Service principal application id

targets:
  dev:
    mode: development          # prefixes resources with your name, pauses schedules
    default: true
    workspace:
      host: https://adb-1111111111111111.11.azuredatabricks.net
    variables:
      catalog: retail_dev
  qa:
    workspace:
      host: https://adb-2222222222222222.12.azuredatabricks.net
    variables:
      catalog: retail_qa
      run_as_sp: "00000000-0000-0000-0000-000000000002"
    run_as:
      service_principal_name: ${var.run_as_sp}
  prod:
    mode: production
    workspace:
      host: https://adb-3333333333333333.13.azuredatabricks.net
    variables:
      catalog: retail_prod
      run_as_sp: "00000000-0000-0000-0000-000000000003"
    run_as:
      service_principal_name: ${var.run_as_sp}
```
```yaml
# resources/daily_sales_job.yml
resources:
  jobs:
    daily_sales:
      name: daily_sales_${bundle.target}
      schedule:
        quartz_cron_expression: "0 30 5 * * ?"
        timezone_id: Asia/Dubai
      email_notifications:
        on_failure: [data-oncall@example.com]
      parameters:
        - name: catalog
          default: ${var.catalog}
        - name: run_date
          default: ""
      tasks:
        - task_key: bronze
          notebook_task: { notebook_path: ../notebooks/01_bronze.py }
          max_retries: 2
        - task_key: silver
          depends_on: [{ task_key: bronze }]
          notebook_task: { notebook_path: ../notebooks/02_silver.py }
        - task_key: gold
          depends_on: [{ task_key: silver }]
          notebook_task: { notebook_path: ../notebooks/03_gold.py }
        - task_key: dq_gate
          depends_on: [{ task_key: gold }]
          notebook_task: { notebook_path: ../notebooks/04_dq_gate.py }
      timeout_seconds: 3600
```
(This example uses serverless job compute by omitting cluster config. Add `job_clusters` if your workspace uses classic compute, with a UC-capable `data_security_mode`.)

```bash
databricks bundle validate -t dev
databricks bundle deploy   -t dev
databricks bundle run      -t dev daily_sales
databricks bundle deploy   -t prod      # normally only from CI/CD
```

## 4. A GitHub Actions example

```yaml
# .github/workflows/ci.yml
name: ci
on:
  pull_request:
  push:
    branches: [main]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - uses: actions/setup-java@v4
        with: { distribution: temurin, java-version: "17" }
      - run: pip install -r requirements-dev.txt
      - run: ruff check src tests
      - run: pytest -q tests/unit
  deploy-qa:
    if: github.ref == 'refs/heads/main'
    needs: test
    runs-on: ubuntu-latest
    environment: qa                       # GitHub environment holds the secrets
    steps:
      - uses: actions/checkout@v4
      - uses: databricks/setup-cli@main
      - run: databricks bundle deploy -t qa
        env:
          DATABRICKS_HOST: ${{ secrets.DATABRICKS_HOST_QA }}
          DATABRICKS_CLIENT_ID: ${{ secrets.SP_CLIENT_ID_QA }}
          DATABRICKS_CLIENT_SECRET: ${{ secrets.SP_CLIENT_SECRET_QA }}
```
Prod deployment: a separate job triggered by a **release tag**, with a required reviewer on the `prod` GitHub environment. (Azure DevOps pipelines follow the same idea with stages and approvals.)

## 5. Environment-specific configuration & secrets

| Kind | Example | Where it lives |
|---|---|---|
| Non-secret config | catalog name, paths, thresholds | Bundle variables / `conf/<env>.yaml` / job parameters |
| Secrets (runtime) | DB password, API key | **Databricks secret scopes** (Key Vault-backed on Azure), read via `dbutils.secrets.get` |
| Secrets (deployment) | SP client secret for CI | **CI secret store** (GitHub environments / Azure DevOps variable groups), or better, **OIDC workload identity federation** (no stored secret) |

**Rule:** the *same artifact* is deployed to every environment. Only config differs.

## 6. Code promotion & rollback
- **Promotion:** merge to `main` → auto-deploy QA → tests pass → tag `v1.5.0` → approved deploy to prod.
- **Rollback (code):** re-deploy the previous tag (`git checkout v1.4.0 && databricks bundle deploy -t prod`, via CI).
- **Rollback (data):** code rollback doesn't undo data changes. Use Delta `RESTORE` to the version before the bad run (and record versions in your run audit table).
- **Schema changes** (DDL) are deployed as versioned, idempotent scripts (`ALTER TABLE ... ADD COLUMN IF NOT EXISTS`-style logic), in order, through the same pipeline.

## 7. Grants and UC objects as code
Catalogs, schemas, external locations and grants are often managed by the **platform team with Terraform** (`databricks_catalog`, `databricks_grants`, …) or by SQL scripts in the repo, applied by CI. Ask how your project does it. For a migration, grants-as-code is how you guarantee QA and prod get identical permissions.

---

## How this connects to HMS→UC
- Migrated jobs are redeployed through CI/CD with new catalogs/paths. The bundle `catalog` variable is how one codebase targets `hive_metastore` (before) or `sales_prod` (after) during a parallel run.
- Migration scripts (SYNC/CLONE/grants) can be packaged as a bundle job, run per environment: `dev → qa → prod`, same code.
- Rollback for a migrated pipeline = redeploy the previous tag pointing back to HMS, *if* the HMS tables are still intact (Phase 7 §14).

## Hands-on
1. Install the Databricks CLI; authenticate to Free Edition (`databricks auth login`).
2. `databricks bundle init` (default-python template); read every generated file.
3. Convert your Phase 5 job into a bundle with `dev` and `prod` targets (prod can be a second catalog in the same Free workspace).
4. Add the GitHub Actions CI workflow (lint + unit tests) to your capstone repo; make a PR fail, then fix it.
5. Simulate rollback: deploy v1, deploy a broken v2, redeploy v1.

## After this phase you should be able to explain
- [ ] CI vs CD
- [ ] Dev → QA → Prod, and what differs between them
- [ ] What an Asset Bundle is, and what `validate/deploy/run` do
- [ ] Where config vs secrets live, per environment
- [ ] How you roll back code, and how you roll back data

## Beginner vs experienced
| Beginner | Experienced |
|---|---|
| Deploys by importing notebooks via the UI | Bundles + CI/CD + approvals + run-as SPs; nothing manual in prod |
| Rollback = "fix forward quickly" | Tagged releases, data restore points, documented rollback |

## Interview questions
1. What is CI/CD, and why does it matter for data pipelines?
2. How do you deploy Databricks jobs across environments?
3. How do you manage secrets in CI/CD?
4. How would you roll back a bad deployment that also wrote bad data?
5. What are Databricks Asset Bundles?
6. Why should production jobs run as a service principal?
