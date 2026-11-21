@echo off
rem land-batch - copia data\samples\batch-NNN a data\landing\. Uso: bin\land-batch -Batch 1 [-Reset]
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0land-batch.ps1" %*
exit /b %ERRORLEVEL%
