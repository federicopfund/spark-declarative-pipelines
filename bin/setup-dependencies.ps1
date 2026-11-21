<#
.SYNOPSIS
    Descarga los jars que el proyecto necesita y no vienen con Spark (no se versionan en Git).

.DESCRIPTION
    Spark 4.3.0 trae Derby 10.16.1.1 embebido pero no su servidor de red ni su driver cliente.
    Este script los baja de Maven Central a tools\derby\ y verifica su SHA-1.
    Es idempotente: si el jar ya esta y su hash coincide, no lo vuelve a bajar.

      bin\setup-dependencies.cmd
#>
$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

$deps = @(
    @{ Group = 'org/apache/derby'; Artifact = 'derbynet';    Version = '10.16.1.1'; Sha1 = '7ebe74967de9f325ac382887e9cdbfdbe639a84c'; Dir = 'tools\derby' }
    @{ Group = 'org/apache/derby'; Artifact = 'derbyclient'; Version = '10.16.1.1'; Sha1 = '9d6bd93a3d742d8f3a978205c79e68d82b77cd5d'; Dir = 'tools\derby' }
)

function Get-Sha1([string]$Path) { (Get-FileHash -Algorithm SHA1 $Path).Hash.ToLowerInvariant() }

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
Write-Host '==> Dependencies' -ForegroundColor Cyan
foreach ($d in $deps) {
    $dir  = Join-Path $ProjectRoot $d.Dir
    $name = "$($d.Artifact)-$($d.Version).jar"
    $file = Join-Path $dir $name
    New-Item -ItemType Directory -Force $dir | Out-Null

    if ((Test-Path $file) -and (Get-Sha1 $file) -eq $d.Sha1) {
        Write-Host "    [=] $name already present" -ForegroundColor DarkGray
        continue
    }
    $url = "https://repo1.maven.org/maven2/$($d.Group)/$($d.Artifact)/$($d.Version)/$name"
    Invoke-WebRequest -Uri $url -OutFile $file -UseBasicParsing
    $got = Get-Sha1 $file
    if ($got -ne $d.Sha1) {
        Remove-Item $file -Force
        throw "SHA-1 mismatch for ${name}: expected $($d.Sha1), got $got"
    }
    Write-Host "    [OK] $name  sha1=$got" -ForegroundColor Green
}
