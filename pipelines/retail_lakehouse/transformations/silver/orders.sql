-- silver.orders - todos los pedidos de todos los canales, sin duplicados por order_id.
--
-- Con un formato transaccional (Iceberg/Delta) esto seria un streaming table con un
-- append_flow por canal. Con Parquet, la union se hace aca (ver README, "Limitaciones").

CREATE MATERIALIZED VIEW orders
COMMENT 'Orders from every sales channel.'
AS SELECT order_id, customer_id, amount, order_ts, channel
FROM (
  SELECT *, row_number() OVER (PARTITION BY order_id ORDER BY _ingested_at) AS rn
  FROM (
    SELECT order_id, customer_id, amount, order_ts, channel, _ingested_at FROM orders_web_raw
    UNION ALL
    SELECT order_id, customer_id, amount, order_ts, channel, _ingested_at FROM orders_store_raw
  )
)
WHERE rn = 1;
