-- check: cada cliente tiene a lo sumo una version vigente
-- (cero es valido: un cliente dado de baja no tiene version vigente)
SELECT customer_id, count(*) AS current_versions
FROM retail.dim_customer
WHERE is_current
GROUP BY customer_id
HAVING count(*) > 1
