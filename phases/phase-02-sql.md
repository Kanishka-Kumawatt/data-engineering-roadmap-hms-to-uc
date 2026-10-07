# Phase 2 — SQL for Data Engineers

**Weeks:** 1–3 · **Time:** ~20 h (5 h theory, 15 h hands-on)
**Goal:** Write, read, debug and optimise the SQL used in real pipelines and migration validation.

> **Mentor note:** SQL is the tool you'll use most in this project. Validation queries, reconciliation, permission audits (`information_schema`), Gold models: all SQL. A Data Engineer who is strong in SQL is useful from day one. Practise every day, even for 20 minutes.

**Practice setup:** Databricks Free Edition (SQL editor) or local Spark SQL. Create the practice dataset below once and reuse it.

```sql
CREATE CATALOG IF NOT EXISTS learn;          -- Free Edition: or use the default catalog
CREATE SCHEMA  IF NOT EXISTS learn.retail;
USE learn.retail;

CREATE OR REPLACE TABLE customers (customer_id INT, name STRING, city STRING, country STRING, signup_date DATE, email STRING);
INSERT INTO customers VALUES
 (1,'Asha','Mumbai','IN','2024-01-10','asha@x.com'), (2,'Ben','London','UK','2024-02-01',NULL),
 (3,'Chen','Dubai','AE','2024-02-15','chen@x.com'), (4,'Dina','Mumbai','IN','2024-03-05','dina@x.com'),
 (5,'Eli',NULL,'UK','2024-03-20','eli@x.com'),     (5,'Eli',NULL,'UK','2024-03-20','eli@x.com');  -- duplicate on purpose

CREATE OR REPLACE TABLE products (product_id INT, product_name STRING, category STRING, unit_price DECIMAL(10,2));
INSERT INTO products VALUES (10,'Laptop','Electronics',1000.00),(11,'Mouse','Electronics',25.00),
 (12,'Desk','Furniture',300.00),(13,'Chair','Furniture',150.00),(14,'Pen','Stationery',2.50);

CREATE OR REPLACE TABLE orders (order_id INT, customer_id INT, order_ts TIMESTAMP, status STRING);
INSERT INTO orders VALUES
 (100,1,'2024-04-01 10:00:00','COMPLETED'),(101,1,'2024-04-15 12:30:00','COMPLETED'),
 (102,2,'2024-04-02 09:15:00','CANCELLED'),(103,3,'2024-04-03 18:45:00','COMPLETED'),
 (104,4,'2024-05-01 08:00:00','COMPLETED'),(105,9,'2024-05-02 11:00:00','COMPLETED'),   -- customer 9 doesn't exist
 (106,3,'2024-05-20 22:10:00',NULL);

CREATE OR REPLACE TABLE order_items (order_id INT, product_id INT, quantity INT, unit_price DECIMAL(10,2));
INSERT INTO order_items VALUES (100,10,1,1000.00),(100,11,2,25.00),(101,14,10,2.50),(102,12,1,300.00),
 (103,13,4,150.00),(104,10,1,950.00),(104,11,1,25.00),(105,12,1,300.00),(106,11,3,25.00);
```

The data is deliberately messy: there's a duplicate customer, an orphan order, a NULL status and a NULL city. Real data looks like this.

---

## Level 1 — Core querying (week 1)

| Concept | What to know | Common trap |
|---|---|---|
| `SELECT`, `WHERE` | Filtering rows | `WHERE city = NULL` never matches. Use `IS NULL` |
| `ORDER BY`, `LIMIT` | Sorting | Without `ORDER BY`, row order is **not guaranteed** |
| `GROUP BY` | One row per group | Every non-aggregated SELECT column must be in GROUP BY |
| `HAVING` | Filter *after* grouping | `WHERE` filters rows; `HAVING` filters groups |
| `DISTINCT` | Remove duplicate rows | Often hides a bad join. Ask *why* there are duplicates |
| Aggregates | `COUNT(*)`, `COUNT(col)`, `SUM`, `AVG`, `MIN`, `MAX` | `COUNT(col)` skips NULLs; `COUNT(*)` doesn't |

```sql
-- Revenue per category, only categories over 500
SELECT p.category, SUM(oi.quantity * oi.unit_price) AS revenue
FROM order_items oi JOIN products p ON oi.product_id = p.product_id
GROUP BY p.category
HAVING SUM(oi.quantity * oi.unit_price) > 500
ORDER BY revenue DESC;
```

**Logical order of execution.** Learn this; it explains most SQL confusion:
`FROM/JOIN → WHERE → GROUP BY → HAVING → SELECT → DISTINCT → ORDER BY → LIMIT`
(That's why you can't use a SELECT alias in WHERE.)

## Level 2 — Joins (week 1–2)

| Join | Returns | DE use |
|---|---|---|
| `INNER` | Matches only | Enrichment where a match is mandatory |
| `LEFT` | All left rows + matches | Enrichment where the match is optional |
| `FULL OUTER` | Everything from both | **Reconciliation** (source vs target) |
| `LEFT ANTI` (Spark) / `NOT EXISTS` | Left rows with **no** match | **Find missing records / orphans** |
| `LEFT SEMI` / `EXISTS` | Left rows that have a match (no duplication) | Filtering |
| `CROSS` | Every combination | Date spines; dangerous by accident |

```sql
-- Orphan orders (customer doesn't exist) — a classic data quality check
SELECT o.* FROM orders o LEFT ANTI JOIN customers c ON o.customer_id = c.customer_id;

-- Join explosion demo: customer 5 is duplicated, so any join to customers doubles rows
SELECT COUNT(*) FROM customers c JOIN orders o ON c.customer_id = o.customer_id;
```

> **Golden rule:** Before you join, know the **grain** (what one row represents) and the key **uniqueness** of both sides. Check it with `SELECT key, COUNT(*) FROM t GROUP BY key HAVING COUNT(*) > 1`.

## Level 3 — Subqueries, CTEs, CASE, NULLs, dates (week 2)

```sql
WITH order_totals AS (                         -- CTE: name each step, so it reads top to bottom
  SELECT order_id, SUM(quantity * unit_price) AS order_total
  FROM order_items GROUP BY order_id
),
enriched AS (
  SELECT o.order_id, o.customer_id, CAST(o.order_ts AS DATE) AS order_date,
         COALESCE(o.status, 'UNKNOWN') AS status,                 -- NULL handling
         t.order_total,
         CASE WHEN t.order_total >= 1000 THEN 'LARGE'
              WHEN t.order_total >= 100  THEN 'MEDIUM'
              ELSE 'SMALL' END AS order_size                       -- CASE
  FROM orders o JOIN order_totals t USING (order_id)
)
SELECT date_trunc('MONTH', order_date) AS month, order_size, COUNT(*) AS n, SUM(order_total) AS revenue
FROM enriched WHERE status = 'COMPLETED'
GROUP BY ALL ORDER BY month, order_size;
```

**NULL handling to know:** `COALESCE`, `NULLIF(a, 0)` (avoids divide-by-zero), `IS [NOT] DISTINCT FROM` (NULL-safe equality, or `<=>` in Spark), `NULL` in `NOT IN` (returns no rows! Prefer `NOT EXISTS`/anti join).

**Date/time to know:** `current_date()`, `date_trunc`, `date_add`, `datediff`, `months_between`, `to_date(str, fmt)`, `to_timestamp`, `date_format`, time zones (`from_utc_timestamp`). Store timestamps in **UTC**.

## Level 4 — Window functions (week 2–3), the most important DE skill in SQL

Window functions compute across related rows **without collapsing them**.

```sql
-- 1. Deduplication: keep the latest row per key (you'll write this hundreds of times)
SELECT * FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY signup_date DESC) AS rn
  FROM customers
) WHERE rn = 1;
-- Databricks shortcut:  SELECT * FROM customers QUALIFY ROW_NUMBER() OVER (...) = 1;

-- 2. Running total & previous order per customer
SELECT o.customer_id, o.order_id, o.order_ts, t.order_total,
       SUM(t.order_total) OVER (PARTITION BY o.customer_id ORDER BY o.order_ts
                                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running_total,
       LAG(o.order_ts) OVER (PARTITION BY o.customer_id ORDER BY o.order_ts)      AS prev_order_ts
FROM orders o JOIN (SELECT order_id, SUM(quantity*unit_price) order_total FROM order_items GROUP BY 1) t
  USING (order_id);
```

Know: `ROW_NUMBER` vs `RANK` vs `DENSE_RANK`, `LAG`/`LEAD`, `FIRST_VALUE`/`LAST_VALUE`, frame clauses (`ROWS` vs `RANGE`), `NTILE`.

## Level 5 — Reading, debugging and optimising (week 3)

**How to debug a complex SQL query someone hands you:**

1. Find the **final grain**: what does one output row represent?
2. Break CTEs apart and run each one alone, with `COUNT(*)` and a sample.
3. After each join, check that the row count did what you expected (same? fewer? **more = fan-out**).
4. Check filters on the **right side of a LEFT JOIN** in `WHERE`, which silently turns it into an INNER JOIN.
5. Check NULLs in join keys (NULL never equals NULL).
6. Check data types (joining STRING `'001'` to INT `1`).

**Optimisation basics (more in Phase 13):**
- Filter early, and select only the columns you need (columnar formats reward this).
- Filter on partition/cluster columns so files get skipped.
- Avoid `SELECT DISTINCT` as a "fix" for duplicates.
- Avoid functions on filter columns where possible (`WHERE to_date(ts) = ...` vs a range on `ts`).
- Use `EXPLAIN` / the query profile to see scans, joins and shuffles.

**Production-quality SQL:**
- CTEs with meaningful names; one logical step per CTE
- Explicit column lists (no `SELECT *` in Gold/production models)
- **Fully qualified 3-level names** (`catalog.schema.table`), or a parameterised catalog
- Comments that explain *why*, not *what*
- Idempotent DDL (`CREATE OR REPLACE`, `IF NOT EXISTS`, MERGE instead of INSERT)
- Consistent formatting (try `sqlfluff`)

---

## How this connects to HMS→UC

Migration validation **is** SQL. You'll write queries like these:

```sql
-- Row-count reconciliation
SELECT 'hms' src, COUNT(*) FROM hive_metastore.sales.orders
UNION ALL SELECT 'uc', COUNT(*) FROM sales_prod.sales.orders;

-- Content reconciliation: rows in source but not target (and vice versa)
SELECT * FROM hive_metastore.sales.orders EXCEPT SELECT * FROM sales_prod.sales.orders;

-- Aggregate fingerprint (cheap, catches most issues)
SELECT COUNT(*), COUNT(DISTINCT order_id), SUM(amount), MIN(order_ts), MAX(order_ts)
FROM sales_prod.sales.orders;

-- Inventory: what's in a schema, by type (UC)
SELECT table_name, table_type, data_source_format
FROM sales_prod.information_schema.tables WHERE table_schema = 'sales';
```

## Build — mini-projects

1. **Data-quality report query:** one SQL script that outputs, for the practice dataset: duplicate customers, orphan orders, NULL statuses, orders with no items, and negative or zero quantities. Each check is one row: `check_name, failed_rows`.
2. **Monthly customer metrics (a Gold-style model):** per customer per month: orders, revenue, running lifetime revenue, rank within country, days since previous order.
3. **Reconciliation query:** copy `orders` to `orders_copy`, then change 2 rows, delete 1 and add 1. Write a `FULL OUTER JOIN` query that classifies each row as `MATCH`, `MISMATCH`, `MISSING_IN_TARGET` or `EXTRA_IN_TARGET`.

## Troubleshooting drills

| Symptom | Probably |
|---|---|
| Row count grew after a join | Duplicate keys on one side (fan-out) |
| LEFT JOIN behaves like INNER | Filter on the right table in `WHERE` instead of `ON` |
| `NOT IN` returns nothing | NULL in the subquery |
| Revenue slightly off | DECIMAL vs DOUBLE rounding, or currency/units |
| `[UNRESOLVED_COLUMN]` | Typo, wrong alias, or the column was dropped by the GROUP BY |
| `[TABLE_OR_VIEW_NOT_FOUND]` | Wrong catalog/schema; in UC, check `SELECT current_catalog(), current_schema()` |

## After this phase you should be able to explain

- [ ] The logical execution order of a SELECT
- [ ] Every join type, and when you'd use anti joins
- [ ] How to deduplicate with `ROW_NUMBER()`
- [ ] Why `COUNT(col)` ≠ `COUNT(*)`, and why `NOT IN` + NULL is dangerous
- [ ] How you would prove two tables contain the same data

## Beginner vs experienced

| Beginner | Experienced |
|---|---|
| Writes correct queries on clean data | Checks grain and uniqueness *before* joining; anticipates NULLs, duplicates and type mismatches |
| Uses DISTINCT to remove duplicates | Finds the cause of duplicates |
| Writes one big query | Writes modular CTEs that reviewers can follow; reads query plans |

Exercises: [exercises/sql-exercises.md](../exercises/sql-exercises.md)

## Interview questions

1. Difference between `WHERE` and `HAVING`?
2. `ROW_NUMBER` vs `RANK` vs `DENSE_RANK`?
3. How do you find duplicates? How do you remove them while keeping the latest?
4. How would you find records in table A that aren't in table B?
5. A LEFT JOIN returns fewer rows than the left table. Why?
6. How do you compare two large tables to prove they're identical?
7. Write a query for the second-highest salary per department.
