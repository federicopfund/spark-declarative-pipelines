-- check: fact_orders tiene los mismos pedidos e importe total que silver.orders
-- Devuelve una fila si no cierran (cantidad o importe).
SELECT s.orders AS silver_orders, f.orders AS fact_orders, s.amount AS silver_amount, f.amount AS fact_amount
FROM (SELECT count(*) AS orders, sum(amount) AS amount FROM retail.orders) s
CROSS JOIN (SELECT count(*) AS orders, sum(amount) AS amount FROM retail.fact_orders) f
WHERE s.orders <> f.orders OR s.amount <> f.amount
