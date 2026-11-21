@echo off
rem stop-cluster - detiene el servidor Spark Connect, el worker y el master.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop-cluster.ps1" %*
exit /b %ERRORLEVEL%
