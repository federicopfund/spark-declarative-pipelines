-- check: agg_sales_by_customer suma los mismos pedidos e importe total que fact_orders
-- Devuelve una fila si no cierran (cantidad de pedidos o importe).
SELECT f.orders AS fact_orders, a.orders AS agg_orders, f.amount AS fact_amount, a.amount AS agg_amount
FROM (SELECT count(*) AS orders, sum(amount) AS amount FROM retail.fact_orders) f
CROSS JOIN (SELECT coalesce(sum(orders), 0) AS orders, sum(total_amount) AS amount FROM retail.agg_sales_by_customer) a
WHERE f.orders <> a.orders OR NOT (f.amount <=> a.amount)
