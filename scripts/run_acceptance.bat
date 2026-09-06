@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."

set "PY=python"
where py >nul 2>&1 && set "PY=py -3"

echo [scs-sim] full acceptance campaign (fast then slow)...
%PY% scripts\run_acceptance.py
exit /b %ERRORLEVEL%
