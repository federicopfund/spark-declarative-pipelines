-- gold.fact_orders - hechos de pedidos.
--
-- Grano: un pedido. Dimensiones: dim_date (date_key), dim_customer (customer_sk), dim_channel (channel_key).
-- order_id queda como dimension degenerada (identificador sin dimension propia).
--
-- Cada pedido se une a la VERSION del cliente vigente en el momento del pedido
-- (order_ts en [valid_from, valid_to)), no a la version actual: asi las ventas por pais reflejan donde
-- estaba el cliente cuando compro. Si no hay version vigente (cliente que todavia no llego por CDC, o un
-- pedido durante el lapso de una baja) el pedido va al miembro desconocido (-1) y no se pierde.

CREATE MATERIALIZED VIEW fact_orders
COMMENT 'Orders. Grain: one order. Customer joined as of order_ts (point in time).'
AS SELECT
  o.order_id,
  CAST(date_format(o.order_ts, 'yyyyMMdd') AS INT) AS date_key,
  coalesce(c.customer_sk, -1)                      AS customer_sk,
  coalesce(ch.channel_key, -1)                     AS channel_key,
  o.amount,
  o.order_ts,
  current_timestamp()                              AS _loaded_at
FROM orders o
LEFT JOIN dim_customer c
  ON  c.customer_id = o.customer_id
  AND o.order_ts >= c.valid_from
  AND o.order_ts <  c.valid_to
LEFT JOIN dim_channel ch
  ON ch.channel_code = o.channel;
