<#
.SYNOPSIS
    Aterriza un lote de datos de ejemplo en data\landing\ (simula archivos que llegan).

.PARAMETER Batch
    Numero de lote de data\samples\batch-NNN.

.PARAMETER Reset
    Vacia data\landing\ y data\export\ antes de aterrizar (usar junto con --full-refresh-all).

.EXAMPLE
    bin\land-batch.cmd -Batch 1
    bin\land-batch.cmd -Batch 1 -Reset
#>
param(
    [Parameter(Mandatory)][ValidateRange(1, 999)][int]$Batch,
    [switch]$Reset
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\conf\spark-env.ps1')

$landing = Join-Path $ProjectRoot 'data\landing'
$source  = Join-Path $ProjectRoot ('data\samples\batch-{0:D3}' -f $Batch)
if (-not (Test-Path $source)) { throw "Batch not found: $source" }

if ($Reset) {
    foreach ($dir in $landing, (Join-Path $ProjectRoot 'data\export')) {
        if (Test-Path $dir) { Get-ChildItem $dir -Force | Remove-Item -Recurse -Force }
    }
    Write-Host '    [OK] landing and export emptied' -ForegroundColor Green
}

Get-ChildItem $source -Directory | ForEach-Object {
    $target = Join-Path $landing $_.Name
    New-Item -ItemType Directory -Force $target | Out-Null
    Get-ChildItem $_.FullName -File | ForEach-Object {
        Copy-Item $_.FullName (Join-Path $target $_.Name) -Force
        Write-Host ("    [OK] {0}\{1}" -f (Split-Path $target -Leaf), $_.Name) -ForegroundColor Green
    }
}
