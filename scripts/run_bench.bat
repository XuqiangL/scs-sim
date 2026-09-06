@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."

set "PY=python"
where py >nul 2>&1 && set "PY=py -3"

echo [scs-sim] 10k Walker + Kepler-J2 bench (ISL subsample 64)...
%PY% -m scs_sim.bench --config configs/walker_10k.yaml --full --steps 4 --isl-max-sats 64 %*
exit /b %ERRORLEVEL%
