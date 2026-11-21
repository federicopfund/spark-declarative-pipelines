"""bronze.orders_store_raw - streaming table con los pedidos del canal store (CSV)."""

from pyspark import pipelines as dp
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from retail_lakehouse.schemas import ORDERS_SCHEMA

spark: SparkSession


@dp.table(
    comment="Raw orders from the store channel, ingested incrementally.",
    table_properties={"layer": "bronze", "source": "orders_store"},
)
def orders_store_raw() -> DataFrame:
    landing = spark.conf.get("retail.landing.root")
    return (
        spark.readStream.schema(ORDERS_SCHEMA)
        .option("header", "true")
        .csv(f"{landing}/orders_store")
        .withColumn("channel", F.lit("store"))
        .withColumn("_ingested_at", F.current_timestamp())
    )
