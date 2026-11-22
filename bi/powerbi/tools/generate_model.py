"""Genera un modelo semantico de Power BI (TMDL) a partir de una especificacion JSON.

Cada tabla lee de Spark por el Thrift Server con el conector nativo de Power BI:
    ApacheSpark.Tables(SparkServer, 0 /* SparkProtocol.Standard */)
y fija los tipos en Power Query para que coincidan con los dataType del modelo.

Uso (desde la raiz del proyecto):
    .venv\\Scripts\\python bi\\powerbi\\tools\\generate_model.py                         # RetailLakehouse
    .venv\\Scripts\\python bi\\powerbi\\tools\\generate_model.py --spec bi\\specs\\<reporte>\\model.json

Formato de la especificacion (ver bi/specs/README.md):
    name, spark_server, database, culture, logical_id (opcional),
    tables: { <tabla Spark>: { description, columns[], calculated[], measures[] } },
    relationships: [ { from: "tabla.columna", to: "tabla.columna" } ]

Escribe <name>.SemanticModel junto a esta carpeta (o en --out). Los lineageTag son deterministicos
(uuid5), asi que regenerar no cambia la identidad de los objetos.
"""

from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path

POWERBI_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = POWERBI_DIR.parents[1]
DEFAULT_SPEC = PROJECT_ROOT / "bi" / "specs" / "retail-lakehouse" / "model.json"
NS = uuid.UUID("6d1c3c2e-6a4f-4d55-9a49-1f6f0c1d2b7a")

# dataType de la especificacion -> (dataType TMDL, tipo M)
TYPES = {
    "string": ("string", "type text"),
    "int64": ("int64", "Int64.Type"),
    "double": ("double", "type number"),
    "decimal": ("decimal", "Currency.Type"),
    "boolean": ("boolean", "type logical"),
    "dateTime": ("dateTime", "type datetime"),
    "date": ("dateTime", "type date"),  # TMDL guarda fechas como dateTime; M las tipa como date
}
SUMMARIZE = {"none", "sum", "min", "max", "count", "average", "distinctCount"}


class SpecError(ValueError):
    """La especificacion del modelo es invalida."""


def tag(*parts: str) -> str:
    """lineageTag deterministico a partir del tipo y nombre del objeto."""
    return str(uuid.uuid5(NS, "/".join(parts)))


def q(name: str) -> str:
    """Comillas TMDL solo cuando hacen falta."""
    simple = name.replace("_", "a").isalnum() and not name[0].isdigit()
    return name if simple else "'" + name.replace("'", "''") + "'"


# ---------------------------------------------------------------------------------------------
# Validacion
# ---------------------------------------------------------------------------------------------


def validate(spec: dict) -> None:
    """Falla temprano con un mensaje claro, antes de escribir archivos."""
    for key in ("name", "spark_server", "database", "tables"):
        if not spec.get(key):
            raise SpecError(f"falta '{key}'")
    columns_by_table: dict[str, set[str]] = {}
    for table, t in spec["tables"].items():
        if not t.get("columns"):
            raise SpecError(f"{table}: sin columnas")
        names = set()
        for c in t["columns"]:
            if c.get("type") not in TYPES:
                raise SpecError(f"{table}.{c.get('name')}: tipo '{c.get('type')}' no soportado {sorted(TYPES)}")
            if c.get("summarize", "none") not in SUMMARIZE:
                raise SpecError(f"{table}.{c['name']}: summarize '{c['summarize']}' invalido")
            names.add(c["name"])
        names |= {c["name"] for c in t.get("calculated", [])}
        columns_by_table[table] = names
        for m in t.get("measures", []):
            if m["name"] in names:
                raise SpecError(f"{table}: la medida '{m['name']}' choca con una columna")
    for r in spec.get("relationships", []):
        for side in ("from", "to"):
            table, _, column = r[side].partition(".")
            if column not in columns_by_table.get(table, set()):
                raise SpecError(f"relacion {r}: '{r[side]}' no existe en el modelo")


# ---------------------------------------------------------------------------------------------
# TMDL
# ---------------------------------------------------------------------------------------------


def table_tmdl(name: str, t: dict, database: str) -> str:
    """Una tabla: medidas, columnas, columnas calculadas y particion M contra Spark."""
    out = [f"/// {t['description']}", f"table {q(name)}"]
    if t.get("data_category"):
        out.append(f"\tdataCategory: {t['data_category']}")  # "Time" marca la tabla de fechas
    out += [f"\tlineageTag: {tag('table', name)}", ""]

    for m in t.get("measures", []):
        out += [
            f"\t/// {m['description']}",
            f"\tmeasure {q(m['name'])} = {m['expression']}",
            f"\t\tformatString: {m['format']}",
        ]
        if m.get("folder"):
            out.append(f"\t\tdisplayFolder: {m['folder']}")
        out += [
            f"\t\tlineageTag: {tag('measure', name, m['name'])}",
            "",
        ]

    for c in t["columns"]:
        out.append(f"\tcolumn {q(c['name'])}")
        out.append(f"\t\tdataType: {TYPES[c['type']][0]}")
        if c.get("hidden"):
            out.append("\t\tisHidden")  # claves tecnicas: se usan en relaciones, no en visuales
        if c.get("key"):
            out.append("\t\tisKey")
        if c.get("format"):
            out.append(f"\t\tformatString: {c['format']}")
        if c.get("folder"):
            out.append(f"\t\tdisplayFolder: {c['folder']}")
        out += [
            f"\t\tlineageTag: {tag('column', name, c['name'])}",
            f"\t\tsummarizeBy: {c.get('summarize', 'none')}",
            f"\t\tsourceColumn: {c['name']}",
        ]
        if c.get("sort_by"):
            out.append(f"\t\tsortByColumn: {q(c['sort_by'])}")  # p. ej. nombre del mes ordenado por numero
        out += [
            "",
            "\t\tannotation SummarizationSetBy = Automatic",
            "",
        ]
        if c["type"] == "date":
            # Sin esta anotacion Power BI trata la columna como fecha y hora (ejes por hora, no por dia)
            out += ["\t\tannotation UnderlyingDateTimeDataType = Date", ""]

    for c in t.get("calculated", []):
        out += [
            f"\t/// {c['description']}",
            f"\tcolumn {q(c['name'])} = {c['expression']}",
            f"\t\tdataType: {TYPES[c.get('type', 'string')][0]}",
            f"\t\tlineageTag: {tag('column', name, c['name'])}",
            "\t\tsummarizeBy: none",
            "",
            "\t\tannotation SummarizationSetBy = Automatic",
            "",
        ]

    types = ", ".join(f'{{"{c["name"]}", {TYPES[c["type"]][1]}}}' for c in t["columns"])
    source = t.get("source", name)
    out += [
        f"\tpartition {q(name)} = m",
        "\t\tmode: import",
        "\t\tsource =",
        "\t\t\t\tlet",
        "\t\t\t\t    Source = ApacheSpark.Tables(SparkServer, 0, [BatchSize = null]),",
        f'\t\t\t\t    Data = Source{{[Schema = "{database}", Item = "{source}"]}}[Data],',
        f"\t\t\t\t    Typed = Table.TransformColumnTypes(Data, {{{types}}})",
        "\t\t\t\tin",
        "\t\t\t\t    Typed",
        "",
        "\tannotation PBI_ResultType = Table",
        "",
    ]
    return "\n".join(out)


def write(path: Path, text: str) -> None:
    """UTF-8 sin BOM y finales CRLF, como los escribe Power BI Desktop."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.replace("\r\n", "\n").replace("\n", "\r\n").encode("utf-8"))


def generate(spec: dict, model_dir: Path) -> None:
    """Escribe la carpeta <name>.SemanticModel completa."""
    d = model_dir / "definition"
    name = spec["name"]
    tables = spec["tables"]

    write(model_dir / "definition.pbism", """{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",
  "version": "4.2",
  "settings": {}
}
""")
    write(model_dir / ".platform", f"""{{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
  "metadata": {{
    "type": "SemanticModel",
    "displayName": "{name}"
  }},
  "config": {{
    "version": "2.0",
    "logicalId": "{spec.get('logical_id') or tag('item', name)}"
  }}
}}
""")
    write(d / "database.tmdl", "database\n\tcompatibilityLevel: 1601\n\tcompatibilityMode: powerBI\n")

    culture = spec.get("culture", "es-AR")
    refs = "\n".join(f"ref table {q(t)}" for t in tables)
    order = ",".join(f'"{t}"' for t in ["SparkServer", *tables])
    write(d / "model.tmdl", f"""model Model
\tculture: {culture}
\tdefaultPowerBIDataSourceVersion: powerBI_V3
\tdiscourageImplicitMeasures
\tsourceQueryCulture: {culture}
\tdataAccessOptions
\t\tlegacyRedirects
\t\treturnErrorValuesAsNull

annotation __PBI_TimeIntelligenceEnabled = 0

annotation PBI_QueryOrder = [{order}]

{refs}
""")

    # Parametro: servidor Thrift JDBC/ODBC de Spark (host y puerto), protocolo Standard
    write(d / "expressions.tmdl", f"""expression SparkServer = "{spec['spark_server']}" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]
\tlineageTag: {tag('expression', 'SparkServer')}

\tannotation PBI_ResultType = Text
""")

    rels = []
    for r in spec.get("relationships", []):
        f_t, _, f_c = r["from"].partition(".")
        t_t, _, t_c = r["to"].partition(".")
        rels += [
            f"relationship {tag('rel', f_t, f_c, t_t, t_c)}",
            f"\tfromColumn: {q(f_t)}.{q(f_c)}",
            f"\ttoColumn: {q(t_t)}.{q(t_c)}",
            "",
        ]
    write(d / "relationships.tmdl", "\n".join(rels))

    for table, t in tables.items():
        write(d / "tables" / f"{table}.tmdl", table_tmdl(table, t, spec["database"]))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC, help="model.json (default: RetailLakehouse)")
    parser.add_argument("--out", type=Path, help="carpeta destino (default: bi/powerbi/<name>.SemanticModel)")
    args = parser.parse_args()

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    validate(spec)
    model_dir = args.out or POWERBI_DIR / f"{spec['name']}.SemanticModel"
    generate(spec, model_dir)

    print(f"OK: {model_dir}")
    for p in sorted(model_dir.rglob("*")):
        if p.is_file() and ".pbi" not in p.parts:
            print("   ", p.relative_to(model_dir.parent))


if __name__ == "__main__":
    main()
