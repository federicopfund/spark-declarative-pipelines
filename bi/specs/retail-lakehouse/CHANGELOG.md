# Changelog: RetailLakehouse

`RetailLakehouse` es **el único reporte** del proyecto (`bi/powerbi/RetailLakehouse.pbip`, con su modelo semántico
`RetailLakehouse.SemanticModel`). Cada pedido a `/build-report` lo **modifica** (agrega o cambia páginas, visuales,
medidas o filtros) y agrega una entrada acá; nunca se crea otro reporte ni otro modelo.

La versión vive en `layout.json` (`"version"`), en el encabezado de cada página y en la anotación `version` del
reporte. `build_report.py` no construye una versión que no tenga su entrada en este archivo.

| Cambio | Versión |
|---|---|
| Se quita o se rehace una página, o el modelo cambia de forma incompatible (se borra una tabla o medida usada) | **mayor** (`3.0`) |
| Se agrega una página, un visual, una medida, una columna o un filtro | **menor** (`2.1`) |
| Correcciones de QA, formato o textos sin cambiar el contenido | **parche** (`2.0.1`) |

Formato de cada entrada: `## [versión] - AAAA-MM-DD`, una línea con el pedido y las secciones que apliquen
(**Agregado**, **Cambiado**, **Corregido**, **Quitado**).

## [2.0] - 2026-11-22

Pedido: un solo reporte sobre el modelo estrella de gold, con un diseño profesional.

**Cambiado**
- El modelo pasa a ser el modelo estrella: `fact_orders`, `fact_customer_changes`, `dim_date`, `dim_customer`,
  `dim_channel`. Sin tablas silver ni agregados.
- Sistema de diseño `LakehouseModern` (`bi/design/`): tema, banda de encabezado con versión, riel de filtros a la
  izquierda y grilla de 20 px.

**Agregado**
- Página **Resumen de ventas**: importe, pedidos, clientes y ticket promedio; importe por fecha, canal, país al
  comprar y cliente; segmentadores de canal y año-mes.
- Página **Cambios de clientes**: cambios por tipo, clientes con cambios, cambios por fecha y detalle de cada cambio.

**Quitado**
- Los reportes separados `CambiosClientes` y `VentasEstrella`: sus páginas quedaron en este reporte.

## [1.0] - 2026-11-21

Primera versión sobre las tablas silver y los agregados (`orders`, `customers`, `customers_history`,
`daily_sales_by_channel`, `sales_by_country`).
