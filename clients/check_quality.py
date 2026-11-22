"""Controles de calidad del modelo dimensional, por Spark Connect.

Cada archivo de ``pipelines/retail_lakehouse/quality/*.sql`` es un control: una consulta que devuelve las
filas que violan una regla. Sin filas = PASA. La primera linea ``-- check: ...`` describe la regla.

    bin\\check-quality.cmd              todos los controles
    bin\\check-quality.cmd 01 05        solo los que empiezan con esos prefijos

Sale con codigo 1 si algun control falla, para poder usarlo despues de cada ejecucion del pipeline.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pyspark.sql import SparkSession

QUALITY_DIR = Path(__file__).resolve().parents[1] / "pipelines" / "retail_lakehouse" / "quality"


def description(sql: str) -> str:
    """Texto de la linea ``-- check:`` (o el nombre del archivo si no la tiene)."""
    for line in sql.splitlines():
        if line.startswith("-- check:"):
            return line.removeprefix("-- check:").strip()
    return ""


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("prefixes", nargs="*", help="prefijos de archivo a correr (default: todos)")
    parser.add_argument("--remote", default="sc://127.0.0.1:15002", help="Spark Connect URL")
    args = parser.parse_args()

    checks = sorted(QUALITY_DIR.glob("*.sql"))
    if args.prefixes:
        checks = [c for c in checks if c.name.startswith(tuple(args.prefixes))]
    if not checks:
        sys.exit(f"No hay controles en {QUALITY_DIR}")

    spark = SparkSession.builder.remote(args.remote).getOrCreate()
    failed = 0
    for check in checks:
        sql = check.read_text(encoding="utf-8")
        violations = spark.sql(sql)
        count = violations.count()
        status = "PASA " if count == 0 else "FALLA"
        print(f"[{status}] {check.stem}: {description(sql)}")
        if count:
            failed += 1
            violations.show(10, truncate=False)
    spark.stop()

    print(f"\n{len(checks) - failed}/{len(checks)} controles pasan")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
