"""Convenciones de claves del modelo dimensional.

- Claves sustitutas (``*_sk``): hash determinístico de la clave de negocio (más la versión en SCD2).
  Los materialized views se recalculan completos en cada ejecución: un numerador secuencial cambiaría
  de valor y rompería las relaciones; un hash da siempre el mismo valor para la misma fila.
- Claves de fecha (``date_key``): entero ``yyyyMMdd`` (p. ej. 20261101), legible y ordenable.
- Miembro desconocido: cada dimensión tiene una fila con clave ``-1``. Un hecho sin dimensión (p. ej. un
  pedido cuyo cliente todavía no llegó por CDC) se asigna a ella en lugar de perderse en el join.
- Vigencia SCD2: ``[valid_from, valid_to)``; la versión vigente usa ``HIGH_DATE`` como fin.

Las funciones devuelven expresiones (``Column``) o DataFrames sin analizarlos: dentro de una función de
dataset de SDP no se puede consultar el esquema ni contar filas.
"""

from __future__ import annotations

from typing import Mapping

from pyspark.sql import Column, DataFrame, SparkSession
from pyspark.sql import functions as F

__all__ = ["HIGH_DATE", "LOW_DATE", "UNKNOWN_KEY", "date_key", "surrogate_key", "unknown_member"]

UNKNOWN_KEY = -1
LOW_DATE = "1900-01-01 00:00:00"
HIGH_DATE = "9999-12-31 23:59:59"


def surrogate_key(*columns: str | Column) -> Column:
    """Clave sustituta determinística (xxhash64, bigint) a partir de una o más columnas de negocio."""
    if not columns:
        raise ValueError("surrogate_key needs at least one column")
    return F.xxhash64(*columns)


def date_key(timestamp: str | Column) -> Column:
    """Clave de fecha ``yyyyMMdd`` (int) para un timestamp o fecha; nula si el valor es nulo."""
    value = F.col(timestamp) if isinstance(timestamp, str) else timestamp
    return F.date_format(value, "yyyyMMdd").cast("int")


def unknown_member(spark: SparkSession, columns: Mapping[str, Column]) -> DataFrame:
    """Una fila con los valores del miembro desconocido, para unir con ``unionByName``.

    ``columns`` define nombre y valor (ya casteado al tipo de la dimensión) de cada columna, en el mismo
    orden que la dimensión: ``{"customer_sk": F.lit(UNKNOWN_KEY).cast("bigint"), ...}``.
    """
    return spark.range(1).select(*[value.alias(name) for name, value in columns.items()])
