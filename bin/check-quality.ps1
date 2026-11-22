<#
.SYNOPSIS
    Corre los controles de calidad del modelo dimensional (clients\check_quality.py).

.EXAMPLE
    bin\check-quality.cmd
    bin\check-quality.cmd 01 05
#>
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\conf\spark-env.ps1')
if (-not (Wait-TcpPort 15002 3)) { throw "Spark Connect server is not running at $ConnectUrl. Start it with bin\start-cluster.cmd" }
& $PythonExe (Join-Path $ProjectRoot 'clients\check_quality.py') --remote $ConnectUrl @args
exit $LASTEXITCODE
