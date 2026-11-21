"""Esquemas explicitos de los archivos que llegan a la capa bronze.

Los streaming tables sobre archivos necesitan un esquema fijo: Structured Streaming no infiere
esquemas en lecturas incrementales.
"""

from pyspark.sql.types import (
    DecimalType,
    IntegerType,
    LongType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

# Evento de cambio de un cliente (Change Data Capture)
#   op       INSERT | UPDATE | DELETE
#   version  secuencia monotona por cliente: el valor mas alto es el estado mas reciente
CUSTOMERS_CDC_SCHEMA = StructType(
    [
        StructField("customer_id", IntegerType(), nullable=False),
        StructField("name", StringType()),
        StructField("email", StringType()),
        StructField("country", StringType()),
        StructField("op", StringType(), nullable=False),
        StructField("version", LongType(), nullable=False),
        StructField("event_ts", TimestampType(), nullable=False),
    ]
)

# Pedido (mismo esquema para los canales web y store)
ORDERS_SCHEMA = StructType(
    [
        StructField("order_id", StringType(), nullable=False),
        StructField("customer_id", IntegerType(), nullable=False),
        StructField("amount", DecimalType(12, 2), nullable=False),
        StructField("order_ts", TimestampType(), nullable=False),
    ]
)
