-- check: cada date_key de los hechos existe en dim_date
SELECT f.order_id, f.date_key
FROM retail.fact_orders f
LEFT ANTI JOIN retail.dim_date d ON d.date_key = f.date_key
