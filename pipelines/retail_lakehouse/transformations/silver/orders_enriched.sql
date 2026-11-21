-- silver.orders_enriched - vista temporal: pedidos + datos actuales del cliente.
-- Existe solo durante la ejecucion del pipeline: la usan los datasets gold, pero no se publica.

CREATE TEMPORARY VIEW orders_enriched AS
SELECT
  o.order_id,
  o.customer_id,
  c.name                     AS customer_name,
  coalesce(c.country, 'N/A') AS country,
  o.channel,
  o.amount,
  o.order_ts,
  CAST(o.order_ts AS DATE)   AS order_date
FROM orders o
LEFT JOIN customers c
  ON o.customer_id = c.customer_id;
