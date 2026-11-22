-- Entradas de los datasets Python de silver (vistas temporales).
--
-- Un dataset Python que lee una tabla del pipeline que YA existe en el catalogo (spark.table("x")) la
-- resuelve como tabla externa: SDP no registra la dependencia, lo ejecuta en paralelo con su origen y puede
-- leer datos de la corrida anterior. Una vista temporal no existe en el catalogo, asi que SDP la resuelve
-- dentro del grafo y el dataset espera a su origen. Ver docs/data-model.md, "Dependencias".

CREATE TEMPORARY VIEW src_customers_cdc_events AS
SELECT * FROM customers_cdc_events;
