-- Views recreated in Unity Catalog with fully qualified 3-level names.
-- ${catalog} is replaced by the target catalog at run time (notebooks/11_migration_execute.py).
-- Order matters: a view must come after every table/view it reads from (see planner.creation_order).

CREATE OR REPLACE VIEW ${catalog}.legacy.v_store_summary
COMMENT 'Migrated from legacy retail.v_store_summary. Grain: one row per region'
AS SELECT region, COUNT(*) AS stores
FROM ${catalog}.legacy.stores
GROUP BY region;
