# SCS-Sim Desktop + GPU (vNext)

## Desktop EXE (no browser)
- Entry: `scs_sim/desktop/exe_entry.py`
- Default UI: Edge WebView2 embedded window (`pywebview`, `gui=edgechromium`)
- Local API: `http://127.0.0.1:18765/ui` inside the native window (no system browser)
- Build: `powershell -ExecutionPolicy Bypass -File scripts\build_exe.ps1`
- Output: `dist\scs-sim\scs-sim.exe` (~7 MB + ~64 MB folder)
- Flags: default WebView2; `--browser` debug only; `--no-window` API only
- Requires WebView2 Runtime (usually with Edge)

## Launch options
1. Portable EXE: `dist\scs-sim\scs-sim.exe` (NumPy orbit inside frozen env)
2. CUDA desktop: `scs-sim-desktop.cmd` (system Python + torch CUDA on RTX)

## GPU
- Rendering: Cesium WebGL high-performance, PointPrimitiveCollection + LOD (~10k), ISL pulse, ArcGIS Earth imagery
- Orbit: `propagator: kepler_j2_gpu` (PyTorch CUDA when available; NumPy fallback)
- Status: `GET /system/gpu`

## Config
- `configs/phase6_viz.yaml` and `walker_10k.yaml` use `kepler_j2_gpu`
