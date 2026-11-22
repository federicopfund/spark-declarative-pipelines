-- check: fact_customer_changes tiene un cambio por cada version posterior a la primera (silver)
SELECT s.changes AS silver_changes, f.changes AS fact_changes
FROM (SELECT count(*) - count(DISTINCT customer_id) AS changes FROM retail.customers_history) s
CROSS JOIN (SELECT count(*) AS changes FROM retail.fact_customer_changes) f
WHERE s.changes <> f.changes
