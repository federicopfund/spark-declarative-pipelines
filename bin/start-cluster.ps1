<#
.SYNOPSIS
    Levanta el metastore Derby (modo red), el cluster Spark Standalone (master + worker),
    el servidor Spark Connect y el Thrift JDBC/ODBC Server.

.DESCRIPTION
    Equivalente en Windows a sbin/start-master.sh, sbin/start-worker.sh, sbin/start-connect-server.sh
    y sbin/start-thriftserver.sh (esos scripts son solo para bash). Cada proceso corre en segundo plano
    y escribe en logs\.

      Derby (metastore)  127.0.0.1:1527          catalogo Hive compartido por Connect y Thrift
      Master UI          http://127.0.0.1:8080
      Worker UI          http://127.0.0.1:8081
      Spark Connect      sc://127.0.0.1:15002    pipelines y clientes PySpark
      Thrift Server      jdbc:hive2://127.0.0.1:10000   Power BI (conector Spark, protocolo Standard)
      Driver UIs         http://127.0.0.1:4040 (Connect), :4041 (Thrift)

.PARAMETER WorkerCores
    Nucleos que el worker ofrece al cluster (tu i3 tiene 4 hilos): 2 para Connect + 1 para Thrift.

.PARAMETER WorkerMemory
    Memoria que el worker ofrece a los ejecutores (1g por ejecutor).

.PARAMETER NoThrift
    No levanta el Thrift Server (solo pipelines por Spark Connect).
#>
param(
    [int]$WorkerCores = 3,
    [string]$WorkerMemory = '3g',
    [switch]$NoThrift
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\conf\spark-env.ps1')

function Start-SparkDaemon([string]$Name, [string]$MainClass, [string]$Command, [int]$Port) {
    if (Get-SparkDaemon $MainClass) { Write-Host "    [=] $Name already running" -ForegroundColor DarkGray; return }
    $log = Join-Path $LogDir "$Name.log"
    # cmd /c quita la primera y la ultima comilla: se envuelve todo en un par extra
    Start-Process cmd.exe -ArgumentList '/c', "`"$Command > `"$log`" 2>&1`"" -WindowStyle Hidden -WorkingDirectory $ProjectRoot | Out-Null
    if (Wait-TcpPort $Port) { Write-Host "    [OK] $Name (port $Port)  log: logs\$Name.log" -ForegroundColor Green }
    else { throw "$Name did not start. See $log" }
}

$java        = if ($env:JAVA_HOME) { "`"$(Join-Path $env:JAVA_HOME 'bin\java.exe')`"" } else { 'java' }
$sparkClass  = "`"$env:SPARK_HOME\bin\spark-class.cmd`""
$sparkSubmit = "`"$env:SPARK_HOME\bin\spark-submit.cmd`""
$env:SPARK_DAEMON_JAVA_OPTS = $Log4jOptions

Write-Host '==> Metastore (Derby network server)' -ForegroundColor Cyan
$derbyHome = Join-Path $LogDir 'derby'
New-Item -ItemType Directory -Force $derbyHome | Out-Null
Start-SparkDaemon 'derby' 'org.apache.derby.drda.NetworkServerControl' (
    "$java -cp `"$DerbyServerJars`" -Dderby.system.home=`"$derbyHome`" " +
    "org.apache.derby.drda.NetworkServerControl start -h 127.0.0.1 -p $DerbyPort -noSecurityManager"
) $DerbyPort

Write-Host '==> Spark Standalone' -ForegroundColor Cyan
Start-SparkDaemon 'master' 'org.apache.spark.deploy.master.Master' `
    "$sparkClass org.apache.spark.deploy.master.Master --host 127.0.0.1 --port 7077 --webui-port 8080" 7077

Start-SparkDaemon 'worker' 'org.apache.spark.deploy.worker.Worker' `
    "$sparkClass org.apache.spark.deploy.worker.Worker $MasterUrl --host 127.0.0.1 --webui-port 8081 --cores $WorkerCores --memory $WorkerMemory --work-dir `"$ProjectRoot\work\worker`"" 8081

# Opciones comunes a los dos drivers (Connect y Thrift): mismo cluster, warehouse y metastore
$jarsArg   = if ($ExtraJars) { "--jars `"$ExtraJars`" " } else { '' }
$driverArgs = (
    "--properties-file `"$ProjectRoot\conf\spark-defaults.conf`" " +
    $jarsArg +
    "--driver-class-path `"$DerbyClientJar`" " +
    "--driver-java-options `"$Log4jOptions`" " +
    "--conf spark.sql.warehouse.dir=$WarehouseUri " +
    "--conf `"spark.hadoop.javax.jdo.option.ConnectionURL=$MetastoreUrl`" " +
    "--conf spark.hadoop.javax.jdo.option.ConnectionDriverName=$MetastoreDriver "
)

Write-Host '==> Spark Connect server' -ForegroundColor Cyan
Start-SparkDaemon 'connect-server' 'org.apache.spark.sql.connect.service.SparkConnectServer' (
    "$sparkSubmit --class org.apache.spark.sql.connect.service.SparkConnectServer --name `"Spark Connect server`" " +
    $driverArgs
) 15002

Write-Host '==> Catalog' -ForegroundColor Cyan
& $PythonExe (Join-Path $ProjectRoot 'clients\bootstrap_catalog.py') --remote $ConnectUrl
if ($LASTEXITCODE -ne 0) { throw 'Could not create the pipeline database.' }

if (-not $NoThrift) {
    Write-Host '==> Thrift JDBC/ODBC server' -ForegroundColor Cyan
    # spark-internal = sin JAR de aplicacion (la clase viene con Spark); lo que sigue son --hiveconf del servidor.
    # cores.max 1: deja 2 nucleos del worker para el servidor Connect.
    Start-SparkDaemon 'thrift-server' 'org.apache.spark.sql.hive.thriftserver.HiveThriftServer2' (
        "$sparkSubmit --class org.apache.spark.sql.hive.thriftserver.HiveThriftServer2 --name `"Thrift JDBC/ODBC server`" " +
        $driverArgs +
        "--conf spark.cores.max=1 " +
        "spark-internal " +
        "--hiveconf hive.server2.thrift.bind.host=127.0.0.1 --hiveconf hive.server2.thrift.port=$ThriftPort"
    ) $ThriftPort
}

Write-Host "`n    Master UI   http://127.0.0.1:8080"
Write-Host "    Connect     $ConnectUrl"
if (-not $NoThrift) { Write-Host "    Thrift      $ThriftUrl   (Power BI: Spark, servidor 127.0.0.1:$ThriftPort, protocolo Standard)" }
