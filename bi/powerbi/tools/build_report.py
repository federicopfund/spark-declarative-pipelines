"""Construye un reporte de Power BI (PBIR) a partir de un layout.json, con el CLI pbir.

Lo usa el agente bi-builder. El modelo semantico tiene que existir antes (generate_model.py), porque
pbir valida cada campo de los visuales contra el modelo.

Uso (desde la raiz del proyecto):
    .venv\\Scripts\\python bi\\powerbi\\tools\\build_report.py bi\\specs\\<reporte>\\layout.json [--replace]

Formato del layout (ver bi/specs/README.md):
    { "report": "<Nombre>", "model": "<Nombre del SemanticModel>",
      "pages": [ { "name": "<Pagina>", "visuals": [ { visual_type, name, x, y, width, height, title,
                                                       fields: {Rol: "tabla.campo" | [..]},
                                                       properties: {"categoryAxis.axisType": "Categorical"},
                                                       filters: [{field, type, operator, values}],
                                                       sort: {field: "tabla.campo", direction} } ] } ] }

Pasos: crea el reporte, lo enlaza al modelo local (byPath), crea cada pagina con su titulo, agrega los
visuales, aplica propiedades, borra la pagina por defecto y valida (pbir validate --qa).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

POWERBI_DIR = Path(__file__).resolve().parents[1]
TITLE_Y, TITLE_HEIGHT = 8, 78  # con menos alto, el titulo de 24pt muestra barra de desplazamiento


def find_pbir() -> str:
    """pbir desde la variable PBIR, el venv dedicado o el PATH."""
    candidates = [os.environ.get("PBIR"), str(Path.home() / ".venvs" / "pbir" / "Scripts" / "pbir.exe")]
    for c in candidates:
        if c and Path(c).exists():
            return c
    found = shutil.which("pbir")
    if not found:
        sys.exit("pbir no encontrado: instalar con 'pip install pbir-cli' o definir la variable PBIR")
    return found


class Pbir:
    """Ejecuta pbir dentro de bi/powerbi y corta ante el primer error."""

    def __init__(self) -> None:
        self.exe = find_pbir()

    def __call__(self, *args: str, check: bool = True) -> str:
        proc = subprocess.run([self.exe, "-q", *args], cwd=POWERBI_DIR, capture_output=True)
        out = (proc.stdout + proc.stderr).decode("utf-8", errors="replace").strip()
        if check and proc.returncode != 0:
            sys.exit(f"pbir {' '.join(args)}\n{out}")
        return out


def visuals_json(visuals: list[dict]) -> Path:
    """Archivo temporal para --from-json, en ASCII: pbir lee el JSON con la codificacion de Windows."""
    specs = [{k: v for k, v in vis.items() if k not in ("properties", "filters", "sort")} for vis in visuals]
    fd, name = tempfile.mkstemp(suffix=".json")
    os.close(fd)  # en Windows, un archivo abierto no se puede borrar despues
    tmp = Path(name)
    tmp.write_text(json.dumps(specs, ensure_ascii=True, indent=2), encoding="ascii")
    return tmp


def default_page_folders(report_dir: Path) -> list[str]:
    """Carpetas de pagina cuyo displayName es el de la pagina por defecto de pbir ('Page 1')."""
    pages = report_dir / "definition" / "pages"
    found = []
    for page_json in pages.glob("*/page.json"):
        if json.loads(page_json.read_text(encoding="utf-8")).get("displayName") == "Page 1":
            found.append(page_json.parent.name)
    return found


def add_filter(pbir: Pbir, visual_path: str, flt: dict) -> None:
    """Filtro de nivel visual: {"field": "tabla.campo", "type": "Advanced", "operator": "GreaterThan", "values": [1]}."""
    table, _, field = flt["field"].partition(".")
    args = ["add", "filter", table, field, "-v", visual_path, "--type", flt.get("type", "Categorical")]
    if flt.get("operator"):
        args += ["--operator", flt["operator"]]
    for value in flt.get("values", []):
        args += ["--values", str(value)]
    pbir(*args)


def build(layout: dict, replace: bool) -> int:
    pbir = Pbir()
    report, model = layout["report"], layout["model"]
    report_dir = POWERBI_DIR / f"{report}.Report"

    if not (POWERBI_DIR / f"{model}.SemanticModel").exists():
        sys.exit(f"No existe {model}.SemanticModel: generar el modelo primero (generate_model.py)")
    if report_dir.exists():
        if not replace:
            sys.exit(f"{report_dir.name} ya existe; usar --replace para reconstruirlo")
        shutil.rmtree(report_dir)
        (POWERBI_DIR / f"{report}.pbip").unlink(missing_ok=True)

    print(f"==> {report}.Report (modelo {model})")
    pbir("new", "report", f"{report}.Report", "--thick")
    pbir("report", "rebind", f"{report}.Report", "--local", f"../{model}.SemanticModel")

    for page in layout["pages"]:
        name = page["name"]
        page_path = f"{report}.Report/{name}.Page"
        pbir("add", "page", page_path, "-n", name)
        pbir("visuals", "position", f"{page_path}/Title.Visual", "--y", str(TITLE_Y), "--height", str(TITLE_HEIGHT))

        tmp = visuals_json(page["visuals"])
        try:
            pbir("add", "visual", page_path, "--from-json", str(tmp))
        finally:
            tmp.unlink(missing_ok=True)

        for vis in page["visuals"]:
            visual_path = f"{page_path}/{vis['name']}.Visual"
            for prop, value in vis.get("properties", {}).items():
                pbir("set", f"{visual_path}.{prop}", "--value", str(value))
            for flt in vis.get("filters", []):
                add_filter(pbir, visual_path, flt)
            if vis.get("sort"):
                sort = vis["sort"]
                pbir("visuals", "sort", visual_path, "--field", sort["field"],
                     "--direction", sort.get("direction", "Ascending"))
        print(f"    [OK] pagina {name}: {len(page['visuals'])} visuales")

    for folder in default_page_folders(report_dir):
        pbir("rm", f"{report}.Report/{folder}.Page", "-f")

    result = pbir("validate", f"{report}.Report", "--qa", check=False)
    print(result)
    return 0 if "validation passed" in result else 1


def main() -> None:
    # La consola de Windows usa cp1252 y pbir imprime simbolos Unicode (✓, tablas)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("layout", type=Path, help="layout.json del diseñador")
    parser.add_argument("--replace", action="store_true", help="borrar y reconstruir si el reporte ya existe")
    args = parser.parse_args()
    layout = json.loads(args.layout.read_text(encoding="utf-8"))
    sys.exit(build(layout, args.replace))


if __name__ == "__main__":
    main()
