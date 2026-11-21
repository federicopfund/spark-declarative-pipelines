-- gold.sales_by_country - ventas por pais (segun el pais ACTUAL del cliente).

CREATE MATERIALIZED VIEW sales_by_country
COMMENT 'Sales per customer country.'
AS SELECT
  country,
  count(*)                AS orders,
  count(DISTINCT customer_id) AS customers,
  sum(amount)             AS total_amount,
  round(avg(amount), 2)   AS average_order
FROM orders_enriched
GROUP BY country;
