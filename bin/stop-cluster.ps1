<#
.SYNOPSIS
    Detiene el Thrift Server, el servidor Spark Connect, el worker, el master y, al final, el metastore Derby.
#>
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\conf\spark-env.ps1')

$daemons = [ordered]@{
    'thrift-server'  = 'org.apache.spark.sql.hive.thriftserver.HiveThriftServer2'
    'connect-server' = 'org.apache.spark.sql.connect.service.SparkConnectServer'
    'worker'         = 'org.apache.spark.deploy.worker.Worker'
    'master'         = 'org.apache.spark.deploy.master.Master'
}
foreach ($name in $daemons.Keys) {
    $procs = Get-SparkDaemon $daemons[$name]
    if (-not $procs) { Write-Host "    [=] $name not running" -ForegroundColor DarkGray; continue }
    foreach ($p in $procs) { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue }
    Write-Host "    [OK] $name stopped" -ForegroundColor Green
}
# Ejecutores que hayan quedado huerfanos
Get-SparkDaemon 'org.apache.spark.executor.CoarseGrainedExecutorBackend' |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

# Derby al final, cuando ya no quedan clientes. Apagado ordenado (cierra la base limpia); si no responde, se mata.
$derby = Get-SparkDaemon 'org.apache.derby.drda.NetworkServerControl'
if (-not $derby) { Write-Host '    [=] derby not running' -ForegroundColor DarkGray }
else {
    $java = if ($env:JAVA_HOME) { Join-Path $env:JAVA_HOME 'bin\java.exe' } else { 'java' }
    # Start-Process y no "& java ... 2>&1": en PowerShell 5.1 con ErrorActionPreference=Stop, el stderr de un
    # ejecutable nativo redirigido corta el script.
    Start-Process $java -ArgumentList '-cp', "`"$DerbyServerJars`"", 'org.apache.derby.drda.NetworkServerControl',
        'shutdown', '-h', '127.0.0.1', '-p', $DerbyPort -WindowStyle Hidden -Wait
    Start-Sleep -Seconds 2
    Get-SparkDaemon 'org.apache.derby.drda.NetworkServerControl' |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Write-Host '    [OK] derby stopped' -ForegroundColor Green
}
