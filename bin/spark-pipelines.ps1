<#
.SYNOPSIS
    Port para Windows de $SPARK_HOME/bin/spark-pipelines (ese script es solo para bash).

.DESCRIPTION
    Ejecuta la CLI de Spark Declarative Pipelines contra el servidor Spark Connect del cluster local.
    Acepta los mismos comandos y opciones que spark-pipelines:

      bin\spark-pipelines dry-run
      bin\spark-pipelines run
      bin\spark-pipelines run --refresh customers
      bin\spark-pipelines run --full-refresh customers_cdc_events,customers
      bin\spark-pipelines run --full-refresh-all

    Si no se pasa --spec, usa pipelines\retail_lakehouse\spark-pipeline.yml: es una plantilla con
    ${PROJECT_ROOT_URI}; se renderiza en spark-pipeline.local.yml (misma carpeta, ignorado por Git).
    Si no se pasa --remote, usa el servidor Connect local (sc://127.0.0.1:15002).
#>
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\conf\spark-env.ps1')

$cliArgs = @($args)
if ($cliArgs.Count -eq 0) { $cliArgs = @('--help') }
$command = $cliArgs[0]

if ($command -in 'run', 'dry-run') {
    if ($cliArgs -notcontains '--spec')   { $cliArgs += @('--spec', (New-PipelineSpec)) }
    if ($cliArgs -notcontains '--remote') { $cliArgs += @('--remote', $ConnectUrl) }
    if ($cliArgs -contains $ConnectUrl -and -not (Wait-TcpPort 15002 3)) {
        throw "Spark Connect server is not running at $ConnectUrl. Start it with bin\start-cluster.cmd"
    }
}

# Igual que el script de bash: ubicar cli.py dentro del PySpark de SPARK_HOME
$cliPy = & $PythonExe -c "import os, pyspark; print(os.path.join(os.path.dirname(pyspark.__file__), 'pipelines', 'cli.py'))"
if (-not (Test-Path $cliPy)) { throw "SDP CLI not found: $cliPy" }

Push-Location $ProjectRoot
try {
    & "$env:SPARK_HOME\bin\spark-class.cmd" org.apache.spark.deploy.SparkPipelines $cliPy @cliArgs
    exit $LASTEXITCODE
} finally { Pop-Location }
