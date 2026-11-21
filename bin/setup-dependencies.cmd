@echo off
rem setup-dependencies - descarga los jars de Derby (servidor de red y cliente) y verifica su SHA-1.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup-dependencies.ps1" %*
exit /b %ERRORLEVEL%
