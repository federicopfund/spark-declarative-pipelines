@echo off
rem refresh-thrift - REFRESH TABLE de todas las tablas de retail en el Thrift Server.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0refresh-thrift.ps1" %*
exit /b %ERRORLEVEL%
