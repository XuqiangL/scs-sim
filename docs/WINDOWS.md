# Windows install (Phase 7)

Supported path: **Python 3.11+ venv + editable install**. A signed MSI is
**out of scope** — this phase does not fail if WiX / Advanced Installer is
absent.

## Quick install

In PowerShell from the repo root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install_windows.ps1
.\scs-sim.cmd demo
.\scs-sim.cmd viz
.\scs-sim.cmd api
.\.venv\Scripts\python.exe -m pytest
```

`install_windows.ps1` creates `.venv` and runs:

```text
pip install -e ".[dev,viz,api]"
```

`scs-sim.cmd` prefers `.venv\Scripts\python.exe`, else `py -3`.

## Scripts

| Script | What |
|--------|------|
| `scripts\install_windows.ps1` | venv + extras |
| `scs-sim.cmd` | `demo` / `viz` / `ops` / `api` / `twin` |
| `scripts\run_demo.bat` | Phase 1 |
| `scripts\run_phase4.bat` | Compute |
| `scripts\run_phase5.bat` | Ops waves |
| `scripts\run_phase6.bat` | CZML / KPI |
| `scripts\run_api.bat` | FastAPI on `127.0.0.1:18765` |
| `scripts\run_all_demos.bat` | Phase 1→6 small configs, then TLE align + micro-bench |
| `scripts\run_bench.bat` | 10k generate + Kepler-J2 (`out/bench.json`) |
| `scripts\build_pyinstaller.ps1` | **Optional** one-folder `scs-demo` |

## Optional PyInstaller

`scripts\build_pyinstaller.ps1` builds `dist\scs-demo\` if you need a folder
you can copy. It downloads PyInstaller and freezes numpy — expect a large
tree. Daily use should stay on the venv launcher.

## Orekit

`propagator: orekit` in YAML is accepted. The adapter is a **pure-Python stub**
(`scs_sim.orbit.orekit_prop`). It raises `NotImplementedError` with JDK / Orekit
install hints. No Java is required to install or test SCS-Sim.

## Not included

- Signed / notarized MSI
- Start-menu shortcuts
- Live CelesTrak fetch
- Production auth on the API
