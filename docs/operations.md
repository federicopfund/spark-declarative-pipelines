# Operación

Todos los scripts están en `bin/`. Cada `.cmd` llama al `.ps1` del mismo nombre; los dos cargan el entorno desde
`conf/spark-env.ps1` (`SPARK_HOME`, `HADOOP_HOME`, `.venv`, rutas del proyecto).

## Scripts

| Script | Qué hace |
|---|---|
| `setup-dependencies` | Descarga los jars de Derby (servidor de red y cliente) a `tools/derby/` y verifica su SHA-1. |
| `start-cluster [-WorkerCores 3] [-WorkerMemory 3g] [-NoThrift]` | Levanta Derby, master, worker, Spark Connect, crea la base `retail` y levanta el Thrift Server. Es idempotente. |
| `stop-cluster` | Detiene Thrift, Connect, worker, master y por último Derby (apagado ordenado). |
| `land-batch -Batch N [-Reset]` | Copia `data/samples/batch-00N` a `data/landing/`. `-Reset` vacía landing y export. |
| `spark-pipelines run` / `dry-run` | CLI de SDP contra Spark Connect. Renderiza la spec (plantilla) y acepta las opciones de `spark-pipelines` (`--refresh`, `--full-refresh`, ...). |
| `query-lakehouse [tablas...]` | Muestra las tablas del pipeline por Spark Connect. |
| `reset-pipeline` | Borra todo el estado (tablas, checkpoints, metastore, landing, export) y reinicia el cluster. |

## Logs y UIs

- Logs: `logs/<proceso>.log` (`derby`, `master`, `worker`, `connect-server`, `thrift-server`).
- Master UI: http://127.0.0.1:8080 · Spark Connect: http://127.0.0.1:4040 · Thrift: http://127.0.0.1:4041

## Consultas SQL por el Thrift Server

```powershell
& "$env:SPARK_HOME\bin\beeline.cmd" -u jdbc:hive2://127.0.0.1:10000 -n powerbi -p powerbi
```

Usuario y contraseña son obligatorios para el cliente pero el servidor no los valida (autenticación `NONE`).
Sin `-p`, beeline se queda esperando la contraseña por teclado.

## Power BI

1. Con el cluster levantado, abrir `bi/powerbi/RetailLakehouse.pbip` en Power BI Desktop 2.159 o posterior.
2. **Actualizar**. En credenciales elegir *Nombre de usuario y contraseña* (cualquier valor) y, si lo pide,
   aceptar la conexión sin cifrar.

Errores conocidos:

| Error | Causa | Solución |
|---|---|---|
| *Report is using the PBIR format. Please enable the preview feature…* | Formato PBIR desactivado | Opciones → Características en versión preliminar → *Store reports using enhanced metadata format (PBIR)*; reiniciar Desktop. |
| *Can't resolve schema '3.3.0' in 'report.json'* | Power BI Desktop anterior a 2026 | Actualizar Desktop. Si conviven la versión de Microsoft Store y la instalada (MSI), abrir con la nueva: `C:\Program Files\Microsoft Power BI Desktop\bin\PBIDesktop.exe`. |

### Regenerar el modelo semántico

El TMDL se genera desde `bi/powerbi/tools/generate_model.py` (tablas, tipos, medidas, relaciones). Los `lineageTag`
son determinísticos, así que regenerar no cambia la identidad de los objetos:

```powershell
.venv\Scripts\python bi\powerbi\tools\generate_model.py
```

Los visuales se crearon con el CLI `pbir` a partir de `bi/powerbi/tools/visuals-*.json`.
