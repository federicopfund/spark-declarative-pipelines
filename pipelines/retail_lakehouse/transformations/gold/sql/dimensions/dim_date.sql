-- gold.dim_date - calendario.
--
-- Grano: un dia. Cubre años completos, desde el primer hasta el ultimo año con pedidos o eventos de
-- clientes, asi que crece solo cuando llegan datos de un año nuevo.
-- date_key = yyyyMMdd (int). Dias de la semana en formato ISO: 1 = lunes ... 7 = domingo.
--
-- Sin miembro desconocido (excepcion a la convencion del modelo): Power BI exige que la columna de fecha de
-- una tabla de fechas sea unica, sin blancos y sin huecos. Las fechas de los hechos nunca son desconocidas
-- (order_ts y event_ts son obligatorios en bronze) y el control de calidad 03 verifica la cobertura.

CREATE MATERIALIZED VIEW dim_date
COMMENT 'Calendar. Grain: one day (full years, contiguous). date_key yyyyMMdd. No unknown member.'
AS WITH bounds AS (
  SELECT
    make_date(year(min(d)), 1, 1)   AS first_day,
    make_date(year(max(d)), 12, 31) AS last_day
  FROM (
    SELECT CAST(order_ts AS DATE) AS d FROM orders
    UNION ALL
    SELECT CAST(event_ts AS DATE) AS d FROM customers_history
  )
),
days AS (
  SELECT explode(sequence(first_day, last_day, INTERVAL 1 DAY)) AS date FROM bounds
)
SELECT
  CAST(date_format(date, 'yyyyMMdd') AS INT)                             AS date_key,
  date,
  year(date)                                                             AS year,
  quarter(date)                                                          AS quarter,
  month(date)                                                            AS month,
  element_at(array('enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto',
                   'septiembre', 'octubre', 'noviembre', 'diciembre'), month(date)) AS month_name,
  date_format(date, 'yyyy-MM')                                           AS year_month,
  day(date)                                                              AS day_of_month,
  (dayofweek(date) + 5) % 7 + 1                                          AS day_of_week,
  element_at(array('lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo'),
             (dayofweek(date) + 5) % 7 + 1)                              AS day_name,
  dayofweek(date) IN (1, 7)                                              AS is_weekend,
  current_timestamp()                                                    AS _loaded_at
FROM days;
