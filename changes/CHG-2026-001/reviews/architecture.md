# Revisión: arquitectura · CHG-2026-001 · vuelta 1

- **Revisor:** architecture-reviewer
- **Veredicto:** APROBADO
- **Revisado:** `changes/CHG-2026-001/request.md` (G0 aprobado), `design.md`, `plan.md`; contra el repo en la rama
  `change/CHG-2026-001` (commit base `2099a85`): `docs/data-model.md`, `docs/architecture.md`, `docs/agents.md`,
  `transformations/gold/**`, `transformations/silver/orders.sql`, `src/retail_lakehouse/cdc.py`,
  `quality/*.sql`, `clients/check_quality.py`, `data/samples/`.

## Verificaciones deterministas

| Verificación | Comando | Resultado |
|---|---|---|
| Contratos válidos | `contract-check --schema` | NO APLICA: `contracts/` y `contract-check` son de la fase 2 (`docs/agents.md`, sección 13); el diseño no escribe contrato (T8 como deuda) |
| Grafo SDP sin ciclos, un flow por target | Lectura de `design.md` §Grafo contra `transformations/gold/**` | PASA: `fact_orders` → `agg_sales_by_customer` ← `dim_customer`; un solo MV SQL, nombre sin colisión con datasets existentes; el glob `transformations/**` lo descubre |
| Regla `src_*` | Lectura de `design.md` §Grafo y `docs/data-model.md` §1 | PASA: dataset SQL (`FROM fact_orders`, `FROM dim_customer`); la regla `src_*` aplica solo a Python |
| Tipos de la tabla de columnas | Reglas de tipos de Spark: `sum(decimal(12,2))` → `decimal(22,2)`; `avg` → `decimal(16,6)`; `round(·,2)` → `decimal(13,2)` | PASA: coinciden con `design.md` líneas 33 y 34 |
| Supuesto "la vigente es la de mayor `version`" | `src/retail_lakehouse/cdc.py:169-179` (`__END_AT = lead(sequence)`, los DELETE se filtran después) | PASA: solo la versión no-DELETE de mayor secuencia puede tener `__END_AT` nulo, así que `max_by(country, version)` + `bool_or(is_current)` equivale a unir con `is_current` (`design.md` líneas 66-68) |
| Unicidad de `order_id` en el hecho (base de `count(*)`) | `transformations/silver/orders.sql:10-17` (dedup `row_number() ... WHERE rn = 1`) | PASA |
| Miembro desconocido | `transformations/gold/python/dimensions/dim_customer.py:63-73` | PASA: `customer_id = -1`, `version = 0`, `country`/`name` = `'Desconocido'`, `is_current = true`; cae en una fila `-1` con país no nulo, como describe `design.md` líneas 70-73 |
| Zona horaria de `to_date(order_ts)` | `grep timeZone` en el repo; `data/samples/*/orders_*` | PASA: timestamps sin zona y sin `timeZone` configurado; fecha consistente con `fact_orders.date_key` (`date_format` en la misma sesión) |

## Cobertura del pedido

| Pedido | Lo resuelve | Verificado por |
|---|---|---|
| P1 / CA2 | `orders = count(*)` | T1 (total), T5 (por cliente) |
| P2 / CA3 | `total_amount = sum(amount)` | T1 (total), T5 |
| P3 / CA4 | `average_order = round(avg(amount), 2)`, HALF_UP | T5 (ver hallazgo 4) |
| P4 / CA5 | `first_order_date`, `last_order_date` (`date`) | T3 (`first <= last`), T5 |
| P5 / CA6 | `country` de la vigente, `'N/A'` sin vigente | T3, T5 |
| P6 | `customer_id`, `name` | T2, T3 |
| CA1 / CA7 | Grano `customer_id` (agrupa versiones) | T2, T5 |
| CA8 | Sin cambios en 01-07 | T5 (`check-quality` 01 a 10) |
| Datos personales | `name` sí, `email` no | `design.md` §Impacto; T7 (fase 3) |

Modelado correcto: capa gold, agregado derivado de `fact_orders` (regla de `data-model.md` §6), grano explícito y
único, clave de negocio sin sustituta (como los agregados existentes), sin SCD (estado actual), sin cambios en la
matriz de bus, `_loaded_at` según `data-model.md` §7. Cambio compatible: tabla nueva, ningún consumidor afectado,
`model.json` sin cambios, sin migración ni G4.

## Hallazgos

| # | Hallazgo | Evidencia (archivo:línea o salida) | Severidad | Responsable |
|---|---|---|---|---|
| 1 | La lista de impacto en documentación omite referencias que quedan desactualizadas con la tabla y los controles nuevos: "7 controles de calidad" en `architecture.md` (pasa a 10), los agregados enumerados en `README.md` y "contracts/ para las 13 tablas" en `agents.md`. `README.md` no tiene dueño en la sección 8 de `agents.md`. | `design.md:106`, `plan.md:14` (T6) vs. `docs/architecture.md:372`, `README.md:122`, `README.md:176`, `docs/agents.md:357` | menor | data-architect |
| 2 | Límite no documentado: un pedido hecho durante el lapso de una baja (o antes de que el cliente llegue por CDC) va a `customer_sk = -1` y en el resumen se suma a la fila `-1`, no a su cliente real aunque luego se reinserte. Como `fact_orders` no guarda `customer_id`, el agregado no puede recuperarlo sin violar la regla de §6. Esto relativiza CA7 ("ningún cliente partido") fuera de los lotes de ejemplo. Conviene dejarlo en Riesgos y en el `COMMENT`. | `design.md:70-73`, `design.md:143-144`; `transformations/gold/sql/facts/fact_orders.sql:6-9,16`; `docs/data-model.md:191-192` | menor | data-architect |
| 3 | Las tareas T1, T2 y T3 declaran "Depende de: —" pero su "Hecho cuando" exige "sin filas con los lotes 1 a 3", que solo se puede comprobar con T4 implementada; esa verificación es parte de T5. El criterio de hecho de T1–T3 debería ser "archivo con `-- check:` que corre sin error de sintaxis" y dejar el resultado en T5. | `plan.md:9-11`, `plan.md:13`, `plan.md:20-21` | menor | data-architect |
| 4 | Sin control para la regla nueva de ticket promedio: ningún control verifica `average_order = round(total_amount / orders, 2)` ni que las fechas caigan dentro del rango de `fact_orders` de cada cliente; CA4/CA5 quedan cubiertos solo por la consulta puntual de T5 y no por regresión. Sugerido: sumar esa regla a T3 (control 10) o a T1 (control 08). | `plan.md:9-11`; `design.md:34-36` | menor | data-architect |
| 5 | Semántica mixta de atributos para clientes sin versión vigente: `name` es el de la última versión conocida, pero `country` es `'N/A'`. Está justificado en Decisiones, pero no figura en Riesgos ni en el `COMMENT` pedido en T4; quien lea la tabla puede tomar `name` como "actual". | `design.md:30-31`, `design.md:124-125`, `plan.md:12` | menor | data-architect |
| 6 | G1 pide revisión de `security-governance` (PII) y ese agente no existe en la fase 1; la exposición de `name` quedó aprobada por la persona en G0, pero la revisión de seguridad no se hace. El diseño lo reconoce (T7), y tiene que quedar como deuda explícita en `status.md`. | `docs/agents.md` §6 (G1) y §13; `design.md:107`, `design.md:141-142`; `plan.md:15`; `status.md:8` | menor | data-architect |

Severidades: **bloqueante** frena la puerta; **mayor** se corrige en esta vuelta; **menor** queda como deuda en
`status.md`. El veredicto es RECHAZADO si hay al menos un hallazgo bloqueante o mayor.

Sin hallazgos bloqueantes ni mayores. **Veredicto: APROBADO.** Los hallazgos 1 a 6 se registran como deuda en
`status.md`. Se recomienda resolver el 3 y el 4 en `plan.md` antes de lanzar T1–T3, porque son baratos y
afectan a lo que el `data-quality-engineer` escribe primero.
