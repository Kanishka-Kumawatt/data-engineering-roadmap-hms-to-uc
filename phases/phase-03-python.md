# Phase 3 — Python for Data Engineers

**Weeks:** 2–4 · **Time:** ~18 h (4 h theory, 14 h hands-on)
**Goal:** Write Python that automates work, is reusable, handles failure gracefully, and that someone else can maintain.

> **Mentor note:** You don't need to be a software engineer, but you do need to write Python that doesn't embarrass you in code review. Skip decorators, metaclasses and async for now. Focus on functions, data structures, error handling, logging, files, config, and packaging code into modules. On a migration project, Python is how you automate things: "loop over 400 tables and generate SYNC statements" is a Python job.

---

## 1. What to learn (and only this)

| Topic | Why a DE needs it | Must-know |
|---|---|---|
| Types & data structures | Holding table lists, configs, mappings | `list`, `dict`, `set` (dedupe, membership), `tuple` (immutable keys) |
| Loops & comprehensions | Iterating tables/files | `for`, `enumerate`, `zip`, list/dict comprehensions |
| Functions | Reusable, testable logic | args, defaults, `*args/**kwargs`, return values, type hints, docstrings |
| Exceptions | Pipelines must fail **clearly** or recover | `try/except/else/finally`, raising custom exceptions, **never bare `except:`** |
| Files | Configs, manifests, reports | `pathlib`, `with open()`, `json`, `csv` |
| Modules & packages | Sharing code across notebooks/jobs | `import`, `__init__.py`, `src/` layout, `pip install -e .` |
| Logging | Production debugging | `logging` module, levels, formats, **no `print` in prod code** |
| APIs | Ingesting from REST sources | `requests`, auth headers, pagination, retries, timeouts |
| Configuration | Same code across dev/test/prod | YAML/JSON configs, env vars, Databricks widgets/job params, secrets |
| Basic OOP | Grouping related state + behaviour | classes, `__init__`, `dataclasses` (configs) |
| Testing | Proving it works | `pytest`, fixtures, `assert` |

## 2. Concepts explained the DE way

### Data structures in a migration context
```python
tables = ["orders", "customers", "orders", "products"]          # list: ordered, may contain duplicates
unique_tables = set(tables)                                       # set: dedupe, fast membership tests
table_types = {"orders": "EXTERNAL", "customers": "MANAGED"}      # dict: lookups by key
full_name = ("hive_metastore", "sales", "orders")                 # tuple: fixed, hashable

# Comprehension: generate SYNC statements for external tables only
stmts = [f"SYNC TABLE sales_dev.sales.{t} FROM hive_metastore.sales.{t} DRY RUN"
         for t, typ in table_types.items() if typ == "EXTERNAL"]
```

### Functions: small, named, testable, typed
```python
def build_target_name(source_fqn: str, catalog_map: dict[str, str]) -> str:
    """Map an HMS 2-level name 'schema.table' to a UC 3-level name using a schema->catalog map."""
    schema, table = source_fqn.split(".")
    if schema not in catalog_map:
        raise KeyError(f"No target catalog configured for schema '{schema}'")
    return f"{catalog_map[schema]}.{schema}.{table}"
```
Pure functions like this (no Spark, no I/O) are **easy to unit test**. Push as much logic into them as you can.

### Exceptions: fail clearly, recover only when you know how
```python
import logging
log = logging.getLogger(__name__)

class MigrationError(Exception):
    """Raised when a table cannot be migrated."""

def migrate_table(spark, src: str, tgt: str) -> dict:
    try:
        spark.sql(f"CREATE TABLE IF NOT EXISTS {tgt} DEEP CLONE {src}")
    except Exception as e:                       # catch, add context, re-raise or record
        log.error("Clone failed %s -> %s: %s", src, tgt, e)
        return {"table": src, "status": "FAILED", "error": str(e)[:500]}
    else:
        return {"table": src, "status": "OK", "error": None}
```
Ask yourself: **should this error stop the whole pipeline, or be recorded so we can continue?** In a batch migration of 400 tables, you record and continue, then report. In a pipeline writing Gold data, you usually stop.

### Logging, not print
```python
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
log = logging.getLogger("migration")
log.info("Starting schema %s (%d tables)", "sales", 42)
log.warning("Table %s has no _delta_log; treating as Parquet", "sales.legacy")
```

### Configuration: never hard-code environment
```yaml
# conf/dev.yaml
env: dev
source_catalog: hive_metastore
target_catalog: sales_dev
schemas: [sales, finance]
```
```python
import yaml, os
from dataclasses import dataclass

@dataclass(frozen=True)
class Config:
    env: str
    source_catalog: str
    target_catalog: str
    schemas: list[str]

def load_config(env: str | None = None) -> Config:
    env = env or os.environ.get("APP_ENV", "dev")
    with open(f"conf/{env}.yaml") as f:
        return Config(**yaml.safe_load(f))
```
On Databricks, `env` comes from a **job parameter / widget**, and passwords come from **secrets** (`dbutils.secrets.get(scope, key)`), never from code or YAML.

### APIs: timeouts, retries, pagination
```python
import requests, time

def fetch_all(url: str, token: str, max_retries: int = 3) -> list[dict]:
    results, page = [], 1
    while True:
        for attempt in range(1, max_retries + 1):
            try:
                r = requests.get(url, params={"page": page}, headers={"Authorization": f"Bearer {token}"}, timeout=30)
                r.raise_for_status()
                break
            except requests.RequestException as e:
                if attempt == max_retries:
                    raise
                time.sleep(2 ** attempt)                 # exponential backoff
        data = r.json()
        results.extend(data["items"])
        if not data.get("next_page"):
            return results
        page += 1
```

## 3. How it connects to HMS→UC

Typical Python tasks on a migration:
- Generate migration SQL (SYNC/CTAS/CLONE/GRANT) from an inventory.
- Loop over tables, run validation queries, and write the results to a report table.
- Parse `SHOW GRANTS` output and translate HMS grants to UC grants.
- Scan the notebooks/repos for 2-level table names, `/mnt/` paths and `dbfs:/` paths that need changing.
- Call the Databricks REST API / SDK (`databricks-sdk`) to list jobs, clusters and groups.

## 4. Practice (in order)

1. Exercises on lists/dicts/sets: dedupe a table list, invert a dict, group tables by schema.
2. Read a CSV inventory of tables (`schema,table,type,location,format`) and produce counts by type and format.
3. Write `build_target_name()` and 5 `pytest` tests for it, including the error case.
4. Write a `logging`-based script that reads a JSON config and prints what it *would* do (dry-run pattern).
5. Call a public API (e.g. `https://jsonplaceholder.typicode.com/posts`), handle errors, and save the results to JSON.

## 5. Build — mini-projects

### Project A: Migration Statement Generator (directly useful at work)
```
migration_gen/
├── conf/dev.yaml
├── inventory.csv            # schema,table,table_type,format,location
├── src/migration_gen/
│   ├── __init__.py
│   ├── naming.py            # build_target_name
│   ├── planner.py           # choose strategy per table -> SYNC / DEEP CLONE / CTAS / MANUAL
│   └── cli.py               # python -m migration_gen.cli --env dev --dry-run
└── tests/test_planner.py
```
Rules for the planner (simplified; refine them in Phase 7):
- External + Delta → `SYNC`
- Managed + Delta (on DBFS root) → `DEEP CLONE` into a UC managed table
- Managed or external + Parquet/CSV → `CTAS` (or convert)
- View → `MANUAL` (needs SQL rewritten to 3-level names)

Output: a `.sql` file + a `plan.csv`. **No Spark needed.** That's what makes it testable.

### Project B: Code scanner
Walk a folder of `.py`/`.sql` files and report every line that has a `/mnt/` path, a `dbfs:/` path, a 2-level table reference after `FROM`/`JOIN`, `spark.sparkContext`, or `input_file_name()`. These are the real things that break after UC migration (see Phase 7).

## 6. Errors you should learn to troubleshoot

| Error | Meaning / fix |
|---|---|
| `ModuleNotFoundError` | Not installed in this env, wrong venv, or `src/` not on the path → `pip install -e .` |
| `KeyError` | Missing dict key → use `.get()` with a default, or validate config upfront |
| `TypeError: unsupported operand` | Mixing str/int/None → check types and use type hints |
| `FileNotFoundError` | Relative path from the wrong working dir → use `pathlib.Path(__file__).parent` |
| `JSONDecodeError` | API returned HTML/error → check the status code before `.json()` |
| `requests.exceptions.Timeout` | Add `timeout=` and retries |
| Mutable default arg bug | `def f(x=[])` shares the list across calls → use `None` |

## 7. After this phase you should be able to explain

- [ ] When to use list vs set vs dict
- [ ] Why we put logic in pure functions and how to test them
- [ ] When to catch an exception vs let it fail
- [ ] Why `logging` beats `print` in production
- [ ] How config differs from secrets, and where each lives
- [ ] How you'd structure a small Python package with tests

## Beginner vs experienced

| Beginner | Experienced |
|---|---|
| Script runs top to bottom in a notebook | Code is in modules with functions, typed, tested and imported by notebooks/jobs |
| Hard-coded paths and names | Config-driven, environment-aware, secrets via a secret manager |
| `try/except: pass` | Specific exceptions, context-rich errors, and a clear decision to fail or record |

Exercises: [exercises/pyspark-exercises.md](../exercises/pyspark-exercises.md) (the Python warm-up section)

## Interview questions

1. Difference between a list and a tuple? When would you use a set?
2. How do you handle exceptions in a data pipeline? Fail fast or continue?
3. How do you manage configuration for dev/test/prod?
4. How would you call a paginated API reliably?
5. What's the problem with `def f(items=[])`?
6. How do you make Python code reusable across Databricks notebooks?
