# Revisión: datos · CHG-2026-001 · vuelta 1

- **Revisor:** data-quality-engineer
- **Veredicto:** RECHAZADO (puerta G3 sin completar: la primera corrida del pipeline se colgó; no se pudo verificar ningún criterio)
- **Revisado:** `pipelines/retail_lakehouse/quality/01..11`, `transformations/gold/sql/aggregates/agg_sales_by_customer.sql` (sin cambios de código en esta vuelta; ambiente reconstruido desde cero, con confirmación de la persona)

## Verificaciones deterministas

Se frenó en el primer error, según la instrucción. Fecha local 2026-11-22, hora ART.

| Verificación | Comando | Resultado |
|---|---|---|
| Reset desde cero | `bin\reset-pipeline.cmd` | PASA (derby, master, worker, connect y thrift arriba; base `retail` creada; unos 3 min) |
| Lote 1 | `bin\land-batch.cmd -Batch 1` | PASA (3 archivos en landing) |
| Pipeline tras lote 1 | `bin\spark-pipelines.cmd run` | FALLA: se cuelga. Inicio 03:54:57; último evento 03:55:30 (`orders_export_flow has COMPLETED`); sin nuevos eventos hasta 04:07 (más de 11 min, pasa el límite de 10). Se detuvo el cliente a mano |
| Lote 2, pipeline, lote 3, pipeline | `land-batch -Batch 2/3`, `spark-pipelines run` | NO EJECUTADO (se frena ante el primer error) |
| Controles de calidad | `bin\check-quality.cmd` (01 a 11) | NO EJECUTADO (las tablas gold no existen: no hay corrida completa) |

Diagnóstico del cuelgue (logs y Spark UI del Connect server, `http://127.0.0.1:4040`):

- Flujos `COMPLETED`: `dim_channel`, `orders_web_raw`, `orders_store_raw`, `customers_cdc_events`, `customers`, `orders`, `orders_export_flow`.
- `spark_catalog.retail.customers_history` quedó en `RUNNING` (03:55:11) y nunca terminó. Ningún flujo gold (`dim_customer`, `fact_*`, `agg_*`) llegó a `STARTING`, así que el dataset nuevo `agg_sales_by_customer` ni se evaluó.
- Spark UI: el job 6 (`start_run`) tiene 1 tarea activa en la etapa 7, en el ejecutor 0, sin avanzar desde las 06:55:18 UTC (03:55 ART). El worker tiene 3/3 cores y 3072/3072 MB usados (Connect: 2 ejecutores de 1 core; Thrift: 1 ejecutor de 1 core), 0 cores libres.
- En `logs/pipeline-run-3.log` (corrida anterior del 2026-11-22 02:07), `customers_history` completó en 15 s, así que no es un problema estructural conocido. La causa no se determinó: puede ser del ambiente (recursos del worker, tarea trabada en el ejecutor) o del pipeline. `customers_history` es código existente, no cambiado por este cambio (`git status` muestra solo archivos nuevos).
- No se pudo atribuir con certeza. No se reintentó el reset para no repetir una reconstrucción completa sin confirmación; ver recomendación.

### Controles de calidad

| Control | Resultado |
|---|---|
| 01 a 07 (existentes, regresión CA8) | NO EJECUTADO |
| 08 reconciliación `agg_sales_by_customer` vs `fact_orders` | NO EJECUTADO |
| 09 unicidad por `customer_id`, faltantes y sobrantes | NO EJECUTADO |
| 10 `name`/`country` no vacíos, país = versión vigente o `'N/A'`, `orders > 0`, fechas ordenadas | NO EJECUTADO |
| 11 métricas: `average_order`, primera y última fecha | NO EJECUTADO |

Controles: 0/11 ejecutados.

### Criterios de aceptación (valores esperados calculados desde `data/samples/` y `request.md`)

| CA | Esperado | Obtenido | Resultado |
|---|---|---|---|
| CA1 | 6 filas, `customer_id` 1 a 6 sin repetidos | sin datos | NO VERIFICADO |
| CA2 | pedidos: 1=2, 2=2, 3=2, 4=2, 5=1, 6=1; suma 10 = filas de `fact_orders` | sin datos | NO VERIFICADO |
| CA3 | total: 1=200.50, 2=174.99, 3=105.90, 4=265.25, 5=300.00, 6=150.00; suma 1196.64 | sin datos | NO VERIFICADO |
| CA4 | ticket: 1=100.25, 2=87.50, 3=52.95, 4=132.63, 5=300.00, 6=150.00 | sin datos | NO VERIFICADO |
| CA5 | primera/última: 1=11-01/11-03, 2=11-01/11-02, 3=11-01/11-02, 4=11-01/11-03, 5=11-01/11-01, 6=11-02/11-02 | sin datos | NO VERIFICADO |
| CA6 | país: 1=Argentina, 2=Argentina, 3=Brasil, 4=Mexico, 5=Peru, 6=Chile | sin datos | NO VERIFICADO |
| CA7 | clientes 2 y 3 en una sola fila con todos sus pedidos; país no vacío | sin datos | NO VERIFICADO |
| CA8 | controles 01 a 07 pasan | sin datos | NO VERIFICADO |

Criterios: 0/8 verificados.

## Hallazgos

| # | Hallazgo | Evidencia (archivo:línea o salida) | Severidad | Responsable |
|---|---|---|---|---|
| 1 | `spark-pipelines run` del lote 1 sobre ambiente recién reconstruido se cuelga: `customers_history` queda `RUNNING` más de 11 min y no arranca ningún flujo gold. Bloquea toda la puerta G3. Causa sin determinar (¿pipeline o ambiente?). Los controles y el dataset nuevo no se pudieron evaluar | `scratchpad/run1.txt` (último evento `orders_export_flow has COMPLETED` 06:55:30 UTC); `logs/connect-server.log` (sin eventos tras 03:55:31); Spark UI job 6, etapa 7, 1 tarea activa en ejecutor 0; worker 3/3 cores usados | bloqueante | transformation-engineer |

Recomendación al orquestador: reintentar la vuelta (reset, lotes 1 a 3, controles) una vez más antes de dar el defecto por
del código. Si se repite en `customers_history`, el responsable es `transformation-engineer`; si el pipeline pasa, el
cuelgue fue del ambiente (por ejemplo, el Thrift Server ocupando cores del worker) y conviene registrarlo como deuda en
`status.md`. La persona debe confirmar otro reset, porque borra todo el estado local.

Severidades: **bloqueante** frena la puerta; **mayor** se corrige en esta vuelta; **menor** queda como deuda en
`status.md`. El veredicto es RECHAZADO si hay al menos un hallazgo bloqueante o mayor.
