# SQL Exercises (40)

Use the practice dataset from [Phase 2](../phases/phase-02-sql.md) (`customers`, `products`, `orders`, `order_items`). It's deliberately messy. For each exercise: **write it, run it, check the row count makes sense, then explain it in one sentence.** Commit your solutions to `solutions/sql/`.

Difficulty: 🟢 basic · 🟡 intermediate · 🔴 production-level

## Level 1 — Querying (Week 1)
1. 🟢 List all customers from India, sorted by signup date.
2. 🟢 Count customers per country. Then count *distinct* customers per country. Why do the numbers differ?
3. 🟢 Find customers with no city. (Did `= NULL` work? Why not?)
4. 🟢 Total quantity sold per product.
5. 🟢 Categories with more than 2 products (`HAVING`).
6. 🟢 Orders placed in May 2024 (use a range on `order_ts`, not a function on the column).
7. 🟢 `COUNT(*)` vs `COUNT(status)` on `orders`. Explain the difference.
8. 🟢 Top 3 most expensive products.
9. 🟢 Average unit price per category, rounded to 2 decimals.
10. 🟢 Orders per status, with NULL shown as `'UNKNOWN'`.

## Level 2 — Joins (Week 2)
11. 🟢 Order lines with product name and category (INNER JOIN).
12. 🟢 All customers and their order count, including customers with 0 orders.
13. 🟡 Orphan orders: orders whose customer doesn't exist (two ways: `LEFT JOIN ... IS NULL` and `LEFT ANTI JOIN`).
14. 🟡 Products never ordered.
15. 🟡 Show that joining `orders` to `customers` produces extra rows because of the duplicate customer. Then fix it **without** `DISTINCT`.
16. 🟡 Revenue per customer name. Handle the orphan order: where should its revenue appear?
17. 🟡 Put a filter on the right table of a LEFT JOIN, once in `WHERE` and once in `ON`. Explain the different results.
18. 🟡 `NOT IN` with a subquery that contains NULL. Demonstrate the empty result, then fix it with `NOT EXISTS`.
19. 🟡 Customers who ordered both Electronics **and** Furniture.
20. 🟡 Full outer join of `customers` and `orders` on `customer_id`, labelling each row `BOTH`, `CUSTOMER_ONLY` or `ORDER_ONLY`.

## Level 3 — CTEs, CASE, dates (Week 2)
21. 🟡 Using CTEs: order totals → enriched orders → monthly revenue by status.
22. 🟡 Classify orders into `SMALL/MEDIUM/LARGE` by total, and count each per month.
23. 🟡 Days between signup and first order per customer.
24. 🟡 Revenue by day of week.
25. 🟡 Convert `order_ts` (UTC) to Dubai time and recompute the daily revenue. Which orders moved to a different day?

## Level 4 — Window functions (Week 3)
26. 🟡 Deduplicate `customers`, keeping one row per `customer_id` (ROW_NUMBER, then QUALIFY).
27. 🟡 Each customer's orders numbered in time order.
28. 🟡 Running total of revenue per customer.
29. 🟡 Days since the previous order per customer (LAG).
30. 🟡 Rank products by revenue within each category (RANK vs DENSE_RANK: show the difference with a tie).
31. 🟡 Each order's share of its customer's total revenue (%).
32. 🔴 7-day moving average of daily revenue (use a date spine so missing days count as 0).
33. 🔴 The second-largest order per customer (customers with one order are excluded).
34. 🔴 "Sessionise" orders: a new session starts if the gap since the previous order is > 10 days. Assign session numbers.

## Level 5 — Debugging, reconciliation and production SQL (Week 3+)
35. 🔴 **DQ report**: one query returning `(check_name, failed_rows)` for duplicates, orphans, NULL status, orders with no items, and non-positive quantities.
36. 🔴 **Reconciliation**: copy `orders` to `orders_copy`, modify 2 rows, delete 1, insert 1. One query classifies every key as `MATCH / MISMATCH / MISSING_IN_TARGET / EXTRA_IN_TARGET`.
37. 🔴 **Aggregate fingerprint** query for a table (rows, distinct keys, sums, min/max dates). Run it on the source and the copy.
38. 🔴 **Hash-by-partition comparison**: compare `orders` and `orders_copy` by `order_date` using `xxhash64`, and output only the dates that differ.
39. 🔴 **Debug this query** (it returns inflated revenue). Find and fix two bugs:
    ```sql
    SELECT c.country, SUM(oi.quantity * oi.unit_price) revenue
    FROM customers c
    LEFT JOIN orders o ON c.customer_id = o.customer_id
    LEFT JOIN order_items oi ON o.order_id = oi.order_id
    WHERE o.status = 'COMPLETED'
    GROUP BY c.country;
    ```
    *(Hints: duplicate customer; a WHERE filter on a LEFT-joined table.)*
40. 🔴 **UC metadata queries** (Free Edition or dev):
    a) all tables in a catalog, by type and format (`information_schema.tables`);
    b) all columns named like `%email%` (PII discovery);
    c) all grants on a schema (`information_schema.schema_privileges` / `SHOW GRANTS`);
    d) tables not modified in 90 days (`information_schema.tables.last_altered`).

## Bonus — migration-flavoured SQL
- B1. Generate `SYNC TABLE` statements from `information_schema.tables` with string concatenation.
- B2. Find views whose definition contains a 2-level name (`information_schema.views.view_definition` + `regexp`).
- B3. Compare column lists between `hive_metastore.x.t` and `cat.x.t` (`DESCRIBE` into temp views, then a full outer join).
- B4. From `system.access.table_lineage`, list the top 10 most-read tables in the last 30 days.
