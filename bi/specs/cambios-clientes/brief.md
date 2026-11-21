# Brief: CambiosClientes

- **Slug:** `cambios-clientes`
- **Pedido original:** "Quiero un reporte para analizar cómo cambian los datos de nuestros clientes: cuántos clientes tenemos hoy, cuántos cambios registramos, qué clientes cambiaron de país y cómo se ve la historia de cada uno."
- **Fecha:** 2026-11-21

## Audiencia y objetivo

Equipo comercial y de datos maestros de clientes. El reporte muestra el padrón vigente y cómo evolucionaron
los datos de cada cliente (país, email), para detectar migraciones entre países y auditar la historia de
cambios capturada por CDC (SCD1 en `customers`, SCD2 en `customers_history`).

## Preguntas de negocio

| # | Pregunta | Cómo se responde (KPI o corte) | Tabla de origen |
|---|---|---|---|
| P1 | ¿Cuántos clientes tenemos hoy? | Medida `Clientes actuales` | `retail.customers` |
| P2 | ¿Dónde están hoy nuestros clientes? | `Clientes actuales` por `customers[country]` | `retail.customers` |
| P3 | ¿Cuántos cambios registramos? | Medidas `Versiones` y `Cambios registrados` | `retail.customers_history` |
| P4 | ¿Cuántos clientes tuvieron al menos un cambio? | Medida `Clientes con cambios` | `retail.customers_history` |
| P5 | ¿Qué clientes cambiaron de país? | Medida `Clientes que cambiaron de país`; tabla por cliente con `Países registrados` y país actual | `retail.customers_history` ⟶ `retail.customers` |
| P6 | ¿Cómo es la historia de un cliente? | Tabla de versiones (versión, país, email, fecha, vigencia, `Estado`) filtrada por cliente | `retail.customers_history` |

## KPIs (nombres exactos de las medidas)

| Medida | Tabla | Definición | Formato |
|---|---|---|---|
| `Clientes actuales` | `customers` | Clientes vigentes (una fila por cliente, sin los borrados): `COUNTROWS ( customers )` | `#,0` |
| `Versiones` | `customers_history` | Cantidad de versiones registradas: `COUNTROWS ( customers_history )` | `#,0` |
| `Cambios registrados` | `customers_history` | Versiones posteriores a la primera de cada cliente: `[Versiones] - DISTINCTCOUNT ( customers_history[customer_id] )` | `#,0` |
| `Clientes con cambios` | `customers_history` | Clientes con más de una versión | `#,0` |
| `Países registrados` | `customers_history` | Cantidad de países distintos por los que pasó el cliente: `DISTINCTCOUNT ( customers_history[country] )` | `#,0` |
| `Clientes que cambiaron de país` | `customers_history` | Clientes con `Países registrados` > 1 | `#,0` |

Columna calculada requerida: `customers_history[Estado]` = `"Vigente"` si `__END_AT` es nulo, `"Histórica"` si no.
Relación: `customers_history[customer_id]` → `customers[customer_id]` (muchos a uno).

## Páginas

| Página | Idea principal | Preguntas |
|---|---|---|
| `Resumen` | Foto de hoy y volumen de cambios: 4 tarjetas (`Clientes actuales`, `Versiones`, `Cambios registrados`, `Clientes con cambios`) y un gráfico de barras `Clientes actuales` por país | P1, P2, P3, P4 |
| `Cambios de país` | Quiénes migraron de país: tarjeta `Clientes que cambiaron de país` y tabla por cliente (id, nombre, país actual, `Países registrados`, `Versiones`) solo con los que cambiaron | P5 |
| `Historia por cliente` | Línea de tiempo de cada cliente: segmentador por nombre de cliente y tabla de versiones (`customer_id`, `name`, `version`, `country`, `email`, `event_ts`, `__START_AT`, `__END_AT`, `Estado`) ordenada por cliente y versión | P6 |

## Filtros

- Página `Historia por cliente`: segmentador por `customers_history[name]` (selección simple; sin selección muestra todas las versiones).
- Página `Cambios de país`: filtro a nivel de visual en la tabla, `Países registrados` > 1.
- Sin filtros de página ni de reporte en `Resumen`.

## Criterios de aceptación

Valores esperados tomados de `retail.customers` (6 filas) y `retail.customers_history` (11 filas) el 2026-11-21.

- [ ] CA1: La tarjeta `Clientes actuales` muestra **6**.
- [ ] CA2: La tarjeta `Versiones` muestra **11**.
- [ ] CA3: La tarjeta `Cambios registrados` muestra **5**.
- [ ] CA4: La tarjeta `Clientes con cambios` muestra **4** (clientes 1, 2, 3 y 4).
- [ ] CA5: El gráfico de clientes por país muestra los **5 países** sin desplazamiento: Argentina 2, Brasil 1, Chile 1, Mexico 1, Peru 1.
- [ ] CA6: La tarjeta `Clientes que cambiaron de país` muestra **3**.
- [ ] CA7: La tabla de `Cambios de país` lista exactamente 3 clientes: Bruno Diaz (actual Argentina, 2 países), Carla Perez (actual Brasil, 3 países), Diego Ruiz (actual Mexico, 2 países). Ana Torres **no** aparece (solo cambió el email).
- [ ] CA8: En `Historia por cliente`, al seleccionar Carla Perez la tabla muestra 3 versiones en orden: Uruguay (v1, Histórica), Paraguay (v2, Histórica), Brasil (v3, Vigente).
- [ ] CA9: Sin selección en el segmentador, la tabla de historia muestra 11 filas: 6 `Vigente` y 5 `Histórica`.
- [ ] CA10: Ninguna tabla ni gráfico requiere desplazamiento horizontal para ver sus columnas.

## Supuestos

- "Cambio" = cualquier versión posterior a la primera de un cliente, sin importar qué campo cambió (país, email, nombre). Por eso Ana Torres cuenta como cliente con cambios (email) pero no como cambio de país.
- "Cambió de país" = pasó por más de un país distinto en su historia. Un ida y vuelta (A → B → A) contaría igual; con los datos actuales no ocurre.
- El cliente 4 (Diego Ruiz) no tiene versión 2: su v1 se cerró en `__END_AT` = 2 y la siguiente versión es la 3 (la v2 fue un DELETE que el SCD2 descarta, seguido de un re-alta). El reporte no muestra bajas porque `customers_history` no guarda filas de DELETE; se cuenta 1 cambio para este cliente.
- Hoy no hay clientes borrados: los 6 clientes de la historia están vigentes en `customers`.
- No se pidió evolución temporal de los cambios (por día), así que no se incluye un gráfico por fecha; `event_ts` solo se muestra en la tabla de historia.
- No se cruza con pedidos ni ventas: el pedido es solo sobre datos maestros de clientes.
