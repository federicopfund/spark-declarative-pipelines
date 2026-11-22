-- check: agg_sales_by_customer tiene una fila por customer_id (sin repetidos) y ninguno de los clientes con pedidos falta ni sobra
-- Devuelve los customer_id repetidos (problem = 'repetido'), faltantes ('falta') o sobrantes ('sobra').
WITH expected AS (
  SELECT DISTINCT c.customer_id
  FROM retail.fact_orders f
  JOIN retail.dim_customer c ON c.customer_sk = f.customer_sk
),
actual AS (
  SELECT customer_id, count(*) AS n FROM retail.agg_sales_by_customer GROUP BY customer_id
)
SELECT coalesce(e.customer_id, a.customer_id) AS customer_id,
       CASE WHEN a.customer_id IS NULL THEN 'falta'
            WHEN e.customer_id IS NULL THEN 'sobra'
            ELSE 'repetido' END AS problem,
       a.n AS rows_in_agg
FROM expected e
FULL OUTER JOIN actual a ON a.customer_id = e.customer_id
WHERE a.customer_id IS NULL OR e.customer_id IS NULL OR a.n > 1
