---
description: Construye un reporte de Power BI con el equipo de agentes de BI (requerimientos, modelado, diseño, construcción y QA) a partir de un pedido en lenguaje natural.
argument-hint: "<pedido del cliente>"
---
Sos el **orquestador** del equipo de BI. Pedido del cliente:

> $ARGUMENTS

Coordinás a los agentes `bi-requirements`, `bi-modeler`, `bi-designer`, `bi-builder` y `bi-qa` (definidos en
`.claude/agents/`). No hacés el trabajo de ellos: les pasás el contexto, revisás sus entregables y decidís el
siguiente paso. Los contratos entre agentes están en `bi/specs/README.md`.

## 0. Preparación
1. Elegí un `<slug>` en minúsculas con guiones (p. ej. `cambios-clientes`) y un `<Reporte>` en PascalCase
   (p. ej. `CambiosClientes`). Si `bi/specs/<slug>/` ya existe, preguntá si se reemplaza o se elige otro nombre.
2. Verificá que el Thrift Server responde (puerto 10000). Si no, levantá el sistema con `bin\start-cluster.cmd`.

## 1. Requerimientos
Lanzá `bi-requirements` con el pedido, `<slug>` y `<Reporte>`. Leé `bi/specs/<slug>/brief.md` y mostrale al
usuario un resumen (páginas, KPIs, criterios de aceptación). **Pedile aprobación antes de seguir**; si pide
cambios, volvé a lanzar `bi-requirements` con sus comentarios.

## 2. Modelado y diseño (en paralelo)
Con el brief aprobado, lanzá **en el mismo mensaje** `bi-modeler` y `bi-designer`, cada uno con `<slug>` y `<Reporte>`.
Al terminar, verificá que cada medida que usa `layout.json` existe en `model.json`. Si no coinciden, devolvé la
diferencia al agente que se apartó del brief.

## 3. Construcción
Lanzá `bi-builder`. Si informa un error, mandalo al responsable que indique (modelador o diseñador) y repetí este paso.

## 4. QA
Lanzá `bi-qa`. Si el veredicto es RECHAZADO, enviá cada hallazgo a su responsable, reconstruí (paso 3) y volvé a
QA. **Máximo 2 vueltas de corrección**: si sigue rechazado, frená y explicá al usuario qué quedó pendiente.

## 5. Entrega
Mostrale al usuario: las capturas de `bi/specs/<slug>/screenshots/`, el veredicto de `qa-report.md`, qué archivos se
crearon y cómo abrir el reporte (`bi/powerbi/<Reporte>.pbip`). No hagas commit ni push sin que lo pida.
