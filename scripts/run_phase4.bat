@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."

set "PY=python"
where py >nul 2>&1 && set "PY=py -3"

echo [scs-sim] installing editable package...
%PY% -m pip install -e .
if errorlevel 1 exit /b 1

echo [scs-sim] running Phase 4 compute demo...
%PY% -m scs_sim.demo --config configs/phase4_compute.yaml %*
exit /b %ERRORLEVEL%
