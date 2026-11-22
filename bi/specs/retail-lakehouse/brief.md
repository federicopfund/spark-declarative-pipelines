# Brief: RetailLakehouse

- **Slug:** `retail-lakehouse` (el único reporte del proyecto; versionado en CHANGELOG.md)
- **Pedido original:** "Quiero un reporte construido sobre el modelo en estrella de la capa gold: las tablas de hechos fact_orders y fact_customer_changes, y las dimensiones dim_date, dim_customer y dim_channel. Debe mostrar las ventas (importe, pedidos, clientes, ticket promedio) por fecha, canal y cliente, aprovechando que cada pedido está unido a la versión del cliente vigente al momento de la compra (país al comprar), y los cambios de los clientes en el tiempo (qué cambió y cuándo). No usar las tablas silver ni los agregados agg_*."
- **Fecha:** 2026-11-22

## Audiencia y objetivo

Gerencia comercial y analistas de clientes. El reporte sirve para ver cómo evolucionan las ventas por día, canal,
país y cliente (con el país que el cliente tenía al comprar) y para entender qué datos de los clientes cambiaron y cuándo.

## Preguntas de negocio

| # | Pregunta | Cómo se responde (KPI o corte) | Tabla de origen |
|---|---|---|---|
| P1 | ¿Cuánto se vendió en total, cuántos pedidos y clientes hubo y cuál es el ticket promedio? | Medidas `Importe`, `Pedidos`, `Clientes`, `Ticket promedio` (tarjetas) | `retail.fact_orders`, `retail.dim_customer` |
| P2 | ¿Cómo evolucionan las ventas por fecha? | `Importe` y `Pedidos` por `dim_date[date]` | `retail.fact_orders`, `retail.dim_date` |
| P3 | ¿Qué canal vende más y con qué ticket? | `Importe`, `Pedidos`, `Ticket promedio` por `dim_channel[channel_name]` | `retail.fact_orders`, `retail.dim_channel` |
| P4 | ¿Cuánto se vendió por país al comprar? | `Importe` por `dim_customer[country]` (versión vigente al comprar) | `retail.fact_orders`, `retail.dim_customer` |
| P5 | ¿Cuánto compró cada cliente? | `Importe`, `Pedidos`, `Ticket promedio` por `dim_customer[name]` | `retail.fact_orders`, `retail.dim_customer` |
| P6 | ¿Cuántos cambios de datos de clientes hubo y de qué tipo? | `Cambios`, `Cambios de país`, `Cambios de email`, `Cambios de nombre` | `retail.fact_customer_changes` |
| P7 | ¿Cuándo cambiaron y qué cambió? | `Cambios` por `dim_date[date]`; tabla de detalle con cliente, fecha, país anterior y nuevo, y cambios | `retail.fact_customer_changes`, `retail.dim_date` |

## KPIs (nombres exactos de las medidas)

| Medida | Definición | Formato |
|---|---|---|
| `Importe` | Suma de `fact_orders[amount]` | `#,0.00` |
| `Pedidos` | Cantidad de pedidos (filas de `fact_orders`, un pedido por fila) | `#,0` |
| `Clientes` | Clientes distintos que compraron (por `customer_id`, NO por `customer_sk`: un cliente con varias versiones cuenta una vez). Se calcula con `dim_customer[customer_id]` filtrado por `fact_orders` | `#,0` |
| `Ticket promedio` | `Importe` / `Pedidos` (divisor seguro, vacío si no hay pedidos) | `#,0.00` |
| `Cambios` | Cantidad de filas de `fact_customer_changes` | `#,0` |
| `Cambios de país` | Cambios con `country_changed = true` | `#,0` |
| `Cambios de email` | Cambios con `email_changed = true` | `#,0` |
| `Cambios de nombre` | Cambios con `name_changed = true` | `#,0` |
| `Clientes con cambios` | Clientes distintos (`customer_id`) con al menos un cambio en `fact_customer_changes` | `#,0` |

## Páginas

| Página | Idea principal | Preguntas |
|---|---|---|
| `Resumen de ventas` | Cuánto, cuándo, dónde y por quién se vende | P1, P2, P3, P4, P5 |
| `Cambios de clientes` | Qué cambió en los clientes y cuándo | P6, P7 |

## Filtros

- Segmentador por canal (`dim_channel[channel_name]`) en la página `Resumen de ventas`.
- Segmentador por año-mes o fecha (`dim_date`) en ambas páginas.
- Sin otros filtros. Las dimensiones comparten `dim_date` y `dim_customer` con los dos hechos, así que los cortes de fecha y cliente aplican a ambas páginas.

## Criterios de aceptación

Valores esperados calculados con los datos actuales de gold (10 pedidos, 5 cambios).

página `Resumen de ventas`
- [ ] CA1: La tarjeta `Importe` muestra 1.196,64.
- [ ] CA2: La tarjeta `Pedidos` muestra 10.
- [ ] CA3: La tarjeta `Clientes` muestra 6 (no 10: hay 10 versiones de cliente con compras).
- [ ] CA4: La tarjeta `Ticket promedio` muestra 119,66.
- [ ] CA5: El gráfico por fecha muestra 3 días: 01/11/2026 = 751,40 (5 pedidos), 02/11/2026 = 309,99 (3), 03/11/2026 = 135,25 (2).
- [ ] CA6: El gráfico por canal muestra Web = 790,74 (7 pedidos, ticket 112,96) y Tienda = 405,90 (3 pedidos, ticket 135,30); no aparece el canal "Desconocido".
- [ ] CA7: El gráfico por país al comprar muestra 6 países sin desplazamiento: Argentina 510,49; Peru 300,00; Chile 225,00; Brasil 60,00; Mexico 55,25; Uruguay 45,90. No aparece "Desconocido" (ningún pedido quedó en el miembro desconocido).
- [ ] CA8: La tabla o gráfico por cliente muestra los 6 clientes con importe: Elena Sosa 300,00; Diego Ruiz 265,25; Ana Torres 200,50; Bruno Diaz 174,99; Facundo Gil 150,00; Carla Perez 105,90.
- [ ] CA9: Se distingue país al comprar de país actual: Argentina vendió 510,49 por país al comprar (el país actual daría 375,49) y Uruguay 45,90 (con país actual no existiría).
- [ ] CA10: Al elegir el canal Tienda en el segmentador, `Importe` = 405,90, `Pedidos` = 3, `Clientes` = 2 y `Ticket promedio` = 135,30.

Página `Cambios de clientes`
- [ ] CA11: La tarjeta `Cambios` muestra 5.
- [ ] CA12: Las tarjetas `Cambios de país`, `Cambios de email` y `Cambios de nombre` muestran 4, 5 y 0.
- [ ] CA13: La tarjeta `Clientes con cambios` muestra 4.
- [ ] CA14: El gráfico de cambios por fecha muestra 3 días: 01/11/2026 = 1, 02/11/2026 = 2, 03/11/2026 = 2.
- [ ] CA15: La tabla de detalle lista las 5 filas (sin desplazamiento) con cliente, fecha del cambio, país anterior (`from_country`), país nuevo (`to_country`) y versiones; Carla Perez aparece 2 veces (Uruguay a Paraguay, Paraguay a Brasil) y Diego Ruiz muestra Argentina a Mexico.

Generales
- [ ] CA16: Todas las páginas tienen título, ningún visual se superpone ni queda fuera de la página, y ninguna etiqueta o categoría aparece cortada.
- [ ] CA17: El modelo usa solo `fact_orders`, `fact_customer_changes`, `dim_date`, `dim_customer` y `dim_channel` (sin tablas silver ni `agg_*`).

## Supuestos

- Moneda no especificada: los importes se muestran sin símbolo.
- Se muestran los nombres de canal (`channel_name`: Web, Tienda) y no los códigos.
- "Clientes" cuenta personas (`customer_id`), no versiones (`customer_sk`). `fact_orders` no tiene `customer_id`; se obtiene por la relación con `dim_customer`.
- "Cliente" en los cortes se identifica por `dim_customer[name]` (único por `customer_id` en los datos actuales); el modelador puede usar `customer_id` como desempate.
- `dim_customer` y `dim_channel` incluyen el miembro desconocido (`-1`); hoy ningún pedido lo usa, pero no debe aparecer en los gráficos con datos. `dim_date` no tiene miembro desconocido y debe marcarse como tabla de fechas.
- La relación `dim_customer` a `fact_customer_changes` usa `customer_sk` (la versión nueva); el país anterior y nuevo se leen de `from_country` y `to_country` del hecho. `previous_customer_sk` no se relaciona (evita una segunda relación activa).
- Los cambios se miden por `date_key` (día); `changed_at` da la hora exacta para el detalle.
- Los valores esperados corresponden a los datos de ejemplo actuales y cambian si se agregan datos.
