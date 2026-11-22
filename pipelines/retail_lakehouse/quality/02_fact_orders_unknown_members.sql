-- check: ningun pedido quedo asignado al miembro desconocido (cliente o canal -1)
-- Un pedido en -1 indica un cliente que no llego por CDC o un canal fuera de dim_channel.
SELECT order_id, customer_sk, channel_key, order_ts
FROM retail.fact_orders
WHERE customer_sk = -1 OR channel_key = -1
