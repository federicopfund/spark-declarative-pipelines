"""gold.dim_customer - dimension de clientes con historial (SCD tipo 2).

Grano: una version de un cliente. Parte de ``silver.customers_history`` y agrega lo que un modelo
dimensional necesita y el SCD2 de silver no tiene:

- ``customer_sk``: clave sustituta determinística por (customer_id, version).
- Vigencia **por fecha** ``[valid_from, valid_to)``: silver la expresa en numeros de version
  (``__START_AT`` / ``__END_AT``); los hechos necesitan fechas para unirse a la version vigente en el
  momento de cada pedido.
  - ``valid_from``: ``event_ts`` del evento que creo la version.
  - ``valid_to``: ``event_ts`` del evento que la cerro (la version siguiente o un DELETE), tomado de
    ``bronze.customers_cdc_events`` porque silver no guarda las filas de DELETE. Vigente: ``HIGH_DATE``.
- ``is_current``: la version no fue reemplazada ni borrada.
- Miembro desconocido (``customer_sk = -1``).

Supuesto: ``version`` y ``event_ts`` crecen juntos para un mismo cliente (el CDC ordena por version).
"""

from pyspark import pipelines as dp
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from retail_lakehouse.gold import HIGH_DATE, LOW_DATE, UNKNOWN_KEY, surrogate_key, unknown_member

spark: SparkSession


@dp.materialized_view(
    comment="Customers with history (SCD type 2). Grain: one customer version. customer_sk -1 = unknown.",
    table_properties={"layer": "gold", "kind": "dimension", "scd": "2"},
)
def dim_customer() -> DataFrame:
    # Lectura por las vistas src_* (gold/sql/inputs.sql): SDP espera a que silver termine (ver docs/data-model.md)
    versions = spark.table("src_customers_history").alias("v")

    # Cuando se cerro cada version: el evento CDC cuya version es el __END_AT de la version (dedup de re-envios)
    closing_events = (
        spark.table("src_customers_cdc_events")
        .select("customer_id", F.col("version").alias("closed_by_version"), F.col("event_ts").alias("closed_at"))
        .dropDuplicates(["customer_id", "closed_by_version"])
        .alias("e")
    )

    customers = (
        versions.join(
            closing_events,
            (F.col("v.customer_id") == F.col("e.customer_id")) & (F.col("v.__END_AT") == F.col("e.closed_by_version")),
            "left",
        )
        .select(
            surrogate_key("v.customer_id", "v.version").alias("customer_sk"),
            F.col("v.customer_id").alias("customer_id"),
            F.col("v.version").alias("version"),
            F.col("v.name").alias("name"),
            F.col("v.email").alias("email"),
            F.col("v.country").alias("country"),
            F.col("v.event_ts").alias("valid_from"),
            F.coalesce(F.col("e.closed_at"), F.to_timestamp(F.lit(HIGH_DATE))).alias("valid_to"),
            F.col("v.__END_AT").isNull().alias("is_current"),
        )
    )

    unknown = unknown_member(spark, {
        "customer_sk": F.lit(UNKNOWN_KEY).cast("bigint"),
        "customer_id": F.lit(UNKNOWN_KEY).cast("int"),
        "version": F.lit(0).cast("bigint"),
        "name": F.lit("Desconocido"),
        "email": F.lit(None).cast("string"),
        "country": F.lit("Desconocido"),
        "valid_from": F.to_timestamp(F.lit(LOW_DATE)),
        "valid_to": F.to_timestamp(F.lit(HIGH_DATE)),
        "is_current": F.lit(True),
    })

    return customers.unionByName(unknown).withColumn("_loaded_at", F.current_timestamp())
