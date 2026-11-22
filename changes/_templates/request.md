# Request: CHG-AAAA-NNN · <título corto>

- **Pedido original:** "<texto literal de la persona>"
- **Fecha:** AAAA-MM-DD
- **Tipo:** tabla nueva · cambio de tabla · regla de negocio · métrica · corrección
- **Estado G0:** PENDIENTE / APROBADO (fecha) / RECHAZADO

## Objetivo de negocio

Quién lo usa y qué decisión permite tomar (2 a 4 líneas).

## Preguntas de negocio

| # | Pregunta | Dato que la responde | Fuente actual |
|---|---|---|---|
| P1 | | | `retail.<tabla>` |

## Fuentes y consumidores

- Fuentes: tablas existentes o datos nuevos (si son datos nuevos de origen, es trabajo de bronze: *fase 3*).
- Consumidores: reporte `RetailLakehouse`, exportaciones, otros.

## Requisitos no funcionales

| Requisito | Valor |
|---|---|
| Frescura (SLA) | p. ej. disponible después de cada corrida del pipeline |
| Volumen esperado | filas por lote |
| Histórico | SCD1 / SCD2 / sin historia |
| Datos personales | ninguno / cuáles |

## Criterios de aceptación

Verificables con una consulta después de correr el pipeline desde cero con los lotes de ejemplo.

- [ ] CA1: `retail.<tabla>` tiene N filas después del lote 3.
- [ ] CA2: <regla de negocio con un valor esperado concreto>.
- [ ] CA3: todos los controles de calidad existentes siguen pasando.

## Fuera de alcance

## Supuestos
