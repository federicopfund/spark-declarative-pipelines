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
                                                       sort: {field: "tabla.campo", direction} } ] } ],
      "field_names": { "tabla.campo": "Nombre visible" },
      "theme": "bi/design/LakehouseModern.Theme",      (opcional; este es el valor por defecto)
      "version": "1.2", "label": "Lakehouse Details" }  (opcional; version exige entrada en CHANGELOG.md)

Pasos: crea el reporte, lo enlaza al modelo local (byPath), aplica el tema del sistema de diseno, crea cada
pagina con su encabezado (banda con titulo, reporte, version y subtitulo), agrega los visuales, aplica
propiedades, borra la pagina por defecto, anota la version y valida (pbir validate --qa y theme validate).
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
PROJECT_ROOT = POWERBI_DIR.parents[1]
DEFAULT_THEME = "bi/design/LakehouseModern.Theme"

# Encabezado de pagina (bi/design/README.md): banda indigo de ancho completo en y=0..80
HEADER = {"height": 80, "background": "#312E81", "title_color": "#FFFFFF", "meta_color": "#C7D2FE",
          "title_size": "20pt", "meta_size": "10pt"}
PAGE_WIDTH = 1280


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


def literal(value: str) -> dict:
    return {"expr": {"Literal": {"Value": value}}}


def solid(color: str) -> dict:
    return {"solid": {"color": literal(f"'{color}'")}}


def check_version(layout: dict, layout_path: Path) -> None:
    """Un reporte versionado necesita la entrada '## [x.y]' de su version en el CHANGELOG.md del spec."""
    version = layout.get("version")
    if not version:
        return
    changelog = layout_path.parent / "CHANGELOG.md"
    if not changelog.exists() or f"## [{version}]" not in changelog.read_text(encoding="utf-8"):
        sys.exit(f"Version {version} sin entrada '## [{version}]' en {changelog}")


def apply_theme(pbir: Pbir, report_dir: Path, theme: str) -> None:
    """Aplica el tema del sistema de diseno y deja solo ese tema en el reporte."""
    theme_dir = (PROJECT_ROOT / theme).resolve()
    if not theme_dir.is_dir():
        sys.exit(f"No existe el tema {theme_dir}")
    pbir("theme", "build", str(theme_dir), "-o", report_dir.name, "-f")
    report_json = report_dir / "definition" / "report.json"
    data = json.loads(report_json.read_text(encoding="utf-8"))
    active = data["themeCollection"]["customTheme"]["name"]
    # El baseTheme que agrega pbir apunta a SharedResources que el reporte no incluye
    data["themeCollection"].pop("baseTheme", None)
    report_json.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for old in (report_dir / "StaticResources" / "RegisteredResources").glob("*.json"):
        if old.name != active:
            old.unlink()
    print(f"    [OK] tema {active}")


def style_headers(report_dir: Path, layout: dict) -> None:
    """Convierte el titulo de cada pagina en la banda de encabezado: titulo + reporte, version y subtitulo."""
    pages = {p["name"]: p for p in layout["pages"]}
    label = layout.get("label", layout["report"])
    for page_json in (report_dir / "definition" / "pages").glob("*/page.json"):
        page = pages.get(json.loads(page_json.read_text(encoding="utf-8")).get("displayName"))
        if page is None:
            continue
        meta = " · ".join(x for x in (label, f"v{layout['version']}" if layout.get("version") else None,
                                           page.get("subtitle")) if x)
        for visual_json in page_json.parent.glob("visuals/*/visual.json"):
            vis = json.loads(visual_json.read_text(encoding="utf-8"))
            if vis["visual"]["visualType"] != "textbox":
                continue
            vis["position"].update({"x": 0, "y": 0, "width": PAGE_WIDTH, "height": HEADER["height"]})
            vis["visual"]["objects"]["general"][0]["properties"]["paragraphs"] = [
                {"textRuns": [{"value": page["name"], "textStyle": {
                    "fontFamily": "Segoe UI Semibold", "fontSize": HEADER["title_size"], "color": HEADER["title_color"]}}]},
                {"textRuns": [{"value": meta, "textStyle": {
                    "fontFamily": "Segoe UI", "fontSize": HEADER["meta_size"], "color": HEADER["meta_color"]}}]},
            ]
            vis["visual"]["visualContainerObjects"].update({
                "background": [{"properties": {"show": literal("true"), "color": solid(HEADER["background"]),
                                               "transparency": literal("0D")}}],
                "padding": [{"properties": {"top": literal("10D"), "bottom": literal("0D"),
                                            "left": literal("24D"), "right": literal("24D")}}],
                "dropShadow": [{"properties": {"show": literal("false")}}],
            })
            visual_json.write_text(json.dumps(vis, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def build(layout: dict, layout_path: Path, replace: bool) -> int:
    pbir = Pbir()
    report, model = layout["report"], layout["model"]
    report_dir = POWERBI_DIR / f"{report}.Report"
    check_version(layout, layout_path)

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
    apply_theme(pbir, report_dir, layout.get("theme", DEFAULT_THEME))

    for page in layout["pages"]:
        name = page["name"]
        page_path = f"{report}.Report/{name}.Page"
        pbir("add", "page", page_path, "-n", name)
        # El titulo que crea pbir pasa a ser la banda de encabezado (style_headers le da el estilo)
        pbir("visuals", "position", f"{page_path}/Title.Visual", "--x", "0", "--y", "0",
             "--width", str(PAGE_WIDTH), "--height", str(HEADER["height"]))

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

    # Nombres de negocio para columnas tecnicas en todo el reporte (encabezados de tablas, segmentadores, ejes)
    for field, display_name in layout.get("field_names", {}).items():
        pbir("fields", "rename", f"{report}.Report", field, display_name)
    if layout.get("field_names"):
        print(f"    [OK] {len(layout['field_names'])} nombres de campo")

    style_headers(report_dir, layout)
    if layout.get("version"):
        pbir("add", "annotation", f"{report}.Report", "--name", "version", "--value", layout["version"])
        print(f"    [OK] version {layout['version']}")

    result = pbir("validate", f"{report}.Report", "--qa", check=False)
    print(result)
    theme_result = pbir("theme", "validate", f"{report}.Report", check=False)
    print(theme_result)
    return 0 if "validation passed" in result and "validation passed" in theme_result else 1


def main() -> None:
    # La consola de Windows usa cp1252 y pbir imprime simbolos Unicode (✓, tablas)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("layout", type=Path, help="layout.json del diseñador")
    parser.add_argument("--replace", action="store_true", help="borrar y reconstruir si el reporte ya existe")
    args = parser.parse_args()
    layout = json.loads(args.layout.read_text(encoding="utf-8"))
    sys.exit(build(layout, args.layout, args.replace))


if __name__ == "__main__":
    main()
