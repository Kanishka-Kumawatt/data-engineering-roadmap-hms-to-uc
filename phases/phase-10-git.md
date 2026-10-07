# Phase 10 — Git and Software Development Practices

**Weeks:** Start in week 2, use it continuously · **Time:** ~8 h focused + daily use
**Goal:** Work with Git like a professional teammate: clean branches, meaningful commits, good PRs, painless conflict resolution, and a well-structured repository.

> **Mentor note:** From week 2, **every exercise you do gets committed** to your fork of this repo. By week 16 you'll have used Git hundreds of times without thinking about it, and you'll have a portfolio.

---

## 1. The mental model

```
 Working directory ──git add──▶ Staging area ──git commit──▶ Local repo ──git push──▶ Remote (GitHub/Azure DevOps/GitLab)
        ▲                                                         │                         │
        └────────────────────────── git checkout / switch ────────┘◀──── git pull/fetch ────┘
```
A **commit** is a snapshot plus a message plus a parent pointer. A **branch** is just a movable label pointing at a commit.

## 2. Daily commands

```bash
git clone https://github.com/org/retail-pipeline.git
git switch main && git pull                          # always start from an up-to-date main
git switch -c feature/DE-142-daily-sales             # new branch per ticket
# ... edit ...
git status                                           # what changed?
git diff                                             # exactly what changed?
git add src/retail_pipeline/silver.py tests/unit/test_silver.py
git commit -m "DE-142: dedupe POS orders by latest updated_at in silver"
git push -u origin feature/DE-142-daily-sales        # then open a Pull Request
# after review feedback:
git add -p && git commit -m "DE-142: handle NULL updated_at in dedupe" && git push
# keep the branch current with main:
git fetch origin && git rebase origin/main           # or: git merge origin/main (follow team convention)
```

Useful extras: `git log --oneline --graph`, `git stash`, `git restore <file>`, `git revert <sha>` (safe undo on shared branches), `git blame` (who changed this line and why), `git tag v1.4.0`.

**Never on shared branches:** `git push --force` (use `--force-with-lease` on *your own* feature branch only), committing secrets, or rewriting `main`'s history.

## 3. Branching strategy

Most DE teams use a simple **trunk-based / GitHub flow**:
```
main ────●────────●──────────●───────── (always deployable; protected; deploys to prod via release/tag)
          \      /            \
feature/DE-142 ●──●     feature/DE-150 ●──●
```
Some use `develop` + `release/*` (GitFlow) when releases are infrequent. **Learn your team's convention, and follow it exactly.**

Branch names: `feature/DE-142-daily-sales`, `fix/DE-160-null-store-id`, `migration/wave2-finance`.

## 4. Commits

Good: `DE-142: add quarantine table for orders with NULL store_id`
Bad: `fix`, `changes`, `wip`, `final final v2`

Rules: one logical change per commit; the message says **what and why**; the code works at every commit.

## 5. Pull requests and code review

### PR description template
```markdown
## What
Silver orders: dedupe by latest `updated_at`, quarantine invalid rows.
## Why
DE-142. Source resends full orders on update; duplicates caused MERGE failures.
## How tested
- Unit tests: tests/unit/test_silver.py (5 new)
- Dev run: job run #8812 — 2,014,332 in / 2,011,980 good / 2,352 quarantined
- Idempotency: re-ran same batch, gold unchanged (screenshot)
## Risks / rollout
New table silver.orders_quarantine needs grant for sp_retail_pipeline_qa/prod.
## Checklist
- [x] No secrets/hard-coded env  - [x] 3-level names / catalog param  - [x] Tests pass  - [x] Docs updated
```

### Being reviewed
Keep PRs small (<400 lines changed where possible), respond to every comment, and don't take it personally. Reviews are the fastest way to learn.

### Reviewing others (yes, as a beginner too)
Look for: hard-coded environments or paths, 2-level table names, missing tests, `collect()` on big data, swallowed exceptions, no handling for re-runs, unclear names. Ask questions rather than making demands: "What happens if this runs twice?"

## 6. Merge conflicts

```
<<<<<<< HEAD (yours)
target_catalog: retail_dev
=======
target_catalog: retail_dev_v2
>>>>>>> origin/main (theirs)
```
1. Understand **both** changes (talk to the other author if needed).
2. Edit the file to the correct combined result; remove the markers.
3. `git add <file>` → `git rebase --continue` (or `git commit` for a merge).
4. **Run the tests again.**

**Practise:** create a conflict on purpose with two branches editing the same line, then resolve it.

## 7. .gitignore and what never goes in Git

Never commit: secrets/tokens/passwords, `.env`, `.databrickscfg`, data files (CSV/Parquet), `metastore_db/`, `spark-warehouse/`, `__pycache__/`, `.venv/`, notebook outputs containing data. See this repo's [.gitignore](../.gitignore).

**If you commit a secret:** consider it compromised. **Revoke/rotate it immediately**, then clean the history. Deleting the line in a new commit isn't enough, because it's still in the history.

## 8. Versioning

- **Semantic versioning** for libraries/wheels: `MAJOR.MINOR.PATCH` (1.4.2). A breaking change bumps MAJOR.
- **Tags/releases** mark what's deployed to prod (`v2026.10.20` or `v1.4.0`), which makes rollback = "deploy the previous tag".
- A `CHANGELOG.md` for user-facing changes.

## 9. A professional DE repository structure

```
retail-pipeline/
├── README.md               # what it is, how to run, how to test, how to deploy
├── RUNBOOK.md              # operations: re-run, backfill, common failures, contacts
├── CHANGELOG.md
├── databricks.yml          # Asset Bundle (jobs, targets)
├── resources/              # job/pipeline definitions
├── conf/                   # per-env non-secret config
├── src/<package>/          # library code (pure functions + IO wrappers)
├── notebooks/              # thin entry points / exploration (not business logic)
├── sql/                    # DDL, grants, views (version-controlled!)
├── tests/unit/ tests/integration/
├── scripts/                # one-off utilities (data generator, migration helpers)
├── docs/                   # design docs, ERDs, ADRs (architecture decision records)
├── .github/workflows/ or azure-pipelines.yml   # CI/CD
├── pyproject.toml / requirements*.txt
├── .gitignore  .pre-commit-config.yaml
```

**Databricks Git folders:** clone the repo into the workspace, work on a branch in the UI or in your IDE (VS Code + the Databricks extension / Databricks Connect), and commit and push from either. Production jobs should run from **deployed bundles or a Git reference (branch/tag)**, never from someone's personal folder.

## 10. Collaboration habits
- Pull `main` daily; rebase your branch often to avoid big conflicts.
- Link commits/PRs to tickets.
- Use **draft PRs** to get early feedback.
- Use **pre-commit hooks** (`ruff`, `black`, `sqlfluff`, secret scanners like `gitleaks`).
- Write **ADRs** for important decisions ("ADR-007: Use DEEP CLONE for DBFS-root managed tables").

---

## How this connects to HMS→UC
- Migration code changes (names, paths) are **many small PRs**. Good branching and PR hygiene keeps them reviewable.
- Store **migration SQL, grants and validation scripts in Git**. They're your audit trail and your rollback plan.
- `git log` + tags show exactly what was deployed when, which matters when a post-migration incident happens.

## Hands-on
1. Fork this roadmap repo; clone it; create `notes/`; commit your Phase 1 diagram.
2. Create a feature branch, make 3 commits, push, and open a PR to your own `main` with the template above.
3. Create and resolve a merge conflict.
4. Commit a fake "secret" to a throwaway repo, then learn how you'd remove it from history (`git filter-repo`), and why rotation comes first.
5. Set up `pre-commit` with `ruff` and run it.
6. Connect a Databricks Git folder to your fork; commit from the workspace.

## After this phase you should be able to explain
- [ ] Working dir vs staging vs commit vs remote
- [ ] Your team's branching strategy, and why
- [ ] What a good PR looks like
- [ ] How to resolve a conflict safely
- [ ] What must never be committed, and what to do if it is
- [ ] How a DE repo is structured, and why notebooks should be thin

## Beginner vs experienced
| Beginner | Experienced |
|---|---|
| Commits and pushes | Shapes small, reviewable PRs with test evidence; reviews others' code |
| Panics at conflicts | Rebases routinely; resolves conflicts by understanding intent |
| Code in notebooks | Code in a package, with tests, CI and bundles; notebooks are entry points |

## Interview questions
1. Merge vs rebase?
2. Describe your branching strategy.
3. How do you resolve a merge conflict?
4. What makes a good pull request?
5. You accidentally committed a password. What do you do?
6. How would you structure a Databricks project repository?
7. `git revert` vs `git reset`?
