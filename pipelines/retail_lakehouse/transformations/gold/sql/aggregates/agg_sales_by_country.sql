-- gold.agg_sales_by_country - ventas por pais ACTUAL del cliente.
--
-- Grano: un pais. Se calcula desde fact_orders (unica fuente de verdad de los importes).
-- Cada pedido se asigna al pais de la version VIGENTE del cliente, no al que tenia al comprar: para el
-- pais en el momento de la venta, usar fact_orders + dim_customer por customer_sk.
-- Clientes dados de baja (sin version vigente) quedan en 'N/A'.

CREATE MATERIALIZED VIEW agg_sales_by_country
COMMENT 'Sales per current customer country. Grain: one country. Derived from fact_orders.'
AS SELECT
  coalesce(cur.country, 'N/A')         AS country,
  count(*)                             AS orders,
  count(DISTINCT c.customer_id)        AS customers,
  sum(f.amount)                        AS total_amount,
  round(avg(f.amount), 2)              AS average_order
FROM fact_orders f
JOIN dim_customer c
  ON c.customer_sk = f.customer_sk
LEFT JOIN dim_customer cur
  ON  cur.customer_id = c.customer_id
  AND cur.is_current
GROUP BY coalesce(cur.country, 'N/A');
