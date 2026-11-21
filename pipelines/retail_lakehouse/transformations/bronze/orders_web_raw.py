"""bronze.orders_web_raw - streaming table con los pedidos del canal web (JSON).

Cada canal tiene su propio streaming table. Con tablas Parquet, dos flows NO pueden escribir en
el mismo target: comparten el registro de lotes `_spark_metadata` y el segundo flow se saltea
en silencio (ver README, "Limitaciones"). La union de canales se hace en silver.orders.
"""

from pyspark import pipelines as dp
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from retail_lakehouse.schemas import ORDERS_SCHEMA

spark: SparkSession


@dp.table(
    comment="Raw orders from the web channel, ingested incrementally.",
    table_properties={"layer": "bronze", "source": "orders_web"},
)
def orders_web_raw() -> DataFrame:
    landing = spark.conf.get("retail.landing.root")
    return (
        spark.readStream.schema(ORDERS_SCHEMA)
        .json(f"{landing}/orders_web")
        .withColumn("channel", F.lit("web"))
        .withColumn("_ingested_at", F.current_timestamp())
    )
