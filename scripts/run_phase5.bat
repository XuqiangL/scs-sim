@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."

set "PY=python"
where py >nul 2>&1 && set "PY=py -3"

echo [scs-sim] installing editable package...
%PY% -m pip install -e .
if errorlevel 1 exit /b 1

echo [scs-sim] running Phase 5 ops demo...
%PY% -m scs_sim.demo_ops --config configs/phase5_ops.yaml %*
exit /b %ERRORLEVEL%
