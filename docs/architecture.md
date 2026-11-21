# Arquitectura

## Componentes en ejecución

```
                        ┌──────────────────────────── Cluster Spark Standalone ────────────────────────────┐
PySpark / spark-pipelines ── gRPC ──► Spark Connect :15002 ─┐                                            │
                                                             ├──► Master :7077 ──► Worker (ejecutores) ──► warehouse/*.parquet
Power BI ── ODBC ─┐                                          │                                            │
beeline  ── JDBC ─┴─ Thrift ──► Thrift JDBC/ODBC :10000 ─────┘                                            │
                        └──────────────────────────────────────────────────────────────────────────────────┘
                                 Spark Connect y Thrift ──► Hive metastore ──► Derby (modo red) :1527 ──► metastore_db/
```

| Proceso | Puerto | Rol |
|---|---|---|
| Derby Network Server | 1527 | Base del Hive metastore. En modo red para que lo compartan los dos drivers (Derby embebido admite una sola JVM). |
| Master | 7077 (UI 8080) | Asigna recursos del cluster. |
| Worker | UI 8081 | 3 núcleos / 3 GB: 2 núcleos para Connect, 1 para Thrift. |
| Spark Connect | 15002 (UI 4040) | Recibe planes de DataFrame (protobuf); ejecuta el pipeline SDP. |
| Thrift JDBC/ODBC Server | 10000 (UI 4041) | Implementación de HiveServer2 sobre Spark SQL; recibe SQL de herramientas de BI. |

Los dos drivers (Connect y Thrift) usan la misma configuración: `conf/spark-defaults.conf`, el mismo
`spark.sql.warehouse.dir` y el mismo metastore. Lo arma `bin/start-cluster.ps1`.

## Flujo de datos

1. **Landing** (`data/landing/`): llegan archivos por lote (`bin/land-batch`).
2. **Bronze**: streaming tables que leen solo los archivos nuevos (checkpoints en `storage/`).
3. **Silver**: `orders` une y deduplica los canales; `customers` (SCD1) y `customers_history` (SCD2) aplican los
   eventos CDC con la lógica de `src/retail_lakehouse/cdc.py`.
4. **Gold**: agregados (`sales_by_country`, `daily_sales_by_channel`) sobre la vista temporal `orders_enriched`.
5. **Exports**: sink que publica en JSON los pedidos nuevos (`data/export/`).
6. **Consumo**: Power BI importa silver y gold por el Thrift Server.

## Modelo de Power BI

`bi/powerbi/RetailLakehouse.SemanticModel` (TMDL, generado por `bi/powerbi/tools/generate_model.py`):

- Tablas: `orders`, `customers`, `customers_history`, `sales_by_country`, `daily_sales_by_channel`, en modo importación con
  `ApacheSpark.Tables(SparkServer, 0)` (protocolo Standard). `SparkServer` es un parámetro (`127.0.0.1:10000`).
- Relaciones: `orders[customer_id]` → `customers[customer_id]`; `customers_history[customer_id]` → `customers[customer_id]`.
- Reporte: páginas *Ventas* y *Clientes* (`bi/powerbi/RetailLakehouse.Report`, formato PBIR).

## Camino a producción

| Hoy (local) | Producción |
|---|---|
| Disco local | Almacenamiento de objetos (S3, ADLS, GCS) |
| Parquet | Delta Lake o Apache Iceberg (transacciones, MERGE, AUTO CDC) |
| Derby | Metastore en PostgreSQL/MySQL gestionado, Unity Catalog o AWS Glue |
| Standalone en una máquina | Varias VMs, Kubernetes (Spark on K8s) o YARN |
| Thrift sin autenticación en 127.0.0.1 | Thrift con LDAP/Kerberos y TLS, en red privada |
| Ejecución manual | Orquestador (Airflow, Dagster) |
| Power BI Desktop | Power BI Service + On-premises data gateway |

Alternativa habitual: una plataforma gestionada (Databricks, Microsoft Fabric, Synapse, EMR) que ya resuelve
cómputo, catálogo, almacenamiento y endpoint SQL; las transformaciones del pipeline se trasladan sin cambios de lógica.
