# Cambios

![Claude Code](https://img.shields.io/badge/Claude%20Code-subagentes-D97757?logo=anthropic&logoColor=white)

Cada cambio del lakehouse (una tabla nueva, una columna, una regla de CDC, una métrica) se lleva de punta a punta
con el equipo de agentes y el comando `/deliver`. Los agentes no se hablan entre sí: se pasan los documentos de
la carpeta del cambio. La arquitectura completa está en [`docs/agents.md`](../docs/agents.md).

```
/deliver "Necesito analizar las ventas por tienda"
```

## Estructura de un cambio

```
changes/
├── README.md                 este archivo
├── _templates/               plantillas de cada documento
└── CHG-AAAA-NNN/             un cambio
    ├── request.md            data-product-analyst    alcance, SLA, criterios de aceptación  (G0: aprueba la persona)
    ├── design.md             data-architect          modelo, grafo, impacto, contratos
    ├── plan.md               data-architect          tareas → agente → archivos
    ├── reviews/
    │   ├── architecture.md   architecture-reviewer   G1
    │   ├── code.md           code-reviewer           G2
    │   └── data-tests.md     data-quality-engineer   G3
    └── status.md             delivery-lead           puerta actual, vueltas, decisiones
```

## Puertas (fase 1)

| Puerta | Valida | Se pasa con |
|---|---|---|
| G0 Alcance | La persona | `request.md` aprobado |
| G1 Diseño | `architecture-reviewer` | `reviews/architecture.md` APROBADO |
| G2 Código | `code-reviewer` | `reviews/code.md` APROBADO y `spark-pipelines dry-run` sin errores |
| G3 Datos | `data-quality-engineer` | `reviews/data-tests.md` APROBADO: pipeline desde cero con los lotes, `check-quality` y criterios del `request.md` |
| G4 Consumo | `bi-qa` (vía `/build-report`) | Solo si cambia una tabla que usa el reporte |

Máximo **2 vueltas de corrección** por puerta. Las tareas de bronze, plataforma, seguridad o release quedan
marcadas como *fase 3* y se escalan a la persona hasta que existan esos agentes.

## Identificador

`CHG-<año>-<número de 3 dígitos>`, correlativo por año (`CHG-2026-001`). La rama de trabajo es
`change/CHG-2026-001` y cada commit lleva el identificador.
