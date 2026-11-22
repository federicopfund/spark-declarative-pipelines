-- Entradas de los datasets Python de gold (vistas temporales).
--
-- Los datasets Python leen las tablas del pipeline a traves de estas vistas, no directamente: asi SDP
-- registra la dependencia y los ejecuta despues de su origen (ver silver/inputs.sql y docs/data-model.md).

CREATE TEMPORARY VIEW src_customers_history AS
SELECT * FROM customers_history;

CREATE TEMPORARY VIEW src_dim_customer AS
SELECT * FROM dim_customer;
