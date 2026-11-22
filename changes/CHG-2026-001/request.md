# Request: CHG-2026-001 · Resumen de compras por cliente (piloto)

- **Pedido original:** "Piloto: necesito un resumen de compras por cliente con la cantidad de pedidos, el importe total, el ticket promedio, la fecha de la primera y de la última compra, y el país actual del cliente."
- **Fecha:** 2026-11-22
- **Tipo:** tabla nueva
- **Estado G0:** APROBADO (2026-11-22)

## Objetivo de negocio

Quien analiza clientes (comercial o BI) necesita ver en una sola tabla cuánto y cuándo compró cada cliente y en qué
país está hoy. Permite identificar clientes de mayor valor, ticket promedio bajo o alto y antigüedad de la relación
de compra, sin recalcular métricas a partir de los pedidos en cada análisis. Es un piloto del flujo `/deliver`.

## Preguntas de negocio

| # | Pregunta | Dato que la responde | Fuente actual |
|---|---|---|---|
| P1 | ¿Cuántos pedidos hizo cada cliente? | Conteo de pedidos por cliente | `retail.fact_orders` (`order_id`, `customer_sk`) |
| P2 | ¿Cuánto compró en total? | Suma de `amount` por cliente | `retail.fact_orders` (`amount`) |
| P3 | ¿Cuál es su ticket promedio? | Importe total / cantidad de pedidos | `retail.fact_orders` (derivado) |
| P4 | ¿Cuándo hizo su primera y su última compra? | Mínimo y máximo de `order_ts` (como fecha) por cliente | `retail.fact_orders` (`order_ts`) |
| P5 | ¿En qué país está hoy? | País de la versión vigente del cliente | `retail.dim_customer` (`country`, `is_current`) |
| P6 | ¿Quién es el cliente? (para identificarlo en el resumen) | `customer_id` y nombre | `retail.dim_customer` (`customer_id`, `name`) |

Todos los datos ya existen en gold; no hay fuentes nuevas ni trabajo de bronze.

## Fuentes y consumidores

- Fuentes: `retail.fact_orders` y `retail.dim_customer`. Los agregados existentes se calculan desde `fact_orders`
  (`docs/data-model.md`, sección 6); este pedido debe seguir esa regla.
- Un pedido está unido a la versión del cliente vigente al comprar, no a la actual. Por eso el resumen debe
  agrupar por la clave de negocio `customer_id` (no por `customer_sk`) para no partir a un cliente en varias filas
  cuando tuvo más de una versión. El país se toma de la versión vigente (`is_current`).
- Consumidores: por ahora ninguno definido. El reporte `RetailLakehouse` no cambia en este pedido (ver Fuera de alcance).

## Requisitos no funcionales

| Requisito | Valor |
|---|---|
| Frescura (SLA) | Actualizado después de cada corrida del pipeline (igual que los demás agregados gold) |
| Volumen esperado | Una fila por cliente con al menos un pedido; 6 filas con los lotes 1 a 3 |
| Histórico | Sin historia: refleja el estado actual (el país es el actual; no se guarda cómo cambió) |
| Datos personales | Nombre del cliente (dato personal ya presente en `dim_customer`). No se agrega email. |

## Criterios de aceptación

Verificables con una consulta después de correr el pipeline desde cero con los lotes 1 a 3. Valores calculados a
partir de `data/samples/` y contrastados con `retail.fact_orders` (10 pedidos) y `retail.customers` actuales.
El nombre de la tabla lo define el arquitecto; abajo se la llama "el resumen".

- [ ] CA1: el resumen tiene 6 filas, una por `customer_id` (1 a 6), sin repetidos.
- [ ] CA2: cantidad de pedidos por cliente: clientes 1, 2, 3 y 4 tienen 2; clientes 5 y 6 tienen 1. La suma de
  pedidos de todo el resumen es 10, igual a las filas de `retail.fact_orders`.
- [ ] CA3: importe total por cliente: 1 = 200.50; 2 = 174.99; 3 = 105.90; 4 = 265.25; 5 = 300.00; 6 = 150.00.
  La suma del resumen es 1196.64, igual a la suma de `amount` de `retail.fact_orders`.
- [ ] CA4: ticket promedio (total / pedidos, redondeado a 2 decimales): 1 = 100.25; 2 = 87.50; 3 = 52.95;
  4 = 132.63; 5 = 300.00; 6 = 150.00.
- [ ] CA5: primera y última compra (fecha): 1 = 2026-11-01 y 2026-11-03; 2 = 2026-11-01 y 2026-11-02;
  3 = 2026-11-01 y 2026-11-02; 4 = 2026-11-01 y 2026-11-03; 5 = 2026-11-01 y 2026-11-01; 6 = 2026-11-02 y 2026-11-02.
- [ ] CA6: país actual: 1 = Argentina; 2 = Argentina (compró desde Chile, W-1002, pero hoy es Argentina);
  3 = Brasil (compró desde Uruguay, S-2001); 4 = Mexico (Diego Ruiz fue dado de baja y reinsertado; W-1003 y W-1007
  cuentan ambos para el cliente 4); 5 = Peru; 6 = Chile.
- [ ] CA7: ningún cliente aparece partido en más de una fila ni con país vacío; el cliente 3 (Carla Perez, 3 versiones
  en silver) y el cliente 2 (2 versiones) suman todos sus pedidos en una sola fila.
- [ ] CA8: todos los controles de calidad existentes (`bin\check-quality.cmd`, controles 01 a 07) siguen pasando.

## Fuera de alcance

- Cambios en el reporte Power BI `RetailLakehouse` (si se quiere mostrar, será otro pedido y pasaría por G4).
- Clientes sin pedidos (no aparecen en el resumen).
- Historia del país (país al comprar o cambios de país): ya disponible en `fact_orders` + `dim_customer` y
  `fact_customer_changes`.
- Segmentación (por canal, por período), recencia, frecuencia u otras métricas no pedidas.
- Fuentes nuevas, cambios en bronze o en silver.

## Supuestos

- "Importe total" y "ticket promedio" se calculan sobre todos los pedidos de `fact_orders`, sin filtrar canal ni fecha
  y sin descontar devoluciones (no existen en los datos).
- "Ticket promedio" = importe total / cantidad de pedidos, con 2 decimales; en empate de medio centavo se redondea
  hacia arriba (cliente 2: 87.495 pasa a 87.50; cliente 4: 132.625 pasa a 132.63).
- "Fecha" de primera y última compra es la fecha calendario de `order_ts`, sin hora.
- "País actual" es el país de la versión vigente del cliente. Si un cliente no tuviera versión vigente (dado de baja
  sin reinsertar) y tuviera pedidos, el país queda sin valor; con los lotes de ejemplo no ocurre (el cliente 4 se
  reinserta en el lote 3). El arquitecto decide cómo mostrar ese caso.
- Incluye nombre del cliente además de `customer_id` para poder leer el resumen; no se pidió email y no se incluye.
- Piloto: no se define un reporte ni exportación para este resumen.
