# Revisión: código · CHG-2026-001 · vuelta 1

- **Revisor:** code-reviewer
- **Veredicto:** APROBADO
- **Revisado:** archivos nuevos sin commitear sobre `change/CHG-2026-001` (`git diff main...HEAD` y `git diff`
  vacíos; `git status` muestra solo los nuevos):
  `pipelines/retail_lakehouse/transformations/gold/sql/aggregates/agg_sales_by_customer.sql`,
  `pipelines/retail_lakehouse/quality/08_agg_sales_by_customer_reconciliation.sql`,
  `09_agg_sales_by_customer_unique_customer.sql`, `10_agg_sales_by_customer_current_attributes.sql`,
  `11_agg_sales_by_customer_metrics.sql`, y `changes/CHG-2026-001/` (documentos del cambio)

## Verificaciones deterministas

| Verificación | Comando | Resultado |
|---|---|---|
| Dry-run del pipeline | `bin\spark-pipelines.cmd dry-run` | PASA: 17 archivos encontrados, `agg_sales_by_customer.sql` registrado, `Run is COMPLETED.` sin errores |
| Secretos, rutas absolutas, datos personales | `grep -rniE 'password\|secret\|token\|C:\\Users\|C:/Users'` sobre los 5 archivos nuevos y `changes/CHG-2026-001/` (el diff contra `main` está vacío porque nada está commiteado) | PASA: sin coincidencias |
| Propiedad de archivos (`docs/agents.md`, sección 8) | revisión manual | PASA: `transformations/gold/` es de `transformation-engineer` (T4); `quality/08` a `11` son de `data-quality-engineer` (T1, T2, T3, T3b); no se modificó ningún archivo existente |

## Lista de verificación

1. **Fidelidad**: `agg_sales_by_customer.sql:14-38` coincide con la consulta de referencia de `design.md`: las
   mismas 9 columnas en el mismo orden, con nombres, expresiones y grano (`customer_id`) iguales. Nada de más ni de
   menos. `spark-pipeline.yml` no cambia.
2. **Correctitud**: `INNER JOIN` por `customer_sk` (N:1, sin pérdida porque `fact_orders` siempre tiene un `sk`
   válido o `-1`) y luego por `customer_id` contra `customer_latest`, que tiene una fila por `customer_id`. No
   multiplica filas. País `'N/A'` sin versión vigente, nombre de la última versión, miembro desconocido en la fila
   `-1`: todo según el diseño. Tipos: los que da Spark (`sum` → `decimal(22,2)`, `round(avg)` → `decimal(13,2)`,
   `to_date` → `date`).
3. **SDP**: dataset SQL con un único flow; sin vistas `src_*` (no hacen falta en SQL); sin efectos fuera del grafo.
4. **Convenciones**: el encabezado explica propósito, grano, semántica de país y nombre, y fila `-1`, como
   `agg_sales_by_country.sql`. El `COMMENT` cubre todo lo que pide T4. `_loaded_at` con `current_timestamp()`, como
   `fact_orders.sql` y `dim_channel.sql`. No se duplica lógica de `gold/keys.py` ni de `cdc.py`.
5. **Controles de calidad**: cada regla nueva tiene su control y todos devuelven las filas que la violan:
   08 reconcilia pedidos e importe (con `<=>` para el caso vacío); 09 detecta repetidos, faltantes y sobrantes;
   10 revisa nombre y país no vacíos, país contra la versión vigente o `'N/A'`, `orders > 0` y el orden de las
   fechas; 11 recalcula pedidos, importe, ticket promedio y fechas.
6. **Mantenibilidad**: el código es legible, no tiene código muerto, y los comentarios explican el porqué (por
   ejemplo, `-- a lo sumo una vigente (control 05)` en `10:6`).

## Hallazgos

| # | Hallazgo | Evidencia (archivo:línea o salida) | Severidad | Responsable |
|---|---|---|---|---|
| 1 | El control 11 compara `average_order` (que sale de `round(avg(amount), 2)`) con `round(total_amount / orders, 2)`. Spark calcula `avg` de `decimal(12,2)` como `decimal(16,6)`, es decir que redondea dos veces (a 6 decimales y después a 2). Puede dar falsos positivos de 0.01 cuando la parte fraccionaria de `100·total/orders` cae en `[0.49995, 0.5)`. Eso solo pasa con más de unos 20 000 pedidos por cliente, así que hoy no ocurre. Si alguna vez aparece, hay que decidir si la fuente de verdad es la fórmula o el control. | `quality/11_agg_sales_by_customer_metrics.sql:23`; `agg_sales_by_customer.sql:29` | menor | data-quality-engineer |

Severidades: **bloqueante** frena la puerta; **mayor** se corrige en esta vuelta; **menor** queda como deuda en
`status.md`. El veredicto es RECHAZADO si hay al menos un hallazgo bloqueante o mayor.
