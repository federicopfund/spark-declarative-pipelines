"""Change Data Capture (CDC) con la semantica de ``dp.create_auto_cdc_flow``.

AUTO CDC de Spark Declarative Pipelines 4.3 necesita un catalogo con operaciones a nivel fila
(Apache Iceberg) y todavia no existe un runtime de Iceberg para Spark 4.3. Este modulo reproduce
sus reglas sobre un materialized view, con los mismos nombres de parametros, para que la migracion
a AUTO CDC sea un cambio de una linea y no un cambio de modelo:

    AUTO CDC                                   este modulo
    ----------------------------------------   ------------------------------------------
    keys=[...]                                 keys=[...]
    sequence_by="version"                      sequence_by="version"
    apply_as_deletes="op = 'DELETE'"           apply_as_deletes="op = 'DELETE'"
    column_list / except_column_list           column_list / except_column_list
    stored_as_scd_type=1                       apply_changes_scd1(...)
    stored_as_scd_type=2                       apply_changes_scd2(...)

Reglas (las de la guia de SDP):
    - Inserts y updates: por clave gana el evento con el ``sequence_by`` mas alto.
    - Deletes: si el evento ganador cumple ``apply_as_deletes``, la clave desaparece (SCD1)
      o su ultima version se cierra sin crear una nueva (SCD2).
    - Eventos desordenados o repetidos convergen al mismo resultado.
    - ``sequence_by`` nulo es un error (``NULL_SEQUENCE``), igual que en AUTO CDC.
    - Los empates de ``sequence_by`` dentro de una misma clave se resuelven de forma arbitraria.

Restricciones de SDP sobre Spark Connect que este modulo respeta:
    - Una funcion de dataset no puede analizar su DataFrame (``df.columns``, ``df.schema``, ``count``):
      falla con ``ATTEMPT_ANALYSIS_IN_PIPELINE_QUERY_FUNCTION``.
    - ``DataFrame.drop()`` resuelve el plan al registrar el dataset y falla con
      ``TABLE_OR_VIEW_NOT_FOUND`` (el origen todavia no existe). Por eso las columnas tecnicas se
      quitan con ``SELECT * EXCEPT (...)``, que se resuelve recien al ejecutar.

Ejemplo::

    customers = apply_changes_scd1(
        spark.table("customers_cdc_events"),
        keys=["customer_id"],
        sequence_by="version",
        apply_as_deletes="op = 'DELETE'",
        except_column_list=["op", "_ingested_at", "_source_file"],
    )
"""

from __future__ import annotations

from typing import Optional, Sequence, Union

from pyspark.sql import Column, DataFrame, Window
from pyspark.sql import functions as F
from pyspark.sql.window import WindowSpec

__all__ = [
    "END_AT",
    "START_AT",
    "CdcConfigurationError",
    "apply_changes_scd1",
    "apply_changes_scd2",
]

# Expresion de columna: texto SQL (``"op = 'DELETE'"``) o un ``Column`` ya construido.
ColumnExpr = Union[str, Column]

# ---------------------------------------------------------------------------------------------
# Columnas
# ---------------------------------------------------------------------------------------------

# Columnas de vigencia SCD tipo 2 (los mismos nombres que usa AUTO CDC).
START_AT = "__START_AT"
END_AT = "__END_AT"

# Columnas tecnicas internas. AUTO CDC reserva el prefijo ``__spark_autocdc_``; aqui ``__cdc_``.
# Nunca llegan a la salida: se quitan en ``_project_output``.
_SEQUENCE = "__cdc_sequence"
_RANK = "__cdc_rank"
_IS_DELETE = "__cdc_is_delete"

_NULL_SEQUENCE_MESSAGE = "CDC NULL_SEQUENCE: sequence_by evaluated to NULL"


class CdcConfigurationError(ValueError):
    """Parametros de CDC invalidos (claves vacias, listas de columnas incompatibles, etc.)."""


# ---------------------------------------------------------------------------------------------
# API publica
# ---------------------------------------------------------------------------------------------


def apply_changes_scd1(
    events: DataFrame,
    *,
    keys: Sequence[str],
    sequence_by: ColumnExpr,
    apply_as_deletes: Optional[ColumnExpr] = None,
    column_list: Optional[Sequence[str]] = None,
    except_column_list: Optional[Sequence[str]] = None,
) -> DataFrame:
    """Aplica eventos CDC como SCD tipo 1: una fila por clave con su ultimo estado.

    Args:
        events: Eventos de cambio (inserts, updates y deletes), en cualquier orden.
        keys: Columnas que identifican a la entidad (clave de negocio).
        sequence_by: Columna o expresion que ordena los eventos de una clave; no puede ser nula.
        apply_as_deletes: Condicion que marca un evento como borrado. ``None``: no hay deletes.
        column_list: Columnas a publicar. Excluyente con ``except_column_list``.
        except_column_list: Columnas a omitir de la salida (p. ej. la operacion o metadatos).

    Returns:
        Un DataFrame con la version vigente de cada clave. Las claves cuyo ultimo evento es un
        delete no aparecen.

    Raises:
        CdcConfigurationError: Si ``keys`` esta vacio o se pasan las dos listas de columnas.
    """
    _validate_options(keys, column_list, except_column_list)

    # Por clave, el evento con el sequence_by mas alto (rank 1) es el estado vigente.
    latest = (
        _with_sequence(events, sequence_by)
        .withColumn(_RANK, F.row_number().over(_window_by_keys(keys).orderBy(F.col(_SEQUENCE).desc())))
        .filter(F.col(_RANK) == 1)
    )

    # Si el ultimo evento de una clave es un delete, la clave deja de existir.
    if apply_as_deletes is not None:
        latest = latest.filter(~_to_column(apply_as_deletes))

    return _project_output(
        latest,
        technical_columns=[_SEQUENCE, _RANK],
        column_list=column_list,
        except_column_list=except_column_list,
    )


def apply_changes_scd2(
    events: DataFrame,
    *,
    keys: Sequence[str],
    sequence_by: ColumnExpr,
    apply_as_deletes: Optional[ColumnExpr] = None,
    column_list: Optional[Sequence[str]] = None,
    except_column_list: Optional[Sequence[str]] = None,
) -> DataFrame:
    """Aplica eventos CDC como SCD tipo 2: una fila por cada version de cada clave.

    ``__START_AT`` es el ``sequence_by`` en que la version empieza a regir y ``__END_AT`` el del
    evento siguiente de la misma clave (otra version o el delete que la cerro). ``__END_AT`` nulo
    marca la version vigente.

    Args:
        events: Eventos de cambio (inserts, updates y deletes), en cualquier orden.
        keys: Columnas que identifican a la entidad (clave de negocio).
        sequence_by: Columna o expresion que ordena los eventos de una clave; no puede ser nula.
        apply_as_deletes: Condicion que marca un evento como borrado. ``None``: no hay deletes.
        column_list: Columnas a publicar (siempre se agregan ``__START_AT`` y ``__END_AT``).
            Excluyente con ``except_column_list``.
        except_column_list: Columnas a omitir de la salida (p. ej. la operacion o metadatos).

    Returns:
        Un DataFrame con todas las versiones de cada clave y sus columnas de vigencia. Los deletes
        no generan filas propias: solo cierran la version anterior.

    Raises:
        CdcConfigurationError: Si ``keys`` esta vacio o se pasan las dos listas de columnas.
    """
    _validate_options(keys, column_list, except_column_list)

    is_delete = _to_column(apply_as_deletes) if apply_as_deletes is not None else F.lit(False)
    ordered_by_sequence = _window_by_keys(keys).orderBy(_SEQUENCE)

    versions = (
        _with_sequence(events, sequence_by)
        # Un evento re-enviado (misma clave y secuencia) no es una version nueva.
        .dropDuplicates([*keys, _SEQUENCE])
        .withColumn(_IS_DELETE, is_delete)
        # La vigencia se calcula antes de filtrar los deletes: un delete cierra la version previa.
        .withColumn(START_AT, F.col(_SEQUENCE))
        .withColumn(END_AT, F.lead(_SEQUENCE).over(ordered_by_sequence))
        .filter(~F.col(_IS_DELETE))
    )

    return _project_output(
        versions,
        technical_columns=[_SEQUENCE, _IS_DELETE],
        column_list=column_list,
        except_column_list=except_column_list,
        always_include=[START_AT, END_AT],
    )


# ---------------------------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------------------------


def _validate_options(
    keys: Sequence[str],
    column_list: Optional[Sequence[str]],
    except_column_list: Optional[Sequence[str]],
) -> None:
    """Valida los parametros comunes de las dos variantes, antes de construir el plan."""
    if not keys:
        raise CdcConfigurationError("keys must not be empty")
    if column_list and except_column_list:
        raise CdcConfigurationError("column_list and except_column_list are mutually exclusive")


def _to_column(expr: ColumnExpr) -> Column:
    """Convierte una expresion SQL en texto a ``Column``; un ``Column`` se devuelve tal cual."""
    return F.expr(expr) if isinstance(expr, str) else expr


def _window_by_keys(keys: Sequence[str]) -> WindowSpec:
    """Ventana particionada por las claves de negocio (un grupo por entidad)."""
    return Window.partitionBy(*keys)


def _with_sequence(events: DataFrame, sequence_by: ColumnExpr) -> DataFrame:
    """Agrega la columna de secuencia; si evalua a NULL, la ejecucion falla con NULL_SEQUENCE."""
    sequence = _to_column(sequence_by)
    return events.withColumn(
        _SEQUENCE,
        F.when(sequence.isNull(), F.raise_error(F.lit(_NULL_SEQUENCE_MESSAGE))).otherwise(sequence),
    )


def _project_output(
    df: DataFrame,
    *,
    technical_columns: Sequence[str],
    column_list: Optional[Sequence[str]],
    except_column_list: Optional[Sequence[str]],
    always_include: Sequence[str] = (),
) -> DataFrame:
    """Selecciona las columnas de salida y descarta las tecnicas.

    Con ``column_list`` se proyectan esas columnas (mas ``always_include``). Si no, se publica todo
    menos las columnas tecnicas y ``except_column_list``, con ``SELECT * EXCEPT`` para no resolver
    el plan al registrar el dataset (ver la nota sobre ``drop()`` en el docstring del modulo).
    """
    if column_list:
        return df.select(*column_list, *always_include)

    excluded = ", ".join(f"`{name}`" for name in [*technical_columns, *(except_column_list or [])])
    return df.selectExpr(f"* EXCEPT ({excluded})")
