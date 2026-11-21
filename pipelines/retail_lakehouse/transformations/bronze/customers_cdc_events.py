"""bronze.customers_cdc_events - streaming table con los eventos de cambio de clientes.

Lee de forma incremental los JSON que llegan a data/landing/customers_cdc: en cada ejecucion
procesa solo los archivos nuevos (el checkpoint vive en el `storage` del spec).
"""

from pyspark import pipelines as dp
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from retail_lakehouse.schemas import CUSTOMERS_CDC_SCHEMA

spark: SparkSession  # SDP inyecta la sesion (Spark 4.2+); esta linea es solo para el analisis estatico


@dp.table(
    comment="Raw customer change events (INSERT/UPDATE/DELETE), ingested incrementally.",
    table_properties={"layer": "bronze", "source": "customers_cdc"},
)
def customers_cdc_events() -> DataFrame:
    landing = spark.conf.get("retail.landing.root")
    return (
        spark.readStream.schema(CUSTOMERS_CDC_SCHEMA)
        .json(f"{landing}/customers_cdc")
        .withColumn("_ingested_at", F.current_timestamp())
        .withColumn("_source_file", F.col("_metadata.file_name"))
    )
