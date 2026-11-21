# Retail Lakehouse · Spark Declarative Pipelines

![Apache Spark](https://img.shields.io/badge/Apache%20Spark-4.3.0-E25A1C?logo=apachespark&logoColor=white)
![Spark Declarative Pipelines](https://img.shields.io/badge/Spark-Declarative%20Pipelines-E25A1C?logo=apachespark&logoColor=white)
![Power BI](https://img.shields.io/badge/Power%20BI-PBIP%20%2F%20TMDL-F2C811?logo=powerbi&logoColor=black)
![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)
![License](https://img.shields.io/badge/Licencia-MIT-green)

Lakehouse de ejemplo con arquitectura medallón (bronze → silver → gold) construido con
**Spark Declarative Pipelines (SDP)** sobre **Apache Spark 4.3**, con ingesta incremental,
Change Data Capture (SCD tipo 1 y 2) y un reporte de **Power BI** conectado por el Thrift JDBC/ODBC Server.

## Contenido

- [Stack](#stack)
- [Arquitectura en ejecución](#arquitectura-en-ejecución)
- [Flujo de datos](#flujo-de-datos)
- [Datasets](#datasets)
- [Estructura del repositorio](#estructura-del-repositorio)
- [Requisitos](#requisitos)
- [Puesta en marcha](#puesta-en-marcha)
- [Reporte de Power BI](#reporte-de-power-bi)
- [Limitaciones](#limitaciones)
- [Documentación](#documentación)
- [Licencia](#licencia)

## Stack

| | Componente | Uso |
|---|---|---|
| ![Apache Spark](https://img.shields.io/badge/Apache%20Spark-4.3.0-E25A1C?logo=apachespark&logoColor=white) | Apache Spark 4.3 (Standalone: master + worker) | Motor de cómputo |
| ![Spark Declarative Pipelines](https://img.shields.io/badge/Spark-Declarative%20Pipelines-E25A1C?logo=apachespark&logoColor=white) | Spark Declarative Pipelines | Definición declarativa de datasets y flujos |
| ![PySpark](https://img.shields.io/badge/PySpark-4.3-E25A1C?logo=apachespark&logoColor=white) | PySpark | Transformaciones en Python y clientes |
| ![Spark Connect](https://img.shields.io/badge/Spark%20Connect-gRPC%2015002-244c5a?logo=grpc&logoColor=white) | Spark Connect (`sc://127.0.0.1:15002`) | Ejecución del pipeline y clientes PySpark |
| ![Thrift](https://img.shields.io/badge/Thrift-JDBC%2FODBC%2010000-555555?logo=apache&logoColor=white) | Thrift JDBC/ODBC Server (`127.0.0.1:10000`) | Acceso SQL para herramientas de BI |
| ![Hive Metastore](https://img.shields.io/badge/Hive%20Metastore-Derby-FDEE21?logo=apachehive&logoColor=black) | Hive metastore sobre Apache Derby en modo red (`:1527`) | Catálogo compartido por Connect y Thrift |
| ![Parquet](https://img.shields.io/badge/Apache%20Parquet-tables-50ABF1?logo=apacheparquet&logoColor=white) | Parquet | Formato de las tablas (`warehouse/`) |
| ![Power BI](https://img.shields.io/badge/Power%20BI-PBIP%20%2F%20TMDL-F2C811?logo=powerbi&logoColor=black) | Power BI (PBIP + TMDL, conector Spark) | Reporte `RetailLakehouse` |

## Arquitectura en ejecución

![Spark Connect](https://img.shields.io/badge/Spark%20Connect-gRPC%2015002-244c5a?logo=grpc&logoColor=white)
![Thrift](https://img.shields.io/badge/Thrift-JDBC%2FODBC%2010000-555555?logo=apache&logoColor=white)
![Hive Metastore](https://img.shields.io/badge/Hive%20Metastore-Derby-FDEE21?logo=apachehive&logoColor=black)

```mermaid
flowchart LR
    subgraph CLIENTS["Clientes"]
        direction TB
        SDP["spark-pipelines<br/>(CLI de SDP)"]
        PY["clients/*.py<br/>(PySpark)"]
        BI["Power BI Desktop"]
        BL["beeline"]
    end

    subgraph DRIVERS["Drivers Spark"]
        direction TB
        CON["Spark Connect<br/>:15002"]
        THR["Thrift JDBC/ODBC<br/>:10000"]
    end

    subgraph CLUSTER["Spark Standalone"]
        direction TB
        MAS["Master :7077"]
        WRK["Worker<br/>ejecutores"]
    end

    DER[("Derby · metastore Hive<br/>:1527")]
    WH[("warehouse/<br/>tablas Parquet")]

    SDP -- "gRPC" --> CON
    PY -- "gRPC" --> CON
    BI -- "ODBC" --> THR
    BL -- "JDBC" --> THR

    CON --> MAS
    THR --> MAS
    MAS --> WRK
    WRK --> WH

    CON -. "catálogo" .-> DER
    THR -. "catálogo" .-> DER
```

Spark Connect recibe planes de DataFrame (código); el Thrift Server recibe SQL (herramientas de BI). Los dos
comparten el cluster y el catálogo: Derby corre en modo red porque en modo embebido admite una sola JVM.
Detalle en [`docs/architecture.md`](docs/architecture.md).

## Flujo de datos

![Medallion](https://img.shields.io/badge/Arquitectura-Medallion%20(bronze%2Fsilver%2Fgold)-8B5A2B)
![CDC](https://img.shields.io/badge/CDC-SCD1%20%7C%20SCD2-6A5ACD)
![Mermaid](https://img.shields.io/badge/Diagramas-Mermaid-FF3670?logo=mermaid&logoColor=white)

```mermaid
flowchart LR
    subgraph LANDING["data/landing"]
        direction TB
        FW["orders_web/*.json"]
        FS["orders_store/*.csv"]
        FC["customers_cdc/*.json"]
    end

    subgraph BRONZE["🥉 Bronze"]
        direction TB
        OWR["orders_web_raw"]
        OSR["orders_store_raw"]
        CCE["customers_cdc_events"]
    end

    subgraph SILVER["🥈 Silver"]
        direction TB
        ORD["orders<br/><i>unión + dedup por order_id</i>"]
        CUS["customers<br/><i>SCD tipo 1</i>"]
        HIS["customers_history<br/><i>SCD tipo 2</i>"]
        ENR(["orders_enriched<br/><i>vista temporal</i>"])
    end

    subgraph GOLD["🥇 Gold"]
        direction TB
        SBC["sales_by_country"]
        DSC["daily_sales_by_channel"]
    end

    EXP[["orders_export<br/><i>sink JSON → data/export</i>"]]
    PBI{{"Power BI<br/>RetailLakehouse"}}

    FW --> OWR
    FS --> OSR
    FC --> CCE

    OWR --> ORD
    OSR --> ORD
    CCE -- "CDC" --> CUS
    CCE -- "CDC" --> HIS

    OWR --> EXP
    OSR --> EXP

    ORD --> ENR
    CUS --> ENR
    ENR --> SBC
    ENR --> DSC

    ORD -. "Thrift / ODBC" .-> PBI
    CUS -.-> PBI
    HIS -.-> PBI
    SBC -.-> PBI
    DSC -.-> PBI
```

- **Landing** recibe archivos por lote (JSON y CSV), simulando lo que llega de los sistemas de origen.
- **Bronze** (streaming tables) lee de forma incremental solo los archivos nuevos de cada carpeta (checkpoints en `storage/`).
- **Silver** une los canales sin duplicados y aplica los eventos de cambio de clientes: versión vigente (SCD1)
  e historial completo con `__START_AT` / `__END_AT` (SCD2).
- **Gold** (materialized views) agrega sobre `orders_enriched` (pedidos + país actual del cliente), una vista que solo existe durante la ejecución.
- **Exports** publica los pedidos nuevos fuera del pipeline, en un único flow para los dos canales.
- **Power BI** importa silver y gold por el Thrift JDBC/ODBC Server.

## Datasets

![Parquet](https://img.shields.io/badge/Apache%20Parquet-tables-50ABF1?logo=apacheparquet&logoColor=white)
![CDC](https://img.shields.io/badge/CDC-SCD1%20%7C%20SCD2-6A5ACD)

| Capa | Dataset | Tipo | Descripción |
|---|---|---|---|
| bronze | `orders_web_raw`, `orders_store_raw` | streaming table | Pedidos crudos por canal (JSON / CSV) |
| bronze | `customers_cdc_events` | streaming table | Eventos de cambio de clientes |
| silver | `orders` | materialized view | Pedidos de todos los canales, sin duplicados |
| silver | `customers` | materialized view | Versión vigente de cada cliente (SCD1) |
| silver | `customers_history` | materialized view | Todas las versiones (SCD2, `__START_AT`/`__END_AT`) |
| silver | `orders_enriched` | vista temporal | Pedidos + cliente; solo durante la ejecución |
| gold | `sales_by_country`, `daily_sales_by_channel` | materialized view | Agregados para consumo |
| exports | `orders_export` | sink | Pedidos nuevos en JSON |

## Estructura del repositorio

```
├── pipelines/retail_lakehouse/      Pipeline SDP
│   ├── spark-pipeline.yml           Spec (plantilla: ${PROJECT_ROOT_URI} se resuelve al correr)
│   └── transformations/
│       ├── bronze/                  Ingesta incremental desde data/landing
│       ├── silver/                  Pedidos unificados, clientes SCD1 y SCD2
│       ├── gold/                    Ventas por país y por día/canal
│       └── exports/                 Sink de pedidos nuevos (JSON)
├── src/retail_lakehouse/            Librería compartida (esquemas, lógica CDC)
├── clients/                         Clientes Spark Connect (bootstrap del catálogo, consultas)
├── bin/                             Scripts de operación (Windows: .cmd → .ps1)
├── conf/                            spark-defaults, log4j2, entorno (spark-env.ps1)
├── bi/powerbi/                      Proyecto Power BI (PBIP) + generador del modelo
├── data/samples/                    Lotes de datos de ejemplo
├── docs/                            Arquitectura, operación e imágenes
└── jars/                            Jars extra opcionales (no versionados)
```

Las carpetas `warehouse/`, `metastore_db/`, `storage/`, `logs/`, `work/`, `data/landing/` y `data/export/`
son estado de ejecución: se generan al correr y no se versionan.

## Requisitos

![Windows](https://img.shields.io/badge/Windows-10%20%7C%2011-0078D6?logo=windows&logoColor=white)
![PowerShell](https://img.shields.io/badge/PowerShell-5.1-5391FE?logo=powershell&logoColor=white)
![Java](https://img.shields.io/badge/Java-17-ED8B00?logo=openjdk&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)
![Apache Spark](https://img.shields.io/badge/Apache%20Spark-4.3.0-E25A1C?logo=apachespark&logoColor=white)

- Windows 10/11 con PowerShell 5.1
- Java 17 (`JAVA_HOME`)
- Apache Spark 4.3.0 (`SPARK_HOME` como variable de usuario) y `HADOOP_HOME` con `winutils.exe`
- Python 3.13
- Power BI Desktop **2.159 (noviembre 2026) o posterior**, con la versión preliminar
  *Store reports using enhanced metadata format (PBIR)* activada

## Puesta en marcha

![PowerShell](https://img.shields.io/badge/PowerShell-5.1-5391FE?logo=powershell&logoColor=white)

```mermaid
flowchart TD
    A["1 · Entorno Python<br/><code>python -m venv .venv</code>"] --> B["2 · Dependencias<br/><code>bin\setup-dependencies</code>"]
    B --> C["3 · Levantar servicios<br/><code>bin\start-cluster</code>"]
    C --> D["4 · Aterrizar un lote<br/><code>bin\land-batch -Batch N</code>"]
    D --> E["5 · Ejecutar el pipeline<br/><code>bin\spark-pipelines run</code>"]
    E --> F["6a · Consultar<br/><code>bin\query-lakehouse</code>"]
    E --> G["6b · Power BI<br/>abrir el .pbip y Actualizar"]
    E -- "siguiente lote" --> D
    C -. "al terminar" .-> H["<code>bin\stop-cluster</code>"]
```

```powershell
# 1. Entorno Python (PySpark se usa desde SPARK_HOME\python, no se instala con pip)
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt

# 2. Jars que no vienen con Spark (Derby en modo red), con verificación SHA-1
bin\setup-dependencies.cmd

# 3. Levantar Derby, el cluster, Spark Connect y el Thrift Server
bin\start-cluster.cmd

# 4. Aterrizar datos de ejemplo y correr el pipeline
bin\land-batch.cmd -Batch 1
bin\spark-pipelines.cmd run

# 5. Consultar las tablas
bin\query-lakehouse.cmd
```

Los lotes 2 y 3 ejercitan updates, deletes, duplicados y eventos fuera de orden (ver `data/samples/README.md`).

## Reporte de Power BI

![Power BI](https://img.shields.io/badge/Power%20BI-PBIP%20%2F%20TMDL-F2C811?logo=powerbi&logoColor=black)
![Thrift](https://img.shields.io/badge/Thrift-JDBC%2FODBC%2010000-555555?logo=apache&logoColor=white)

Abrir `bi/powerbi/RetailLakehouse.pbip` y **Actualizar**. Credenciales: *Nombre de usuario y contraseña*
con cualquier valor (el Thrift Server local no tiene autenticación; solo escucha en `127.0.0.1`).
Ver `docs/operations.md`.

El reporte `RetailLakehouse` importa las tablas silver y gold por el Thrift Server
(conector Spark, protocolo Standard) y tiene dos páginas:

**Ventas**: indicadores de ventas, pedidos, clientes y ticket promedio; ventas por país y por día y canal
(capa gold) y el detalle de pedidos (capa silver).

![Página Ventas del reporte RetailLakehouse](docs/images/powerbi-ventas.png)

**Clientes**: resultado del CDC. Clientes vigentes (SCD1) e historial completo de versiones (SCD2) con su
vigencia (`__START_AT` / `__END_AT`) y su estado.

![Página Clientes del reporte RetailLakehouse](docs/images/powerbi-clientes.png)

## Limitaciones

- **Parquet en lugar de un formato transaccional.** Dos flows no pueden escribir al mismo target: comparten el
  registro `_spark_metadata` y el segundo se saltea en silencio. Por eso cada canal tiene su streaming table y la
  unión se hace en `silver.orders`.
- **AUTO CDC** (`create_auto_cdc_flow`) necesita un catálogo con operaciones a nivel fila (Apache Iceberg) y todavía
  no hay runtime de Iceberg para Spark 4.3. `src/retail_lakehouse/cdc.py` reproduce su semántica con los mismos
  parámetros, para migrar sin cambiar el modelo.
- **`--full-refresh-all`** falla con Parquet (los materialized views leen archivos ya borrados). Usar
  `bin\reset-pipeline.cmd`, que borra el estado y reinicia el cluster.
- **Derby** es un metastore de desarrollo. En producción: PostgreSQL/MySQL, Unity Catalog o AWS Glue
  (ver `docs/architecture.md`).

## Documentación

| Documento | Contenido |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | Componentes, puertos, flujo de datos, modelo de Power BI y camino a producción |
| [`docs/operations.md`](docs/operations.md) | Scripts de `bin/`, logs, consultas SQL por Thrift, Power BI y errores conocidos |
| [`data/samples/README.md`](data/samples/README.md) | Qué ejercita cada lote de datos de ejemplo y el resultado esperado |

## Licencia

![License](https://img.shields.io/badge/Licencia-MIT-green)

Distribuido bajo la licencia [MIT](LICENSE).
