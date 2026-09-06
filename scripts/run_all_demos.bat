@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."

set "PY=python"
where py >nul 2>&1 && set "PY=py -3"

echo [scs-sim] install editable (once)...
%PY% -m pip install -e .
if errorlevel 1 exit /b 1

echo [scs-sim] Phase 1 — small Walker demo...
%PY% -m scs_sim.demo --config configs/walker_10k.yaml --max-sats 24 --steps 4 --no-compute --no-network
if errorlevel 1 exit /b 1

echo [scs-sim] Phase 2 — network...
%PY% -m scs_sim.demo --config configs/phase2_network.yaml --max-sats 24 --steps 4 --no-compute
if errorlevel 1 exit /b 1

echo [scs-sim] Phase 4 — compute...
%PY% -m scs_sim.demo --config configs/phase4_compute.yaml --max-sats 24 --steps 6
if errorlevel 1 exit /b 1

echo [scs-sim] Phase 5 — ops (short)...
%PY% -m scs_sim.demo_ops --config configs/phase5_ops.yaml --steps 6
if errorlevel 1 exit /b 1

echo [scs-sim] Phase 6 — viz / KPI...
%PY% -m scs_sim.demo_viz --config configs/phase6_viz.yaml --max-sats 18 --steps 4
if errorlevel 1 exit /b 1

echo [scs-sim] TLE align (fixture, no network)...
%PY% -m scs_sim.catalog --tle tests/fixtures/starlink_sample.tle --config configs/walker_10k.yaml
if errorlevel 1 exit /b 1

echo [scs-sim] micro-bench...
%PY% -m scs_sim.bench --n-sats 64 --steps 2 --isl-max-sats 32
if errorlevel 1 exit /b 1

echo [scs-sim] all demos OK
exit /b 0
