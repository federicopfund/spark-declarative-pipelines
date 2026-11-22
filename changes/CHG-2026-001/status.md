# Status: CHG-2026-001 · Resumen de compras por cliente (piloto)

- **Rama:** `change/CHG-2026-001`
- **Puerta actual:** FRENADO (G3 vuelta 1 rechazada por el ambiente)

| Puerta | Estado | Vuelta | Evidencia | Fecha |
|---|---|---|---|---|
| G0 Alcance | APROBADO | — | `request.md` (la persona aprobó, incluido el nombre del cliente) | 2026-11-22 |
| G1 Diseño | APROBADO | 1 | `reviews/architecture.md` (6 hallazgos menores) | 2026-11-22 |
| G2 Código | APROBADO | 1 | `reviews/code.md` (dry-run COMPLETED, 1 hallazgo menor) | 2026-11-22 |
| G3 Datos | RECHAZADO | 1 | `reviews/data-tests.md` (pipeline colgado en el lote 1; 0/11 controles, 0/8 criterios) | 2026-11-22 |
| G4 Consumo | NO APLICA / PENDIENTE | 0 | `bi/specs/retail-lakehouse/qa-report.md` | |

## Decisiones

- 2026-11-22: la persona aprobó incluir el nombre del cliente (G0).
- 2026-11-22: la persona decidió registrar T7 (datos personales, fase 3) y T8 (contrato, fase 2) como deuda y seguir.
- 2026-11-22: el arquitecto incorporó los hallazgos menores 2 a 5 de G1 (control 11, riesgos en design.md).

## Deuda registrada (hallazgos menores)

- T7: clasificar `name` de `agg_sales_by_customer` como dato personal (security-governance, fase 3). Hallazgo G1-6.
- T8: contrato de `agg_sales_by_customer` (fase 2, no existe `contracts/`).
- G1-1: referencias a actualizar al cierre (architecture.md:372, README.md:122 y 176, agents.md:357); README sin dueño en agents.md sección 8.
- G2-1: `quality/11_agg_sales_by_customer_metrics.sql:23` puede dar falsos positivos de 0.01 por doble redondeo de `avg(decimal)` con más de ~20 000 pedidos por cliente.
- Diseño: `agg_sales_by_country` y `agg_daily_sales_by_channel` no tienen `_loaded_at`.

## Escalado a la persona

- 2026-11-22: la persona decidió **frenar el piloto** después de G3 vuelta 1. Quedan en la rama el diseño, el código (G2 aprobado) y los controles 08 a 11, sin verificación con datos. Cierre (T6) no ejecutado.

- 2026-11-22, G3 vuelta 1: la corrida del lote 1 quedó colgada en `customers_history` (código existente). El orquestador confirmó por el volcado de hilos del ejecutor 0 que la tarea TID 7 está trabada en `ExecutorClassLoader` / `FileDownloadChannel`: es el cuelgue intermitente conocido del ambiente local, no el cambio. Remedio operativo (plataforma, fase 3): detener el proceso del ejecutor trabado y repetir G3 desde cero (vuelta 2).
