-- check: las vigencias [valid_from, valid_to) de un cliente no se superponen
SELECT a.customer_id, a.version AS version_a, b.version AS version_b
FROM retail.dim_customer a
JOIN retail.dim_customer b
  ON  a.customer_id = b.customer_id
  AND a.version < b.version
  AND a.valid_to > b.valid_from
