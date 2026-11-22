-- check: agg_sales_by_customer tiene name y country no vacios, country = pais de la version vigente (o 'N/A' sin vigente), orders > 0 y primera fecha <= ultima
-- Devuelve las filas que violan alguna regla.
SELECT a.customer_id, a.name, a.country, d.country AS expected_country, a.orders, a.first_order_date, a.last_order_date
FROM retail.agg_sales_by_customer a
LEFT JOIN (
  SELECT customer_id, max(country) AS country   -- a lo sumo una vigente (control 05)
  FROM retail.dim_customer
  WHERE is_current
  GROUP BY customer_id
) d ON d.customer_id = a.customer_id
WHERE a.name IS NULL OR trim(a.name) = ''
   OR a.country IS NULL OR trim(a.country) = ''
   OR a.country IS DISTINCT FROM coalesce(d.country, 'N/A')
   OR a.orders IS NULL OR a.orders <= 0
   OR a.first_order_date IS NULL OR a.last_order_date IS NULL
   OR a.first_order_date > a.last_order_date
