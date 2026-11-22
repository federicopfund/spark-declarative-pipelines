-- check: customer_sk es unico en dim_customer
SELECT customer_sk, count(*) AS rows
FROM retail.dim_customer
GROUP BY customer_sk
HAVING count(*) > 1
