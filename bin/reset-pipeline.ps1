<#
.SYNOPSIS
    Borra todo el estado del pipeline (tablas, checkpoints, metastore, aterrizajes) y reinicia el cluster.

.DESCRIPTION
    Reemplaza a `spark-pipelines run --full-refresh-all` con tablas Parquet: SDP lista los archivos
    de las tablas al analizar el grafo, antes de vaciarlas, y los materialized views terminan leyendo
    archivos borrados (FAILED_READ_FILE.FILE_NOT_EXIST). Con Iceberg o Delta no hace falta.

    Solo borra carpetas generadas por el pipeline. data\samples\ no se toca.
#>
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\conf\spark-env.ps1')

& (Join-Path $PSScriptRoot 'stop-cluster.ps1')

foreach ($dir in 'warehouse', 'storage', 'data\landing', 'data\export', 'work') {
    $path = Join-Path $ProjectRoot $dir
    if (Test-Path $path) { Get-ChildItem $path -Force | Remove-Item -Recurse -Force }
}
# Derby no crea una base dentro de una carpeta existente: se borra la carpeta entera
$metastore = Join-Path $ProjectRoot 'metastore_db'
if (Test-Path $metastore) { Remove-Item $metastore -Recurse -Force }
Write-Host '    [OK] pipeline state removed' -ForegroundColor Green

& (Join-Path $PSScriptRoot 'start-cluster.ps1')
