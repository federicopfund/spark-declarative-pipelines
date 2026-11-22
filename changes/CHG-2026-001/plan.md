# Plan: CHG-2026-001

Cada tarea tiene un único responsable y solo toca archivos de su propiedad (`docs/agents.md`, sección 8).
Diseño de referencia: `design.md` (columnas, tipos y consulta de referencia). Rutas relativas a
`pipelines/retail_lakehouse/` salvo indicación.

Vuelta posterior a G1 (`reviews/architecture.md`): hallazgo 3 resuelto (el "Hecho cuando" de T1 a T3b ya no exige
datos; eso es T5) y hallazgo 4 resuelto (nueva T3b, control 11). Hallazgos 1 y 6: al cierre (T6) y como deuda.

| # | Tarea | Responsable | Archivos | Depende de | Hecho cuando |
|---|---|---|---|---|---|
| T1 | Control de reconciliación: la suma de `orders` y de `total_amount` de `agg_sales_by_customer` es igual al `count(*)` y a la `sum(amount)` de `fact_orders` | data-quality-engineer | `quality/08_agg_sales_by_customer_reconciliation.sql` | — (G1) | Archivo con `-- check:` que devuelve una fila solo si no cierran y corre sin error de sintaxis (el resultado con datos se verifica en T5) |
| T2 | Control de grano: `customer_id` es único en `agg_sales_by_customer` (y hay una fila por cada `customer_id` distinto de los pedidos de `fact_orders` ⋈ `dim_customer`) | data-quality-engineer | `quality/09_agg_sales_by_customer_unique_customer.sql` | — (G1) | Archivo con `-- check:` que devuelve los `customer_id` repetidos o faltantes y corre sin error de sintaxis (resultado en T5) |
| T3 | Control de completitud y coherencia: `name` y `country` no nulos ni vacíos; `country` igual al de la versión vigente de `dim_customer` (o `'N/A'` si no hay vigente); `first_order_date <= last_order_date`; `orders > 0` | data-quality-engineer | `quality/10_agg_sales_by_customer_current_attributes.sql` | — (G1) | Archivo con `-- check:` que devuelve las filas que violan alguna regla y corre sin error de sintaxis (resultado en T5) |
| T3b | Control de regresión de métricas por cliente: `average_order = round(total_amount / orders, 2)` y `first_order_date` / `last_order_date` iguales al `min` / `max` de `to_date(order_ts)` de `fact_orders` ⋈ `dim_customer` agrupado por `customer_id` (cubre CA4 y CA5) | data-quality-engineer | `quality/11_agg_sales_by_customer_metrics.sql` | — (G1) | Archivo con `-- check:` que devuelve los `customer_id` cuyas métricas no coinciden y corre sin error de sintaxis (resultado en T5) |
| T4 | Crear el materialized view `agg_sales_by_customer` según `design.md` (columnas, tipos, encabezado como `agg_sales_by_country.sql`). El `COMMENT` indica grano, que `country` es el país actual, que sin versión vigente `name` es el de la última versión y `country` = `'N/A'`, y que los pedidos sin versión vigente al comprar suman en la fila `-1` | transformation-engineer | `transformations/gold/sql/aggregates/agg_sales_by_customer.sql` | — (G1) | `bin\spark-pipelines.cmd dry-run` sin errores; tras correr el pipeline, `DESCRIBE retail.agg_sales_by_customer` coincide con la tabla de columnas del diseño |
| T5 | Verificación de datos (G3): `bin\reset-pipeline.cmd`, lotes 1 a 3, pipeline, `bin\check-quality.cmd` (01 a 11) y consulta de CA1 a CA8 contra los valores de `request.md`; firmar `reviews/data-tests.md` | data-quality-engineer | `changes/CHG-2026-001/reviews/data-tests.md` | T1, T2, T3, T3b, T4 (G2) | Controles 01 a 11 pasan y CA1 a CA8 se cumplen, con evidencia de las consultas |
| T6 | Al cierre (G3 aprobado): documentar la tabla nueva. `data-model.md`: árbol de código (sección 1), fila en agregados (sección 6), controles 08 a 11 (sección 8). `architecture.md`: grafo y tabla de datasets (sección 4), tabla de gold (sección 7), cantidad de tablas del catálogo 13 → 14 (sección 1). Sin ADR (ver Decisiones). Revisar las referencias del hallazgo 1 de G1 | data-architect | `docs/data-model.md`, `docs/architecture.md` | T5 | Tabla, grafo y controles documentados; sin cambios en la matriz de bus |
| T7 | Clasificar `agg_sales_by_customer.name` como dato personal en el linaje y la clasificación | security-governance | `docs/governance.md` | T6 | *fase 3 · escalar*: el agente y `docs/governance.md` no existen todavía; queda como deuda en `status.md` (hallazgo 6 de G1) |
| T8 | Contrato `contracts/gold/agg_sales_by_customer.yml` | data-architect | `contracts/gold/agg_sales_by_customer.yml` | — | *fase 2*: `contracts/` y `contract-check` no existen; no se escribe en este cambio, queda como deuda |

Sin tareas de reporte (G4 no aplica: `RetailLakehouse` no cambia), de bronze, plataforma ni release.

Orden: T1, T2, T3, T3b y T4 en paralelo después de G1 (los controles se escriben a partir del diseño y de
`request.md`, sin ver la implementación); G2 revisa T4; T5 es la puerta G3; T6 al cierre.
