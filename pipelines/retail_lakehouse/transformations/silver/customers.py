"""silver.customers - estado actual de cada cliente (CDC, SCD tipo 1).

Equivale a:

    dp.create_streaming_table("customers")
    dp.create_auto_cdc_flow(
        target="customers", source="customers_cdc_events",
        keys=["customer_id"], sequence_by="version",
        apply_as_deletes="op = 'DELETE'",
        except_column_list=["op", "_ingested_at", "_source_file"],
        stored_as_scd_type=1,
    )

que se activara cuando exista un catalogo Iceberg compatible con Spark 4.3 (ver README).
"""

from pyspark import pipelines as dp
from pyspark.sql import DataFrame, SparkSession

from retail_lakehouse.cdc import apply_changes_scd1

spark: SparkSession


@dp.materialized_view(
    comment="Current state per customer (SCD type 1). Deleted customers are removed.",
    table_properties={"layer": "silver", "cdc": "scd1"},
)
def customers() -> DataFrame:
    return apply_changes_scd1(
        spark.table("src_customers_cdc_events"),
        keys=["customer_id"],
        sequence_by="version",
        apply_as_deletes="op = 'DELETE'",
        except_column_list=["op", "_ingested_at", "_source_file"],
    )
