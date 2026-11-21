# jars/

Jars extra que se agregan al servidor Spark Connect y al Thrift Server (`--jars`). Los `*.jar` no se versionan.

- `jars/*.jar`: se cargan en cada arranque de `bin\start-cluster`.
- `jars/disabled/`: jars guardados pero **no** cargados. Hoy: `iceberg-spark-runtime-4.1_2.13-1.12.0.jar`, que no carga en Spark 4.3.
  Cuando exista un runtime de Iceberg para Spark 4.3, el jar va en `jars/` y se activa el catálogo en
  `conf/spark-defaults.conf` (ver la sección *AUTO CDC* de ese archivo).
