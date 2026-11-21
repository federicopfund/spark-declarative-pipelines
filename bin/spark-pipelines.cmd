@echo off
rem spark-pipelines - CLI de Spark Declarative Pipelines para Windows.
rem Uso: bin\spark-pipelines dry-run ^| run [--refresh X] [--full-refresh X,Y] [--full-refresh-all]
rem -ExecutionPolicy Bypass aplica solo a esta ejecucion; no cambia la politica de Windows.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0spark-pipelines.ps1" %*
exit /b %ERRORLEVEL%
