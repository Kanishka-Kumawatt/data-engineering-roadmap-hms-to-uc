-- LEGACY (HMS-era) SQL: 2-level names resolve against whatever the current catalog is after migration.
-- Convert to 3-level names (ideally with a parameterised catalog).
CREATE OR REPLACE VIEW retail.v_region_revenue AS
SELECT s.region, SUM(h.amount) AS revenue
FROM retail.daily_store_sales h
JOIN retail.stores s ON h.store_id = s.store_id
GROUP BY s.region;

SELECT * FROM parquet.`dbfs:/FileStore/exports/region_targets/`;
