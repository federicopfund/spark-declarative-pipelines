"""Consulta las tablas del pipeline por Spark Connect.

Es un cliente liviano: no levanta una JVM local, solo envia planes al servidor Spark Connect
(que corre sobre el cluster Standalone) y recibe los resultados en formato Arrow.

    bin\\query-lakehouse.cmd                       todas las tablas
    bin\\query-lakehouse.cmd customers customers_history
"""

from __future__ import annotations

import argparse

from pyspark.sql import SparkSession

DATASETS = [
    "customers_cdc_events",
    "customers",
    "customers_history",
    "orders",
    "sales_by_country",
    "daily_sales_by_channel",
]

SORT_KEYS = {
    "customers_cdc_events": ["customer_id", "version"],
    "customers": ["customer_id"],
    "customers_history": ["customer_id", "__START_AT"],
    "orders": ["order_id"],
    "orders_web_raw": ["order_id"],
    "orders_store_raw": ["order_id"],
    "sales_by_country": ["country"],
    "daily_sales_by_channel": ["order_date", "channel"],
}

HIDDEN_COLUMNS = {"_ingested_at", "_source_file"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("datasets", nargs="*", default=DATASETS, help="datasets to show (default: all)")
    parser.add_argument("--remote", default="sc://127.0.0.1:15002", help="Spark Connect URL")
    parser.add_argument("--database", default="retail")
    args = parser.parse_args()

    spark = SparkSession.builder.remote(args.remote).getOrCreate()
    print(f"Spark Connect {spark.version} at {args.remote}  (cluster: {spark.conf.get('spark.master')})")

    existing = {t.name for t in spark.catalog.listTables(args.database)}
    for name in args.datasets:
        if name not in existing:
            print(f"\n== {args.database}.{name}: not found (run the pipeline first) ==")
            continue
        df = spark.table(f"{args.database}.{name}")
        df = df.select(*[c for c in df.columns if c not in HIDDEN_COLUMNS])
        sort = [c for c in SORT_KEYS.get(name, []) if c in df.columns]
        if sort:
            df = df.orderBy(*sort)
        print(f"\n== {args.database}.{name} ({df.count()} rows) ==")
        df.show(50, truncate=False)

    spark.stop()


if __name__ == "__main__":
    main()
