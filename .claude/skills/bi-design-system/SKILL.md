---
name: bi-design-system
description: Sistema de diseño LakehouseModern del equipo de BI para el reporte único RetailLakehouse. Tokens de color y tipografía, grilla y arquetipos de página, componentes (encabezado, riel de filtros, tarjetas KPI, gráficos, tablas), reglas de redacción, accesibilidad y la rúbrica de calidad visual que usa QA. Cargar antes de diseñar, construir o revisar cualquier página del reporte.
---

# Sistema de diseño LakehouseModern

El reporte `RetailLakehouse` es **uno solo** y crece con cada pedido. Para que siga siendo coherente después de
diez iteraciones, todas las páginas comparten este sistema: el mismo tema, la misma grilla, los mismos componentes
y el mismo tono. Una página nueva tiene que parecer escrita por la misma mano que las anteriores.

- Tema: `bi/design/LakehouseModern.Theme/` (lo aplica `build_report.py`; no se edita desde un visual).
- Formato del layout: `bi/specs/README.md`.
- Ejemplo vivo: `bi/specs/retail-lakehouse/layout.json`.

## 1. Principios

1. **Una pregunta por visual, una idea por página.** Si un visual no responde una pregunta del brief, sobra.
2. **Jerarquía 3-30-300.** En 3 segundos se leen los KPI (fila superior). En 30, las tendencias y comparaciones
   (centro). En 300, el detalle (abajo o a la derecha).
3. **El dato es el protagonista.** Color solo para significar; el resto, neutros. Nada de bordes gruesos, fondos de
   colores ni efectos 3D. Las sombras son suaves y uniformes (las pone el tema).
4. **Formato en el tema, no en el visual.** Un visual solo lleva `properties` cuando el contenido lo exige
   (decimales, orden, eje categórico). Si dos visuales necesitan el mismo ajuste, va al tema.
5. **Consistencia sobre novedad.** Lo innovador está en la composición (riel de filtros, banda de encabezado,
   tarjetas aireadas, barras sin eje con etiqueta directa), no en inventar estilos por página.

## 2. Tokens

### Color

| Token | Valor | Uso |
|---|---|---|
| `brand-900` | `#312E81` | Banda de encabezado, valor de las tarjetas KPI, máximo de escalas |
| `brand-600` | `#4F46E5` | Serie principal, selección, enlaces |
| `brand-100` | `#EEF2FF` | Encabezado de tabla, filtros aplicados, mínimo de escalas |
| `ink-900` | `#1E293B` | Texto principal |
| `ink-700` | `#334155` | Títulos de visual, etiquetas de datos |
| `ink-500` | `#64748B` | Texto secundario, títulos de tarjeta, ejes (contraste ≥ 4,5:1 sobre blanco) |
| `line` | `#E2E8F0` | Bordes de contenedor, líneas de grilla |
| `canvas` | `#F5F6FA` | Fondo de la página |
| `surface` | `#FFFFFF` | Fondo de cada visual |
| `good` / `neutral` / `bad` | `#10B981` / `#F59E0B` / `#EF4444` | Solo semáforos y variaciones (nunca decorativo) |

Paleta categórica (en este orden, la aplica el tema): índigo `#4F46E5`, celeste `#0EA5E9`, ámbar `#F59E0B`,
esmeralda `#10B981`, rosa `#EC4899`, violeta `#8B5CF6`, pizarra `#64748B`, rojo `#EF4444`.

Reglas:
- Un gráfico de **una sola serie** va en `brand-600` (el tema ya lo hace en barras). No colorear por categoría.
- Más de **6 series** en un gráfico: agrupar en "Otros" o cambiar de visual.
- El mismo concepto tiene el mismo color en todas las páginas (p. ej. si "Web" es índigo en una página, lo es en todas).
- Nunca colores literales en `properties` salvo pedido explícito del brief; si hace falta un color nuevo, se agrega al tema.

### Tipografía (Segoe UI, la única familia)

| Rol | Fuente | Tamaño | Color |
|---|---|---|---|
| Título de página (banda) | Segoe UI Semibold | 20 pt | blanco |
| Metadatos de página (banda) | Segoe UI | 10 pt | `#C7D2FE` |
| Título de visual | Segoe UI Semibold | 11 pt | `ink-700` |
| Título de tarjeta KPI | Segoe UI Semibold | 10 pt | `ink-500` |
| Valor de tarjeta KPI | Segoe UI Semibold | 30 pt | `brand-900` |
| Ejes, leyendas, celdas | Segoe UI | 9–10 pt | `ink-500` / `ink-700` |

### Espaciado

Unidad base **20 px**: márgenes de página, separación entre visuales y ancho de las calles. Relleno interno de
cada visual 12 × 14 px y radio de esquina 12 px (los pone el tema).

## 3. Grilla y arquetipos de página

Lienzo de **1280 × 720**. La banda de encabezado ocupa `y = 0..80` y la crea el constructor con el nombre de la
página, el nombre del reporte, la versión y el `subtitle` de la página. Los visuales van en `y ≥ 100` y terminan en
`y + alto ≤ 710`, con `x ≥ 20` y `x + ancho ≤ 1260`.

Columnas útiles (zona principal de 980 px que empieza en `x = 280`, a la derecha del riel):

| Divisiones | Ancho de cada una | `x` |
|---|---|---|
| 1 | 980 | 280 |
| 2 | 480 | 280, 780 |
| 3 | 313 / 313 / 314 | 280, 613, 946 |
| 4 | 230 | 280, 530, 780, 1030 |
| 5 | 180 | 280, 480, 680, 880, 1080 |
| 2/3 + 1/3 | 640 + 320 | 280, 940 |

Sin riel (páginas de detalle a ancho completo) la zona va de `x = 20` a `1260` (1240 px).

### Arquetipo A — Resumen (por defecto)

```
y=0    ┌──────────────────────── banda: Página · Reporte · vX.Y · subtítulo ───────────────────────┐
y=100  │ riel │  KPI   │  KPI   │  KPI   │  KPI   │   ← fila de tarjetas, alto 120
       │ 240  ├────────────────────────────┬────────┤
y=240  │ fil- │  tendencia (2/3)           │ ranking│   ← alto 230
       │ tros ├─────────────┬──────────────┴────────┤
y=490  │      │  corte 1    │  corte 2              │   ← alto 220
y=710  └──────┴─────────────┴───────────────────────┘
```

### Arquetipo B — Análisis (una dimensión a fondo)
Riel + fila de KPI + un visual principal de 980 × 360 + una tabla de 980 × 230 (o dos visuales de 480 × 230).

### Arquetipo C — Detalle
Sin riel: segmentadores en una fila de 100 px de alto arriba (`y = 100`), y una tabla o matriz a ancho completo
hasta `y = 710`. Para listados de más de 10 filas, la tabla ocupa al menos 400 px de alto.

## 4. Componentes

### Banda de encabezado
La genera `build_report.py`; el diseñador solo aporta `subtitle` en cada página: una frase de 6 a 12 palabras que
dice **qué responde la página** ("Importe, pedidos y clientes por fecha, canal y país al comprar"). Sin punto final.

### Riel de filtros (`x = 20`, ancho 240)
- Todos los segmentadores de la página van en el riel, apilados con 20 px de separación, en orden de uso
  (primero el más usado).
- Alto: 200 para listas de hasta 5 valores; el resto hasta `y = 710` para listas largas (fechas, clientes).
- El título del visual nombra la dimensión ("Canal", "Año-mes"); el encabezado interno queda oculto (tema).
- Ocultar el miembro desconocido con un filtro sobre la clave (`<clave> GreaterThan 0`).
- La misma dimensión filtrada en dos páginas usa el mismo título y el mismo lugar del riel.

### Tarjeta KPI
- Fila superior, todas del mismo ancho y alto 120 (110 como mínimo). 4 por fila con riel; 5 como máximo.
- Título = nombre de la medida, sin repetirlo como etiqueta de categoría (el tema la oculta).
- Decimales con `labels.labelPrecision`: 0 para conteos, 2 para importes. Sin unidades abreviadas (tema).
- Orden de lectura: volumen → cantidad → personas → razón (Importe, Pedidos, Clientes, Ticket promedio).
- `pbir validate` avisa `VISUAL_UNDERSIZED` para tarjetas menores a 280 × 140: con el valor de 30 pt del tema, 180 × 120
  es correcto y el aviso se acepta (QA lo verifica en la captura).

### Tendencia (`lineChart`)
- Eje de fecha diario categórico (`categoryAxis.axisType: Categorical`), ordenado por la fecha ascendente.
- `valueAxis.start: 0`. Etiquetas de datos (`labels.show: true`) solo si hay 12 puntos o menos.
- Ancho mínimo 480. Área suave debajo de la línea (tema).

### Ranking y cortes (`clusteredBarChart`)
- Barras horizontales ordenadas de mayor a menor por la medida. Una serie, en `brand-600`.
- Sin eje de valores; etiqueta de dato al final de cada barra (tema). Mínimo 30 px por categoría:
  `alto ≥ 60 + 30 × categorías`. Más de 10 categorías: tabla o top N.

### Tabla (`tableEx`)
- Para detalle, no para comparar. Máximo 6 columnas; la primera es la que identifica la fila (cliente, pedido).
- Encabezados con nombres de negocio (`field_names`), fila Total solo si la columna suma (`total.totals`).
- Orden explícito con `sort`. Alto para todas las filas esperadas sin desplazamiento (≈ 28 px por fila + 40).

### Otros visuales
- `donutChart`/`pieChart`: solo partes de un todo con 2 a 4 categorías.
- `matrix`: cruces de dos dimensiones; `kpi`/`gauge`: solo con meta definida en el brief.
- `textbox`: notas metodológicas de una línea, en el pie de un visual, nunca como decoración.

## 5. Redacción

- Español rioplatense neutro, en mayúscula inicial: "Importe por canal", no "IMPORTE POR CANAL" ni "importe x canal".
- Título de visual = **medida + "por" + corte** ("Cambios por fecha"). Si responde una pregunta, puede ser la
  respuesta corta ("Web concentra las ventas") solo si el dato no cambia con los filtros.
- Nunca nombres técnicos visibles (`customer_sk`, `changed_at`): todo campo visible de una columna técnica va en `field_names`.
- Mismo concepto, misma palabra en todo el reporte (si es "País al comprar", no aparece también "País de compra").

## 6. Accesibilidad

- Contraste de texto ≥ 4,5:1 (≥ 3:1 para etiquetas de 14 pt o más). Los tokens `ink-*` ya cumplen; `#94A3B8`
  solo para texto decorativo.
- No codificar información solo con color: el valor también se lee en la etiqueta o la tabla.
- Orden de tabulación = orden de lectura: arriba a abajo, izquierda a derecha (lo da la posición en la grilla).

## 7. Rúbrica de calidad visual (la usa `bi-qa`)

Cada criterio se califica PASA / FALLA mirando las capturas a escala 2. **El reporte se aprueba con todos los
criterios bloqueantes (B) en PASA y al menos 8 de 10 en total.**

| # | Criterio | Tipo |
|---|---|---|
| D1 | Cada página usa un arquetipo (A, B o C) y respeta la grilla: márgenes de 20 px, sin superposiciones ni visuales fuera del lienzo | B |
| D2 | Banda de encabezado con nombre de página, reporte, versión vigente y subtítulo legible | B |
| D3 | Ningún texto cortado, con puntos suspensivos o con barra de desplazamiento inesperada (títulos, etiquetas, categorías, tarjetas) | B |
| D4 | Sin nombres técnicos visibles; títulos según la sección 5 | B |
| D5 | KPI en la fila superior, mismo tamaño, formato correcto (decimales, sin "K"/"M" inesperados) | B |
| D6 | Color con significado: una serie en índigo, mismos colores para los mismos conceptos en todas las páginas | — |
| D7 | Gráficos ordenados (fechas ascendentes, rankings descendentes) y con el visual adecuado para la pregunta | — |
| D8 | Segmentadores en el riel, sin miembro "Desconocido", con títulos consistentes entre páginas | — |
| D9 | Densidad equilibrada: ningún visual vacío o casi vacío ocupa más espacio que uno con más información | — |
| D10 | Coherencia con las páginas anteriores: la página nueva no introduce estilos, colores o tamaños propios | — |

Un hallazgo de diseño se asigna a `bi-designer` (layout) o, si el problema es del tema o de la banda, a
`bi-builder`, que lo reporta al orquestador (el tema se cambia en `bi/design/` y afecta a todas las páginas).
