@echo off
REM SCS-Sim desktop with system Python (CUDA torch available if installed)
cd /d "%~dp0"
py -3 -m scs_sim.desktop.exe_entry %*
