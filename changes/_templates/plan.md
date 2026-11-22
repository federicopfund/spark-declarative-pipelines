# Plan: CHG-AAAA-NNN

Cada tarea tiene un único responsable y solo toca archivos de su propiedad (`docs/agents.md`, sección 8).

| # | Tarea | Responsable | Archivos | Depende de | Hecho cuando |
|---|---|---|---|---|---|
| T1 | Controles de calidad de `<tabla>` | data-quality-engineer | `pipelines/retail_lakehouse/quality/NN_<tabla>_<regla>.sql` | — | Archivo con `-- check:` y sin filas esperadas |
| T2 | Crear `<tabla>` | transformation-engineer | `pipelines/retail_lakehouse/transformations/gold/sql/…` | — | Dry-run sin errores |
| T3 | Actualizar `docs/data-model.md` | data-architect | `docs/data-model.md` | T2 | Tabla documentada |

Tareas fuera de los agentes de la fase 1 (bronze, plataforma, seguridad, release): marcar *fase 3 · escalar*.
