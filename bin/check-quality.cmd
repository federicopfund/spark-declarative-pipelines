@echo off
rem check-quality - controles de calidad del modelo dimensional (gold).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0check-quality.ps1" %*
exit /b %ERRORLEVEL%
