# Arquitectura

![Apache Spark](https://img.shields.io/badge/Apache%20Spark-4.3.0-E25A1C?logo=apachespark&logoColor=white)
![Spark Declarative Pipelines](https://img.shields.io/badge/Spark-Declarative%20Pipelines-E25A1C?logo=apachespark&logoColor=white)
![Medallion](https://img.shields.io/badge/Arquitectura-Medallion%20(bronze%2Fsilver%2Fgold)-8B5A2B)
![CDC](https://img.shields.io/badge/CDC-SCD1%20%7C%20SCD2-6A5ACD)
![Power BI](https://img.shields.io/badge/Power%20BI-PBIP%20%2F%20TMDL-F2C811?logo=powerbi&logoColor=black)

Definición técnica del proyecto: qué procesos corren, cómo se comunican, cómo fluyen los datos de capa en capa,
cómo se aplica el CDC y cómo llega todo a Power BI. Para la operación diaria (scripts, logs, errores) ver
[`operations.md`](operations.md).

## Contenido

1. [Visión general](#1-visión-general)
2. [Componentes en ejecución](#2-componentes-en-ejecución)
3. [Arranque y apagado](#3-arranque-y-apagado)
4. [Pipeline declarativo](#4-pipeline-declarativo)
5. [Capa bronze: ingesta incremental](#5-capa-bronze-ingesta-incremental)
6. [Capa silver: unión y CDC](#6-capa-silver-unión-y-cdc)
7. [Capa gold y exportaciones](#7-capa-gold-y-exportaciones)
8. [Consumo: Thrift Server y Power BI](#8-consumo-thrift-server-y-power-bi)
9. [Almacenamiento y estado](#9-almacenamiento-y-estado)
10. [Seguridad](#10-seguridad)
11. [Decisiones de diseño](#11-decisiones-de-diseño)
12. [Camino a producción](#12-camino-a-producción)

---

## 1. Visión general

![Medallion](https://img.shields.io/badge/Arquitectura-Medallion%20(bronze%2Fsilver%2Fgold)-8B5A2B)

Un **lakehouse de retail** que recibe pedidos de dos canales (web y tienda) y eventos de cambio de clientes,
los procesa en tres capas con Spark Declarative Pipelines y los publica para análisis en Power BI.

```mermaid
flowchart LR
    SRC["Sistemas de origen<br/><i>web · tienda · CRM</i>"]
    LND[/"data/landing<br/>archivos por lote"/]
    PIPE["Pipeline SDP<br/><b>retail_lakehouse</b><br/>bronze → silver → gold"]
    WH[("warehouse/<br/>tablas Parquet")]
    EXP[/"data/export<br/>pedidos nuevos (JSON)"/]
    PBI{{"Power BI<br/>RetailLakehouse"}}

    SRC -- "JSON / CSV" --> LND
    LND --> PIPE
    PIPE --> WH
    PIPE --> EXP
    WH -- "Thrift / ODBC" --> PBI
```

| Aspecto | Definición |
|---|---|
| Entradas | Pedidos web (JSON), pedidos de tienda (CSV), eventos CDC de clientes (JSON) |
| Procesamiento | Spark 4.3 Standalone, pipeline declarativo ejecutado por Spark Connect |
| Salidas | 13 tablas en el catálogo `retail` (gold: modelo en estrella + agregados), un sink de pedidos en JSON, reportes de Power BI |
| Modo | Por lotes incrementales: cada ejecución procesa solo los archivos nuevos |

## 2. Componentes en ejecución

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
        CON["Spark Connect<br/>:15002 · UI :4040"]
        THR["Thrift JDBC/ODBC<br/>:10000 · UI :4041"]
    end

    subgraph CLUSTER["Spark Standalone"]
        direction TB
        MAS["Master<br/>:7077 · UI :8080"]
        WRK["Worker · UI :8081<br/>3 núcleos · 3 GB"]
    end

    DER[("Derby Network Server<br/>:1527 · metastore_db/")]
    WH[("warehouse/<br/>tablas Parquet")]

    SDP -- "gRPC + protobuf" --> CON
    PY -- "gRPC + protobuf" --> CON
    BI -- "ODBC (Simba)" --> THR
    BL -- "JDBC" --> THR

    CON -- "2 núcleos" --> MAS
    THR -- "1 núcleo" --> MAS
    MAS --> WRK
    WRK --> WH

    CON -. "JDBC (Derby client)" .-> DER
    THR -. "JDBC (Derby client)" .-> DER
```

| Proceso | Puerto | Clase principal | Rol |
|---|---|---|---|
| Derby Network Server | 1527 | `org.apache.derby.drda.NetworkServerControl` | Base del Hive metastore, en modo red para que la compartan dos JVM |
| Master | 7077 (UI 8080) | `org.apache.spark.deploy.master.Master` | Asigna recursos a las aplicaciones |
| Worker | UI 8081 | `org.apache.spark.deploy.worker.Worker` | Lanza los ejecutores (3 núcleos, 3 GB) |
| Spark Connect | 15002 (UI 4040) | `org.apache.spark.sql.connect.service.SparkConnectServer` | Recibe planes de DataFrame; ejecuta el pipeline |
| Thrift JDBC/ODBC | 10000 (UI 4041) | `org.apache.spark.sql.hive.thriftserver.HiveThriftServer2` | HiveServer2 sobre Spark SQL; recibe SQL de herramientas de BI |

**Dos drivers, un cluster, un catálogo.** Connect y Thrift son dos aplicaciones Spark independientes
(`spark.cores.max` 2 y 1) con la misma configuración: `conf/spark-defaults.conf`, el mismo
`spark.sql.warehouse.dir` y la misma URL del metastore. Cualquier tabla que escribe el pipeline es visible de
inmediato por SQL.

| | Spark Connect | Thrift JDBC/ODBC Server |
|---|---|---|
| Recibe | Planes de DataFrame (protobuf) | Texto SQL |
| Transporte | gRPC | Thrift (protocolo de HiveServer2) |
| Resultados | Lotes Apache Arrow | Filas por el protocolo de Hive |
| Clientes | CLI de pipelines, PySpark | Power BI, beeline, cualquier herramienta JDBC/ODBC |

## 3. Arranque y apagado

![PowerShell](https://img.shields.io/badge/PowerShell-5.1-5391FE?logo=powershell&logoColor=white)

`bin/start-cluster` levanta los procesos en orden de dependencia y espera a que cada puerto responda antes de
seguir. Es idempotente: si un proceso ya corre, lo saltea.

```mermaid
sequenceDiagram
    autonumber
    participant S as start-cluster.ps1
    participant D as Derby :1527
    participant M as Master :7077
    participant W as Worker
    participant C as Spark Connect :15002
    participant T as Thrift :10000

    S->>D: NetworkServerControl start
    D-->>S: puerto 1527 abierto
    S->>M: spark-class Master
    M-->>S: puerto 7077 abierto
    S->>W: spark-class Worker (3 núcleos, 3 GB)
    W->>M: registro
    S->>C: spark-submit SparkConnectServer (metastore en Derby)
    C->>D: conecta al catálogo
    C-->>S: puerto 15002 abierto
    S->>C: bootstrap_catalog.py → CREATE DATABASE IF NOT EXISTS retail
    S->>T: spark-submit HiveThriftServer2 (cores.max 1)
    T->>D: conecta al catálogo
    T-->>S: puerto 10000 abierto
```

`bin/stop-cluster` apaga en orden inverso: Thrift, Connect, worker, master, ejecutores huérfanos y, al final,
Derby con un apagado ordenado (`NetworkServerControl shutdown`), cuando ya no quedan clientes del catálogo.

## 4. Pipeline declarativo

![Spark Declarative Pipelines](https://img.shields.io/badge/Spark-Declarative%20Pipelines-E25A1C?logo=apachespark&logoColor=white)
![PySpark](https://img.shields.io/badge/PySpark-4.3-E25A1C?logo=apachespark&logoColor=white)

El pipeline `retail_lakehouse` se define en `pipelines/retail_lakehouse/`: una spec y 10 archivos de
transformaciones (Python y SQL) que declaran datasets. SDP arma el grafo de dependencias y ejecuta cada
dataset en orden.

### Spec portable

`spark-pipeline.yml` es una **plantilla**: las rutas absolutas que SDP exige (`storage`, raíces de landing y
export) se escriben como `${PROJECT_ROOT_URI}`. `bin/spark-pipelines` las resuelve para la máquina actual.

```mermaid
flowchart LR
    TPL["spark-pipeline.yml<br/><i>plantilla versionada</i>"]
    REN["New-PipelineSpec<br/><i>conf/spark-env.ps1</i>"]
    LOC["spark-pipeline.local.yml<br/><i>ignorado por Git</i>"]
    CLI["CLI de SDP<br/>(spark-pipelines run)"]
    CON["Spark Connect"]
    GRF["Grafo de datasets<br/>registrado y ejecutado"]

    TPL --> REN
    REN -- "${PROJECT_ROOT_URI} → file:///…" --> LOC
    LOC -- "--spec" --> CLI
    CLI -- "glob transformations/**" --> CON
    CON --> GRF
```

### Grafo de datasets

```mermaid
flowchart LR
    subgraph BRONZE["🥉 Bronze"]
        direction TB
        OWR["orders_web_raw"]
        OSR["orders_store_raw"]
        CCE["customers_cdc_events"]
    end

    subgraph SILVER["🥈 Silver"]
        direction TB
        ORD["orders"]
        CUS["customers"]
        HIS["customers_history"]
    end

    subgraph GOLD["🥇 Gold · modelo en estrella"]
        direction TB
        DCH["dim_channel"]
        DDT["dim_date"]
        DCU["dim_customer"]
        FOR["fact_orders"]
        FCC["fact_customer_changes"]
        ASC["agg_sales_by_country"]
        ADS["agg_daily_sales_by_channel"]
    end

    EXP[["orders_export"]]

    OWR --> ORD
    OSR --> ORD
    CCE -- "SCD1" --> CUS
    CCE -- "SCD2" --> HIS
    OWR --> EXP
    OSR --> EXP
    HIS --> DCU
    CCE -. "fecha de cierre" .-> DCU
    ORD --> DDT
    HIS --> DDT
    ORD --> FOR
    DCU --> FOR
    DCH --> FOR
    DCU --> FCC
    FOR --> ASC
    FOR --> ADS
    DDT --> ADS
```

| Capa | Dataset | Tipo SDP | Lenguaje | Lee de |
|---|---|---|---|---|
| bronze | `orders_web_raw` | streaming table | Python | `data/landing/orders_web/*.json` |
| bronze | `orders_store_raw` | streaming table | Python | `data/landing/orders_store/*.csv` |
| bronze | `customers_cdc_events` | streaming table | Python | `data/landing/customers_cdc/*.json` |
| silver | `orders` | materialized view | SQL | `orders_web_raw` ∪ `orders_store_raw` |
| silver | `customers` | materialized view | Python | `customers_cdc_events` (SCD1) |
| silver | `customers_history` | materialized view | Python | `customers_cdc_events` (SCD2) |
| gold · dimensión | `dim_channel` | materialized view | SQL | Lista fija de canales |
| gold · dimensión | `dim_date` | materialized view | SQL | Rango de fechas de `orders` y `customers_history` |
| gold · dimensión | `dim_customer` | materialized view | Python | `customers_history` (+ fecha de cierre de `customers_cdc_events`) |
| gold · hecho | `fact_orders` | materialized view | SQL | `orders` ⋈ `dim_customer` (versión vigente al comprar) ⋈ `dim_channel` |
| gold · hecho | `fact_customer_changes` | materialized view | Python | `dim_customer` (versión N-1 → N) |
| gold · agregado | `agg_sales_by_country` | materialized view | SQL | `fact_orders` + `dim_customer` |
| gold · agregado | `agg_daily_sales_by_channel` | materialized view | SQL | `fact_orders` + `dim_date` + `dim_channel` |
| exports | `orders_export` | sink + append flow | Python | `orders_web_raw` ∪ `orders_store_raw` (streaming) |

El código de gold está separado por lenguaje y por tipo de objeto: `gold/sql/{dimensions,facts,aggregates}` y
`gold/python/{dimensions,facts}`. El detalle del modelo está en [`data-model.md`](data-model.md).

## 5. Capa bronze: ingesta incremental

![Apache Spark](https://img.shields.io/badge/Apache%20Spark-4.3.0-E25A1C?logo=apachespark&logoColor=white)
![Parquet](https://img.shields.io/badge/Apache%20Parquet-tables-50ABF1?logo=apacheparquet&logoColor=white)

Cada fuente es un **streaming table** con esquema explícito (`src/retail_lakehouse/schemas.py`): Structured
Streaming no infiere esquemas en lecturas incrementales. El checkpoint de cada tabla vive en `storage/` y
registra qué archivos ya se procesaron, así que cada ejecución lee **solo los archivos nuevos**.

| Esquema | Columnas | Usado por |
|---|---|---|
| `ORDERS_SCHEMA` | `order_id` string · `customer_id` int · `amount` decimal(12,2) · `order_ts` timestamp | `orders_web_raw`, `orders_store_raw` |
| `CUSTOMERS_CDC_SCHEMA` | `customer_id` int · `name` · `email` · `country` · `op` (INSERT/UPDATE/DELETE) · `version` long · `event_ts` timestamp | `customers_cdc_events` |

Columnas agregadas en la ingesta:

| Columna | Tablas | Contenido |
|---|---|---|
| `channel` | pedidos | `web` o `store`, según la fuente |
| `_ingested_at` | todas | Momento de ingesta; desempata duplicados en silver |
| `_source_file` | `customers_cdc_events` | Archivo de origen (`_metadata.file_name`), para trazabilidad |

## 6. Capa silver: unión y CDC

![CDC](https://img.shields.io/badge/CDC-SCD1%20%7C%20SCD2-6A5ACD)

### Pedidos

`silver.orders` une los dos canales y elimina duplicados por `order_id`, quedándose con la primera ingesta
(`row_number() OVER (PARTITION BY order_id ORDER BY _ingested_at)`).

### Clientes: Change Data Capture

Los eventos de `customers_cdc_events` se aplican con `src/retail_lakehouse/cdc.py`, que reproduce la semántica
de `dp.create_auto_cdc_flow` (AUTO CDC) con los mismos parámetros:

```python
keys=["customer_id"], sequence_by="version", apply_as_deletes="op = 'DELETE'",
except_column_list=["op", "_ingested_at", "_source_file"]
```

```mermaid
flowchart TB
    EV["customers_cdc_events<br/><i>eventos en cualquier orden</i>"]
    SEQ["Validar secuencia<br/><i>sequence_by nulo → NULL_SEQUENCE</i>"]
    EV --> SEQ

    SEQ --> R1
    SEQ --> D2

    subgraph SCD1["apply_changes_scd1 → customers"]
        direction TB
        R1["row_number() por clave<br/>ordenado por versión desc"]
        L1["quedarse con rank = 1<br/><i>evento más reciente</i>"]
        X1["descartar si es DELETE"]
        R1 --> L1 --> X1
    end

    subgraph SCD2["apply_changes_scd2 → customers_history"]
        direction TB
        D2["quitar re-envíos<br/><i>misma clave y versión</i>"]
        V2["__START_AT = versión<br/>__END_AT = versión siguiente (lead)"]
        X2["descartar filas DELETE<br/><i>ya cerraron la versión previa</i>"]
        D2 --> V2 --> X2
    end

    X1 --> OUT1[("1 fila por cliente vigente")]
    X2 --> OUT2[("1 fila por versión")]
```

| Regla | Comportamiento |
|---|---|
| Inserts y updates | Por clave gana el evento con el `version` más alto |
| Deletes | SCD1: la clave desaparece · SCD2: la última versión se cierra sin crear una nueva |
| Eventos desordenados o repetidos | Convergen al mismo resultado |
| `version` nulo | Error `NULL_SEQUENCE`, igual que AUTO CDC |
| Empate de `version` en una clave | Se resuelve de forma arbitraria |

**Ejemplo real (cliente 3).** Los eventos llegan desordenados: la versión 2 aterriza en el lote 3, después
de la versión 3.

| Lote | Evento | Versión | País |
|---|---|---|---|
| 1 | INSERT | 1 | Uruguay |
| 2 | UPDATE | 3 | Brasil |
| 3 | UPDATE *(llega tarde)* | 2 | Paraguay |

Resultado:

| Tabla | Filas del cliente 3 |
|---|---|
| `customers` (SCD1) | Brasil, versión 3 (la versión 2 tardía no la pisa) |
| `customers_history` (SCD2) | Uruguay `[1, 2)` · Paraguay `[2, 3)` · Brasil `[3, vigente)` |

## 7. Capa gold y exportaciones

![Medallion](https://img.shields.io/badge/Arquitectura-Medallion%20(bronze%2Fsilver%2Fgold)-8B5A2B)

La capa gold es un **modelo dimensional (esquema en estrella)**: dimensiones, hechos y agregados derivados de
los hechos. El detalle completo (diagrama, matriz de bus, granos, convenciones y controles de calidad) está en
[`data-model.md`](data-model.md).

| Tipo | Dataset | Grano |
|---|---|---|
| Dimensión | `dim_customer` | Una versión de un cliente (SCD2 con vigencia por fecha) |
| Dimensión | `dim_date` | Un día |
| Dimensión | `dim_channel` | Un canal |
| Hecho | `fact_orders` | Un pedido, unido a la versión del cliente vigente al comprar |
| Hecho | `fact_customer_changes` | Un cambio de versión de un cliente |
| Agregado | `agg_sales_by_country` | Un país (actual) del cliente |
| Agregado | `agg_daily_sales_by_channel` | Un día × un canal |

Claves sustitutas determinísticas (`xxhash64`), miembro desconocido `-1` en cada dimensión y 7 controles de
calidad que se corren con `bin/check-quality`.

**Exportaciones.** `orders_export` es un **sink** de Structured Streaming (en producción sería Kafka o Event Hubs;
aquí, archivos JSON en `data/export/orders`). Un único append flow une los dos canales y cada ejecución exporta
solo los pedidos nuevos.

## 8. Consumo: Thrift Server y Power BI

![Power BI](https://img.shields.io/badge/Power%20BI-PBIP%20%2F%20TMDL-F2C811?logo=powerbi&logoColor=black)
![Thrift](https://img.shields.io/badge/Thrift-JDBC%2FODBC%2010000-555555?logo=apache&logoColor=white)

El reporte `bi/powerbi/RetailLakehouse.pbip` es un proyecto PBIP con modelo **TMDL** (generado por
`bi/powerbi/tools/generate_model.py`) y reporte **PBIR** (creado con el CLI `pbir`).

```mermaid
sequenceDiagram
    participant PBI as Power BI Desktop
    participant ODBC as Driver ODBC Spark (Simba)
    participant THR as Thrift Server :10000
    participant MS as Metastore (Derby)
    participant EX as Ejecutores
    participant WH as warehouse/*.parquet

    PBI->>ODBC: ApacheSpark.Tables("127.0.0.1:10000", Standard)
    ODBC->>THR: SQL por Thrift (usuario/contraseña sin validar)
    THR->>MS: resolver retail.<tabla>
    THR->>EX: plan de Spark SQL
    EX->>WH: leer Parquet
    EX-->>THR: filas
    THR-->>PBI: resultados → modelo en modo importación
```

### Modelo semántico

```mermaid
erDiagram
    customers ||--o{ orders : "customer_id"
    customers ||--o{ customers_history : "customer_id"

    customers {
        int64 customer_id PK
        string name
        string email
        string country
        int64 version
        dateTime event_ts
    }
    orders {
        string order_id PK
        int64 customer_id FK
        decimal amount
        dateTime order_ts
        string channel
    }
    customers_history {
        int64 customer_id FK
        int64 version
        int64 __START_AT
        int64 __END_AT
        string Estado
    }
    sales_by_country {
        string country
        int64 orders
        decimal total_amount
    }
    daily_sales_by_channel {
        dateTime order_date
        string channel
        decimal total_amount
    }
```

| Tabla | Medidas |
|---|---|
| `orders` | Ventas totales · Pedidos · Clientes con compras · Ticket promedio |
| `customers` | Clientes actuales |
| `customers_history` | Versiones · Cambios registrados (+ columna calculada `Estado`: Vigente / Histórica) |
| `sales_by_country` | Ventas por país |
| `daily_sales_by_channel` | Ventas diarias |

Las tablas gold del reporte (`sales_by_country`, `daily_sales_by_channel`) leen de los agregados
`agg_sales_by_country` y `agg_daily_sales_by_channel` (campo `source` de `model.json`) y no se relacionan con el
resto: ya están agregadas. Los reportes nuevos pueden usar directamente la estrella (`fact_*` + `dim_*`). El servidor (`SparkServer`) es un parámetro
de Power Query, así que apuntar el reporte a otro Thrift Server no requiere tocar las tablas.

## 9. Almacenamiento y estado

![Parquet](https://img.shields.io/badge/Apache%20Parquet-tables-50ABF1?logo=apacheparquet&logoColor=white)
![Hive Metastore](https://img.shields.io/badge/Hive%20Metastore-Derby-FDEE21?logo=apachehive&logoColor=black)

| Carpeta | Contenido | En Git | Se regenera con |
|---|---|---|---|
| `warehouse/retail.db/` | Archivos Parquet de cada tabla | No | `spark-pipelines run` |
| `metastore_db/` | Catálogo Hive (Derby): tablas, esquemas, ubicaciones | No | `start-cluster` (vacío) + pipeline |
| `storage/` | Checkpoints de los streaming tables | No | `spark-pipelines run` |
| `data/landing/` | Archivos aterrizados | No | `land-batch` |
| `data/export/` | Salida del sink | No | `spark-pipelines run` |
| `logs/`, `work/` | Logs de procesos y directorios de trabajo de Spark | No | Cada arranque |
| `tools/derby/` | Jars de Derby (red y cliente) | No | `setup-dependencies` |

El catálogo guarda la **ruta absoluta** de cada tabla: mover `warehouse/` rompe las tablas. Para empezar de cero,
`bin/reset-pipeline` borra todo el estado y reinicia el cluster.

## 10. Seguridad

![Thrift](https://img.shields.io/badge/Thrift-JDBC%2FODBC%2010000-555555?logo=apache&logoColor=white)

Configuración de **desarrollo local**:

- Todos los servicios escuchan solo en `127.0.0.1`: no son accesibles desde la red.
- El Thrift Server usa autenticación `NONE`: el cliente debe enviar usuario y contraseña, pero no se validan.
- Derby y Spark Connect no tienen autenticación.
- Los jars de terceros se descargan de Maven Central y se verifica su SHA-1 (`bin/setup-dependencies`).
- El repositorio no contiene credenciales ni rutas de una máquina en particular (spec en plantilla).

## 11. Decisiones de diseño

| Decisión | Motivo | Consecuencia |
|---|---|---|
| Tablas **Parquet** | Iceberg no tiene runtime para Spark 4.3 | Dos flows no pueden escribir al mismo target: un streaming table por canal y unión en silver |
| CDC en **materialized views** (`cdc.py`) | AUTO CDC necesita un catálogo con operaciones a nivel fila | Mismos parámetros que AUTO CDC: migrar es cambiar una llamada |
| **Derby en modo red** | Derby embebido admite una sola JVM | Connect y Thrift comparten el catálogo |
| **Spec como plantilla** | SDP exige rutas absolutas | El repo funciona en cualquier máquina |
| **Thrift Server** para BI | Power BI no habla Spark Connect | Power BI usa su conector nativo de Spark por ODBC |
| Modelo **TMDL generado** | Tipos y medidas reproducibles desde código | `lineageTag` determinísticos: regenerar no cambia la identidad de los objetos |

## 12. Camino a producción

![Apache Iceberg](https://img.shields.io/badge/Apache%20Iceberg-tablas-4E8EE9?logo=apache&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-metastore-4169E1?logo=postgresql&logoColor=white)
![Kubernetes](https://img.shields.io/badge/Kubernetes-Spark%20on%20K8s-326CE5?logo=kubernetes&logoColor=white)
![Apache Airflow](https://img.shields.io/badge/Apache%20Airflow-orquestaci%C3%B3n-017CEE?logo=apacheairflow&logoColor=white)

```mermaid
flowchart LR
    subgraph CLOUD["Nube / centro de datos"]
        direction LR
        ORQ["Orquestador<br/>(Airflow / Dagster)"]
        subgraph K8S["Kubernetes"]
            direction TB
            DRV["Drivers Spark<br/>Connect · Thrift"]
            EXE["Ejecutores"]
        end
        MS[("Metastore<br/>PostgreSQL · Glue · Unity Catalog")]
        LAKE[("Data lake S3 / ADLS<br/>Iceberg o Delta")]
        GW["On-premises<br/>data gateway"]
    end
    SVC{{"Power BI Service"}}

    ORQ -- "spark-pipelines run" --> DRV
    DRV --> EXE
    EXE --> LAKE
    DRV -. "catálogo" .-> MS
    SVC -- "refresco programado" --> GW
    GW -- "ODBC + TLS + LDAP" --> DRV
```

| Hoy (local) | Producción |
|---|---|
| Disco local | Almacenamiento de objetos (S3, ADLS, GCS) |
| Parquet | Apache Iceberg o Delta Lake (transacciones, `MERGE`, AUTO CDC) |
| Derby | Metastore en PostgreSQL/MySQL gestionado, Unity Catalog o AWS Glue |
| Standalone en una máquina | Kubernetes (Spark on K8s) o YARN |
| Thrift sin autenticación en `127.0.0.1` | Thrift con LDAP/Kerberos y TLS, en red privada |
| Ejecución manual | Orquestador (Airflow, Dagster) |
| Power BI Desktop | Power BI Service + On-premises data gateway |

Alternativa habitual: una plataforma gestionada (Databricks, Microsoft Fabric, Synapse, EMR) que ya resuelve
cómputo, catálogo, almacenamiento y endpoint SQL. Las transformaciones del pipeline se trasladan sin cambios de
lógica.
