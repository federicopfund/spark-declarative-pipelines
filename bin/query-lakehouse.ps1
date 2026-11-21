<#
.SYNOPSIS
    Consulta las tablas del pipeline por Spark Connect (clients\query_lakehouse.py).

.EXAMPLE
    bin\query-lakehouse.cmd
    bin\query-lakehouse.cmd customers customers_history
#>
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\conf\spark-env.ps1')
if (-not (Wait-TcpPort 15002 3)) { throw "Spark Connect server is not running at $ConnectUrl. Start it with bin\start-cluster.cmd" }
& $PythonExe (Join-Path $ProjectRoot 'clients\query_lakehouse.py') --remote $ConnectUrl @args
exit $LASTEXITCODE
