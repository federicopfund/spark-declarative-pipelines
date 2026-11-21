@echo off
rem query-lakehouse - muestra las tablas del pipeline via Spark Connect. Uso: bin\query-lakehouse [dataset ...]
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0query-lakehouse.ps1" %*
exit /b %ERRORLEVEL%
