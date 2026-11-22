# spark-env.ps1 - entorno del proyecto (equivalente en PowerShell a $SPARK_HOME/conf/spark-env.sh).
# Lo cargan los scripts de bin\ con dot-sourcing.

$env:SPARK_HOME  = [Environment]::GetEnvironmentVariable('SPARK_HOME', 'User')
$env:HADOOP_HOME = [Environment]::GetEnvironmentVariable('HADOOP_HOME', 'User')
if (-not $env:SPARK_HOME) { throw 'SPARK_HOME is not set. Install Spark with tools\instalar_spark.ps1.' }
if ($env:HADOOP_HOME) { $env:Path = "$env:HADOOP_HOME\bin;$env:Path" }

$script:ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$script:PythonExe   = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $PythonExe)) { throw "Virtualenv not found: $PythonExe" }

# PySpark: el que trae la distribucion de Spark (misma version que el servidor)
$env:PYSPARK_PYTHON        = $PythonExe
$env:PYSPARK_DRIVER_PYTHON = $PythonExe
# + src\ : paquete retail_lakehouse (helpers compartidos por las transformaciones)
$env:PYTHONPATH  = "$ProjectRoot\src;$env:SPARK_HOME\python;" + (Get-ChildItem "$env:SPARK_HOME\python\lib" -Filter 'py4j-*-src.zip' | Select-Object -First 1).FullName
$env:Path        = "$(Split-Path $PythonExe);$env:SPARK_HOME\bin;$env:Path"

# Spark en Windows: sin esto, el worker y los ejecutores usan otra carpeta temporal
$env:SPARK_LOCAL_DIRS = Join-Path $ProjectRoot 'work\local'

$script:LogDir        = Join-Path $ProjectRoot 'logs'
$script:WarehouseUri  = ([Uri](Join-Path $ProjectRoot 'warehouse')).AbsoluteUri
# Metastore Hive en Derby *modo red* (no embebido): asi el servidor Connect y el Thrift Server
# comparten el mismo catalogo. Derby embebido solo admite una JVM a la vez.
$script:DerbyPort       = 1527
$script:DerbyServerJars = (@(
        (Get-ChildItem "$env:SPARK_HOME\jars" -Filter 'derby*.jar' | ForEach-Object FullName)
        (Get-ChildItem (Join-Path $ProjectRoot 'tools\derby') -Filter 'derbynet-*.jar' | ForEach-Object FullName)
    ) -join ';')
$script:DerbyClientJar  = (Get-ChildItem (Join-Path $ProjectRoot 'tools\derby') -Filter 'derbyclient-*.jar' | Select-Object -First 1).FullName
if (-not $DerbyClientJar) { throw 'Derby client not found in tools\derby. Run bin\setup-dependencies.cmd first.' }
$script:MetastoreUrl    = "jdbc:derby://127.0.0.1:$DerbyPort/" + ((Join-Path $ProjectRoot 'metastore_db') -replace '\\', '/') + ';create=true'
$script:MetastoreDriver = 'org.apache.derby.jdbc.ClientDriver'
$script:Log4jOptions  = '-Dlog4j2.configurationFile=' + ([Uri](Join-Path $ProjectRoot 'conf\log4j2.properties')).AbsoluteUri
$script:ExtraJars     = (Get-ChildItem (Join-Path $ProjectRoot 'jars') -Filter '*.jar' | ForEach-Object FullName) -join ','

$script:MasterUrl     = 'spark://127.0.0.1:7077'
$script:ConnectUrl    = 'sc://127.0.0.1:15002'
# Thrift JDBC/ODBC Server (HiveServer2): la puerta de entrada de Power BI y otras herramientas de BI
$script:ThriftPort    = 10000
$script:ThriftUrl     = "jdbc:hive2://127.0.0.1:$ThriftPort"

foreach ($d in 'logs', 'work\local', 'warehouse', 'storage', 'data\landing') {
    New-Item -ItemType Directory -Force (Join-Path $ProjectRoot $d) | Out-Null
}

# Pipeline: la spec versionada es una plantilla; ${PROJECT_ROOT_URI} se resuelve por maquina
$script:PipelineDir      = Join-Path $ProjectRoot 'pipelines\retail_lakehouse'
$script:PipelineTemplate = Join-Path $PipelineDir 'spark-pipeline.yml'

function New-PipelineSpec {
    # Escribe spark-pipeline.local.yml junto a la plantilla (el glob transformations/** es relativo a la spec)
    $rootUri = ([Uri]$ProjectRoot).AbsoluteUri.TrimEnd('/')
    $spec = Join-Path $PipelineDir 'spark-pipeline.local.yml'
    $text = (Get-Content $PipelineTemplate -Raw -Encoding UTF8).Replace('${PROJECT_ROOT_URI}', $rootUri)
    [IO.File]::WriteAllText($spec, $text, (New-Object Text.UTF8Encoding $false))
    return $spec
}

function Invoke-Beeline([string[]]$Statements) {
    # Corre sentencias SQL en el Thrift Server con beeline. Start-Process y archivos (no "& ... 2>&1"):
    # en PowerShell 5.1 el stderr redirigido de un ejecutable corta el script. Sin -p, beeline espera la clave.
    $sql = [IO.Path]::GetTempFileName(); $out = [IO.Path]::GetTempFileName()
    [IO.File]::WriteAllText($sql, ($Statements -join ";`n") + ";`n", (New-Object Text.UTF8Encoding $false))
    $beeline = "$env:SPARK_HOME\bin\beeline.cmd"
    Start-Process cmd.exe -ArgumentList '/c', "`"`"$beeline`" -u $ThriftUrl -n pipeline -p pipeline --silent=true --outputformat=csv2 -f `"$sql`" < NUL > `"$out`" 2>&1`"" `
        -WindowStyle Hidden -Wait
    $lines = Get-Content $out | Where-Object { $_ -and $_ -notmatch 'SLF4J|incubator' }
    Remove-Item $sql, $out -Force
    return $lines
}

function Update-ThriftCache {
    # El Thrift Server cachea que archivos Parquet forman cada tabla. El pipeline reescribe las tablas en cada
    # corrida, asi que sin REFRESH una consulta (p. ej. Power BI) puede buscar archivos ya borrados
    # (FAILED_READ_FILE.FILE_NOT_EXIST).
    if (-not (Wait-TcpPort $ThriftPort 2)) { Write-Host '    [=] thrift-server not running: cache refresh skipped' -ForegroundColor DarkGray; return }
    $tables = Invoke-Beeline @('SHOW TABLES IN retail') |
        Where-Object { $_ -match '^retail,([^,]+),false$' } | ForEach-Object { $Matches[1] }
    if (-not $tables) { Write-Host '    [!] no tables found in retail' -ForegroundColor Yellow; return }
    Invoke-Beeline @($tables | ForEach-Object { "REFRESH TABLE retail.$_" }) | Out-Null
    Write-Host "    [OK] thrift-server cache refreshed ($(@($tables).Count) tables)" -ForegroundColor Green
}

function Get-SparkDaemon([string]$MainClass) {
    Get-CimInstance Win32_Process -Filter "Name = 'java.exe'" |
        Where-Object { $_.CommandLine -like "*$MainClass*" }
}

function Wait-TcpPort([int]$Port, [int]$TimeoutSeconds = 120) {
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        $client = New-Object Net.Sockets.TcpClient
        try { $client.Connect('127.0.0.1', $Port); return $true } catch { Start-Sleep -Seconds 2 } finally { $client.Dispose() }
    }
    return $false
}
