@echo off
rem start-cluster - levanta Spark Standalone (master + worker) y el servidor Spark Connect.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-cluster.ps1" %*
exit /b %ERRORLEVEL%
