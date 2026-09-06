@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."

set "PY=python"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
if not exist ".venv\Scripts\python.exe" where py >nul 2>&1 && set "PY=py -3"

echo [scs-sim] installing API extra...
%PY% -m pip install -e ".[api]"
if errorlevel 1 exit /b 1

echo [scs-sim] ops API on http://127.0.0.1:18765/docs
%PY% -m scs_sim.api --host 127.0.0.1 --port 18765 --config configs/phase6_viz.yaml %*
exit /b %ERRORLEVEL%
