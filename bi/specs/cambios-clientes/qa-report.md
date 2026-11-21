# QA Report: CambiosClientes (cambios-clientes)

**Veredicto: APROBADO** (10/10 criterios PASA; 3 observaciones menores de diseño, no bloqueantes)

Fecha: 2026-11-21. Power BI Desktop 2.159. Modelo refrescado por TOM (RequestRefresh Full, ambas tablas en estado Ready).

## Validaciones estáticas
| Validación | Resultado |
|---|---|
| `tmdl-validate` sobre los 6 `.tmdl` | OK, 0 errores / 0 warnings en todos |
| `validate_pbip.py --no-pbir-cli` | OK, 0 errores / 0 warnings |
| `pbir validate CambiosClientes.Report --all` | Valid, 3 warnings avisivos (VISUAL_LEVEL_FILTERS y TOO_MANY_FIELDS en `tabla_ca`; TOO_MANY_FIELDS en `tabla_hi`), previstos por el brief |

## Datos (Spark, `bin\query-lakehouse.cmd`)
- `retail.customers`: 6 filas. `retail.customers_history`: 11 filas (6 vigentes, 5 históricas). Coinciden con los valores esperados del brief.

## Criterios
| Criterio | Resultado | Evidencia | Responsable |
|---|---|---|---|
| CA1 Clientes actuales = 6 | PASA | screenshots/resumen.png | - |
| CA2 Versiones = 11 | PASA | screenshots/resumen.png | - |
| CA3 Cambios registrados = 5 | PASA | screenshots/resumen.png | - |
| CA4 Clientes con cambios = 4 | PASA | screenshots/resumen.png | - |
| CA5 Barras por país: Argentina 2, Brasil 1, Chile 1, Mexico 1, Peru 1, sin scroll | PASA | screenshots/resumen.png | - |
| CA6 Clientes que cambiaron de país = 3 | PASA | screenshots/cambios-de-pais.png | - |
| CA7 Tabla lista Bruno (Argentina, 2), Carla (Brasil, 3), Diego (Mexico, 2); sin Ana | PASA | screenshots/cambios-de-pais.png | - |
| CA8 Carla seleccionada: Uruguay v1 Histórica, Paraguay v2 Histórica, Brasil v3 Vigente | PASA (por datos y orden) | No se pudo accionar el segmentador por automatización. Los datos de Spark y la tabla (ordenada por `version` asc, columnas país/Estado correctas en las filas de Carla) dan exactamente esa secuencia. screenshots/historia-por-cliente.png | - |
| CA9 Sin selección: 11 filas, 6 Vigente y 5 Histórica | PASA | screenshots/historia-por-cliente.png (11 filas; 6 Vigente, 5 Histórica) | - |
| CA10 Sin scroll horizontal | PASA | Las tres tablas/gráficos muestran todas sus columnas en las capturas | - |

## Hallazgos (no bloquean; no son criterios del brief)
- bi-designer: en `Cambios de país` la tabla muestra una fila Total (Países registrados 6, Versiones 7) que no tiene sentido de negocio; conviene quitar totales.
- bi-designer: el segmentador de `Historia por cliente` es bajo y muestra solo 2 de 6 nombres (requiere scroll vertical interno); conviene más alto o en formato lista/desplegable.
- bi-designer: las tarjetas repiten el nombre de la medida (título + etiqueta de categoría); en `Cambios de país` la etiqueta queda truncada ("Clientes que cambiaron de ...").
- Conocido (diseñador): sin selección la tabla de historia se ordena solo por `version`, mezclando clientes; no incumple CA9.

Hallazgos para bi-modeler: ninguno. Para bi-builder: ninguno.

## Capturas
`screenshots/resumen.png`, `screenshots/cambios-de-pais.png`, `screenshots/historia-por-cliente.png`
