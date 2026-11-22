-- gold.agg_sales_by_customer - resumen de compras por cliente (estado actual).
--
-- Grano: un cliente (customer_id) con al menos un pedido. Se calcula desde fact_orders (unica fuente de
-- verdad de los importes): cada pedido llega a customer_id por su customer_sk (la version vigente al comprar),
-- asi un cliente con varias versiones no se parte.
-- name y country salen de dim_customer: country es el pais de la version VIGENTE (para el pais al comprar,
-- usar fact_orders + dim_customer por customer_sk); name es el de la ultima version.
-- Cliente sin version vigente (dado de baja): name = ultima version conocida y country = 'N/A'.
-- Pedidos sin version vigente al comprar (customer_sk = -1) suman en la fila customer_id = -1.

CREATE MATERIALIZED VIEW agg_sales_by_customer
COMMENT 'Purchase summary per customer. Grain: one customer (customer_id) with at least one order. Derived from fact_orders. country is the current country (N/A when the customer has no current version, in which case name is the one from the latest version). Orders placed without a current customer version at purchase time are summed in the row customer_id = -1.'
AS
WITH customer_latest AS (
  SELECT
    customer_id,
    max_by(name, version)     AS name,
    max_by(country, version)  AS last_country,
    bool_or(is_current)       AS has_current
  FROM dim_customer
  GROUP BY customer_id
)
SELECT
  c.customer_id                                                AS customer_id,
  cl.name                                                      AS name,
  CASE WHEN cl.has_current THEN cl.last_country ELSE 'N/A' END AS country,
  count(*)                                                     AS orders,
  sum(f.amount)                                                AS total_amount,
  round(avg(f.amount), 2)                                      AS average_order,
  min(to_date(f.order_ts))                                     AS first_order_date,
  max(to_date(f.order_ts))                                     AS last_order_date,
  current_timestamp()                                          AS _loaded_at
FROM fact_orders f
JOIN dim_customer c
  ON c.customer_sk = f.customer_sk
JOIN customer_latest cl
  ON cl.customer_id = c.customer_id
GROUP BY c.customer_id, cl.name, cl.has_current, cl.last_country;
