"""exports.orders_export - sink: publica los pedidos nuevos fuera del pipeline.

Un sink es un destino externo de Structured Streaming (en produccion, Kafka o Event Hubs).
Aca se usa el sink de archivos JSON para no depender de un broker. Los sinks solo admiten
append_flow y escriben de forma incremental: cada ejecucion exporta solo los pedidos nuevos.

Un unico flow une los dos canales: con un sink de archivos, dos flows al mismo destino
compartirian `_spark_metadata` y el segundo se saltearia (igual que en los streaming tables).
"""

from pyspark import pipelines as dp
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

spark: SparkSession

dp.create_sink(
    name="orders_export",
    format="json",
    options={"path": f"{spark.conf.get('retail.export.root')}/orders"},
)


@dp.append_flow(target="orders_export", name="orders_export_flow")
def orders_export_flow() -> DataFrame:
    columns = ["order_id", "customer_id", "channel", "amount", "order_ts"]
    return (
        spark.readStream.table("orders_web_raw").select(*columns)
        .unionByName(spark.readStream.table("orders_store_raw").select(*columns))
        .withColumn("amount", F.col("amount").cast("string"))
        .withColumn("order_ts", F.date_format("order_ts", "yyyy-MM-dd'T'HH:mm:ss"))
    )
