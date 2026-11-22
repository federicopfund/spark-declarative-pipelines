-- check: agg_sales_by_customer: average_order = round(total_amount / orders, 2) y primera/ultima fecha = min/max de to_date(order_ts) en fact_orders por customer_id
-- Devuelve los customer_id cuyas metricas no coinciden con el recalculo desde fact_orders.
WITH recomputed AS (
  SELECT c.customer_id,
         count(*)                 AS orders,
         sum(f.amount)            AS total_amount,
         min(to_date(f.order_ts)) AS first_order_date,
         max(to_date(f.order_ts)) AS last_order_date
  FROM retail.fact_orders f
  JOIN retail.dim_customer c ON c.customer_sk = f.customer_sk
  GROUP BY c.customer_id
)
SELECT a.customer_id,
       a.orders, r.orders AS expected_orders,
       a.total_amount, r.total_amount AS expected_total,
       a.average_order, round(a.total_amount / a.orders, 2) AS expected_average,
       a.first_order_date, r.first_order_date AS expected_first,
       a.last_order_date, r.last_order_date AS expected_last
FROM retail.agg_sales_by_customer a
JOIN recomputed r ON r.customer_id = a.customer_id
WHERE a.orders <> r.orders
   OR a.total_amount <> r.total_amount
   OR a.average_order IS DISTINCT FROM round(a.total_amount / a.orders, 2)
   OR a.first_order_date IS DISTINCT FROM r.first_order_date
   OR a.last_order_date IS DISTINCT FROM r.last_order_date
