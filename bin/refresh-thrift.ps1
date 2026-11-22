<#
.SYNOPSIS
    Refresca la cache de archivos del Thrift Server para todas las tablas de retail (REFRESH TABLE).

.DESCRIPTION
    bin\spark-pipelines run ya lo hace al terminar. Usarlo a mano si Power BI (o cualquier cliente JDBC/ODBC)
    devuelve FAILED_READ_FILE.FILE_NOT_EXIST despues de que las tablas se reescribieron.

      bin\refresh-thrift.cmd
#>
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\conf\spark-env.ps1')
Update-ThriftCache
