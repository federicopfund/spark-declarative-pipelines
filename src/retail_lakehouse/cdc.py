"""Change Data Capture con la misma semantica que ``dp.create_auto_cdc_flow``.

AUTO CDC de SDP 4.3 necesita un catalogo con operaciones a nivel fila (Apache Iceberg), y todavia
no existe un runtime de Iceberg para Spark 4.3. Estas funciones reproducen sus reglas sobre un
materialized view, con los mismos nombres de parametros, para migrar sin cambiar el modelo:

  AUTO CDC                                   aqui
  ----------------------------------------   ------------------------------------------
  keys=[...]                                 keys=[...]
  sequence_by="version"                       sequence_by="version"
  apply_as_deletes="op = 'DELETE'"           apply_as_deletes="op = 'DELETE'"
  except_column_list=[...] / column_list     except_column_list=[...] / column_list
  stored_as_scd_type=1                       apply_changes_scd1(...)
  stored_as_scd_type=2                       apply_changes_scd2(...)

Reglas (las de la guia de SDP):
  - Inserts y updates: por clave gana el evento con el sequence_by mas alto.
  - Deletes: si el evento ganador cumple apply_as_deletes, la fila se elimina.
  - Eventos desordenados o repetidos: convergen al mismo resultado.
  - sequence_by nulo: error (AUTOCDC_MICROBATCH_VALIDATION.NULL_SEQUENCE en AUTO CDC).
  - Empates de sequence_by en una misma clave: se resuelven de forma arbitraria.
"""

from __future__ import annotations

from typing import Optional, Sequence

from pyspark.sql import Column, DataFrame, Window
from pyspark.sql import functions as F

# Columnas tecnicas. AUTO CDC reserva el prefijo __spark_autocdc_; aqui se usa __cdc_.
_SEQ = "__cdc_sequence"
_RANK = "__cdc_rank"
_IS_DELETE = "__cdc_is_delete"

# Columnas de vigencia SCD tipo 2 (mismos nombres que usa AUTO CDC para SCD2)
START_AT = "__START_AT"
END_AT = "__END_AT"


def _as_column(expr: str | Column) -> Column:
    return F.expr(expr) if isinstance(expr, str) else expr


def _with_sequence(events: DataFrame, sequence_by: str | Column) -> DataFrame:
    seq = _as_column(sequence_by)
    return events.withColumn(
        _SEQ,
        F.when(seq.isNull(), F.raise_error(F.lit("CDC NULL_SEQUENCE: sequence_by evaluated to NULL"))).otherwise(seq),
    )


def _select_output(
    df: DataFrame,
    technical: Sequence[str],
    column_list: Optional[Sequence[str]],
    except_column_list: Optional[Sequence[str]],
    extra: Sequence[str] = (),
) -> DataFrame:
    # Reglas de SDP sobre Spark Connect:
    #  - una funcion de dataset no puede analizar el DataFrame (df.columns, df.schema, count...)
    #    -> ATTEMPT_ANALYSIS_IN_PIPELINE_QUERY_FUNCTION
    #  - DataFrame.drop() resuelve el plan al registrarse y falla con TABLE_OR_VIEW_NOT_FOUND,
    #    porque el dataset de origen todavia no existe. `SELECT * EXCEPT (...)` se resuelve despues.
    if column_list and except_column_list:
        raise ValueError("column_list and except_column_list are mutually exclusive")
    if column_list:
        return df.select(*column_list, *extra)
    excluded = ", ".join(f"`{c}`" for c in [*technical, *(except_column_list or [])])
    return df.selectExpr(f"* EXCEPT ({excluded})")


def apply_changes_scd1(
    events: DataFrame,
    *,
    keys: Sequence[str],
    sequence_by: str | Column,
    apply_as_deletes: Optional[str | Column] = None,
    column_list: Optional[Sequence[str]] = None,
    except_column_list: Optional[Sequence[str]] = None,
) -> DataFrame:
    """SCD tipo 1: una fila por clave con su ultimo estado; las claves borradas desaparecen."""
    if not keys:
        raise ValueError("keys must not be empty")

    latest = (
        _with_sequence(events, sequence_by)
        .withColumn(_RANK, F.row_number().over(Window.partitionBy(*keys).orderBy(F.col(_SEQ).desc())))
        .filter(F.col(_RANK) == 1)
    )
    if apply_as_deletes is not None:
        latest = latest.filter(~_as_column(apply_as_deletes))

    return _select_output(latest, [_SEQ, _RANK], column_list, except_column_list)


def apply_changes_scd2(
    events: DataFrame,
    *,
    keys: Sequence[str],
    sequence_by: str | Column,
    apply_as_deletes: Optional[str | Column] = None,
    column_list: Optional[Sequence[str]] = None,
    except_column_list: Optional[Sequence[str]] = None,
) -> DataFrame:
    """SCD tipo 2: una fila por version de cada clave.

    ``__START_AT`` es el sequence_by de la version y ``__END_AT`` el de la siguiente
    (o del delete que la cerro). ``__END_AT`` nulo marca la version vigente.
    """
    if not keys:
        raise ValueError("keys must not be empty")

    is_delete = _as_column(apply_as_deletes) if apply_as_deletes is not None else F.lit(False)
    versions = (
        _with_sequence(events, sequence_by)
        .dropDuplicates([*keys, _SEQ])  # eventos re-enviados
        .withColumn(_IS_DELETE, is_delete)
        .withColumn(START_AT, F.col(_SEQ))
        .withColumn(END_AT, F.lead(_SEQ).over(Window.partitionBy(*keys).orderBy(_SEQ)))
        .filter(~F.col(_IS_DELETE))
    )
    return _select_output(versions, [_SEQ, _IS_DELETE], column_list, except_column_list, extra=[START_AT, END_AT])
