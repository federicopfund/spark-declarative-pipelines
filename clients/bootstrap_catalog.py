"""Crea la base de datos destino del pipeline (SDP no la crea por su cuenta).

Lee `catalog` y `database` de spark-pipeline.yml y ejecuta CREATE DATABASE IF NOT EXISTS
por Spark Connect. Es idempotente: bin\\start-cluster.cmd lo corre en cada arranque.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml
from pyspark.sql import SparkSession


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remote", default="sc://127.0.0.1:15002")
    parser.add_argument(
        "--spec",
        default=str(Path(__file__).resolve().parents[1] / "pipelines" / "retail_lakehouse" / "spark-pipeline.yml"),
    )
    args = parser.parse_args()

    spec = yaml.safe_load(Path(args.spec).read_text(encoding="utf-8"))
    database = spec.get("database") or spec.get("schema")
    if not database:
        print("spec has no database: nothing to create")
        return
    qualified = f"{spec['catalog']}.{database}" if spec.get("catalog") else database

    spark = SparkSession.builder.remote(args.remote).getOrCreate()
    spark.sql(f"CREATE DATABASE IF NOT EXISTS {qualified} COMMENT 'Pipeline {spec['name']}'")
    print(f"    [OK] database {qualified} ready")
    spark.stop()


if __name__ == "__main__":
    main()
