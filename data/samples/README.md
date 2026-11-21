# Datos de ejemplo

Cada lote simula lo que llega a `data/landing/` en un momento. Se aterriza con `bin\land-batch.cmd -Batch N`.

| Lote | customers_cdc | Qué ejercita |
|---|---|---|
| batch-001 | 5 INSERT (clientes 1–5, version 1) | carga inicial |
| batch-002 | cliente 2 UPDATE v2 (cambia país) · cliente 4 DELETE v2 · cliente 3 UPDATE **v3** · cliente 6 INSERT · cliente 2 v2 **repetido** | update, delete, duplicado |
| batch-003 | cliente 3 UPDATE **v2** (llega tarde) · cliente 1 UPDATE v2 · cliente 4 INSERT v3 (vuelve) | evento desordenado, reinserción tras delete |

Resultado esperado de `customers` (SCD1) después de los 3 lotes:

| customer_id | country | por qué |
|---|---|---|
| 1 | Argentina (email nuevo) | v2 gana sobre v1 |
| 2 | Argentina | v2 gana; el duplicado no cambia nada |
| 3 | Brasil | v3 gana; la v2 que llegó tarde se descarta |
| 4 | Mexico | DELETE en v2, reinsertado en v3 |
| 5 | Peru | sin cambios |
| 6 | Chile | insert del lote 2 |
