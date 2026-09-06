@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."

set "PY=python"
where py >nul 2>&1 && set "PY=py -3"

echo [scs-sim] installing editable package (core)...
%PY% -m pip install -e .
if errorlevel 1 exit /b 1

echo [scs-sim] optional matplotlib for PNG tracks (safe to skip)...
%PY% -m pip install -e ".[viz]"
if errorlevel 1 echo [scs-sim] viz extra skipped — SVG fallback still works

echo [scs-sim] running Phase 6 viz + KPI demo...
%PY% -m scs_sim.demo_viz --config configs/phase6_viz.yaml %*
exit /b %ERRORLEVEL%
