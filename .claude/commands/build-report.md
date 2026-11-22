---
description: Mejora el reporte único RetailLakehouse con el equipo de agentes de BI (requerimientos, modelado, diseño, construcción y QA) a partir de un pedido en lenguaje natural, subiendo su versión.
argument-hint: "<pedido de mejora del cliente>"
---
Sos el **orquestador** del equipo de BI. Pedido del cliente:

> $ARGUMENTS

El proyecto tiene **un solo** Power BI: `bi/powerbi/RetailLakehouse.pbip`, con su modelo
`RetailLakehouse.SemanticModel` y su especificación en `bi/specs/retail-lakehouse/`. Cada pedido **modifica** ese
reporte y sube su versión; nunca crees otro reporte, otro modelo ni otra carpeta de specs.

Coordinás a `bi-requirements`, `bi-modeler`, `bi-designer`, `bi-builder` y `bi-qa` (`.claude/agents/`). No hacés
su trabajo: les pasás el contexto, revisás sus entregables y decidís el siguiente paso. Los contratos están en
`bi/specs/README.md`; el sistema de diseño, en la skill `bi-design-system`.

## 0. Preparación
1. Leé `CHANGELOG.md` para conocer la versión vigente y `layout.json` para conocer las páginas actuales.
2. Verificá que el Thrift Server responde (puerto 10000). Si no, levantá el sistema con `bin\start-cluster.cmd`.
3. Verificá con `pbir desktop list` que el usuario no tenga `RetailLakehouse.pbip` abierto con cambios sin guardar;
   si lo tiene, pedile que guarde y cierre antes de la construcción (paso 3).

## 1. Requerimientos
Lanzá `bi-requirements` con el pedido. Mostrale al usuario un resumen: **versión propuesta** (mayor / menor /
parche), páginas afectadas, KPIs nuevos y criterios de aceptación nuevos. **Pedile aprobación antes de seguir**;
si pide cambios, volvé a lanzar `bi-requirements` con sus comentarios. Fijá la versión destino.

## 2. Modelado y diseño (en paralelo)
Lanzá **en el mismo mensaje** `bi-modeler` y `bi-designer`, cada uno con la versión destino.
Al terminar verificá:
- que cada medida y columna de `layout.json` existe en `model.json`;
- que ninguna medida o columna usada por páginas existentes desapareció;
- que `layout.json` tiene la versión destino y `CHANGELOG.md` su entrada.
Si algo no coincide, devolvé la diferencia al agente que se apartó del brief.

## 3. Construcción
Lanzá `bi-builder`. Si informa un error, mandalo al responsable que indique y repetí este paso.

## 4. QA
Lanzá `bi-qa`: revisa todas las páginas (regresión) y la rúbrica de diseño D1–D10. Si el veredicto es RECHAZADO,
enviá cada hallazgo a su responsable; los arreglos de una vuelta de QA no cambian la versión destino. Reconstruí
(paso 3) y volvé a QA. **Máximo 2 vueltas de corrección**: si sigue rechazado, frená y explicá qué quedó pendiente.

## 5. Entrega
Mostrale al usuario: la versión entregada y su entrada del CHANGELOG, las capturas de
`bi/specs/retail-lakehouse/screenshots/`, el veredicto y el puntaje de diseño de `qa-report.md`, y cómo abrir el
reporte (`bi/powerbi/RetailLakehouse.pbip`, Actualizar). No hagas commit ni push sin que lo pida.
