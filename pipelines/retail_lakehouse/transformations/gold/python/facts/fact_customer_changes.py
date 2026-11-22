"""gold.fact_customer_changes - hechos de cambios de clientes.

Grano: un cambio de version de un cliente (de la version N-1 a la N). La primera version de cada cliente
no es un cambio. Una baja seguida de una nueva alta (p. ej. version 1 -> 3) cuenta como un cambio.

Indica que atributos cambiaron (pais, email, nombre), con la clave de fecha del cambio y las claves
sustitutas de la version anterior y la nueva. Responde "cuantos cambios hubo", "quienes cambiaron de pais"
y "cuando", sin calcularlo en el reporte.
"""

from pyspark import pipelines as dp
from pyspark.sql import Column, DataFrame, SparkSession, Window
from pyspark.sql import functions as F

from retail_lakehouse.gold import UNKNOWN_KEY, date_key, surrogate_key

spark: SparkSession

TRACKED_ATTRIBUTES = ("country", "email", "name")


def _changed(attribute: str) -> Column:
    """True si el atributo es distinto en la version anterior (null-safe)."""
    return ~F.col(attribute).eqNullSafe(F.col(f"previous_{attribute}"))


@dp.materialized_view(
    comment="Customer changes. Grain: one change from version N-1 to N of a customer.",
    table_properties={"layer": "gold", "kind": "fact"},
)
def fact_customer_changes() -> DataFrame:
    by_customer = Window.partitionBy("customer_id").orderBy("version")

    versions = spark.table("src_dim_customer").filter(F.col("customer_id") != UNKNOWN_KEY)
    for column in ("customer_sk", "version", *TRACKED_ATTRIBUTES):
        versions = versions.withColumn(f"previous_{column}", F.lag(column).over(by_customer))

    return (
        versions.filter(F.col("previous_version").isNotNull())
        .select(
            surrogate_key("customer_id", "version").alias("change_sk"),
            date_key("valid_from").alias("date_key"),
            F.col("customer_sk"),
            F.col("previous_customer_sk"),
            F.col("customer_id"),
            F.col("previous_version").alias("from_version"),
            F.col("version").alias("to_version"),
            F.col("previous_country").alias("from_country"),
            F.col("country").alias("to_country"),
            *[_changed(attribute).alias(f"{attribute}_changed") for attribute in TRACKED_ATTRIBUTES],
            F.col("valid_from").alias("changed_at"),
        )
        .withColumn("_loaded_at", F.current_timestamp())
    )
