"""silver.customers_history - historial de versiones de cada cliente (CDC, SCD tipo 2).

Una fila por version: __START_AT / __END_AT son el `version` en que empezo y termino a regir.
__END_AT nulo = version vigente. Un DELETE cierra la ultima version sin crear una nueva.
"""

from pyspark import pipelines as dp
from pyspark.sql import DataFrame, SparkSession

from retail_lakehouse.cdc import apply_changes_scd2

spark: SparkSession


@dp.materialized_view(
    comment="Every version of every customer (SCD type 2).",
    table_properties={"layer": "silver", "cdc": "scd2"},
)
def customers_history() -> DataFrame:
    return apply_changes_scd2(
        spark.read.table("retail.customers_cdc_events"),
        keys=["customer_id"],
        sequence_by="version",
        apply_as_deletes="op = 'DELETE'",
        except_column_list=["op", "_ingested_at", "_source_file"],
    )
