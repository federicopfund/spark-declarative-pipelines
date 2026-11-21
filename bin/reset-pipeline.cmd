@echo off
rem reset-pipeline - borra tablas, checkpoints y metastore, y reinicia el cluster (full refresh total).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0reset-pipeline.ps1" %*
exit /b %ERRORLEVEL%
