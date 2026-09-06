@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -m scs_sim.cli %*
  exit /b %ERRORLEVEL%
)

set "PY=python"
where py >nul 2>&1 && set "PY=py -3"
%PY% -m scs_sim.cli %*
exit /b %ERRORLEVEL%
