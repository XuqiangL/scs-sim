# SCS-Sim

**EN** — Windows-first Python simulator for a Starlink-like **compute** constellation (target 10 000 satellites). Phases 1–6: Walker orbits, ISL/GSL, power/thermal, onboard jobs, launch waves, **CZML / offline globe tracks, KPI dashboard, validation**. Product progress **~78%**. Windows MSI and Orekit are not built.

**中文** — 工业级类星链**算力**星座仿真器。已完成轨道、网络、电源热、机上调度、发射运维、**CZML 可视化与校验**。完整产品约 **78%**。不含 Windows MSI 或 Orekit。

## Status

| | |
|---|---|
| Product progress | **78%** (Phases 1–5 + Phase 6 viz / validation) |
| Viz demo | `configs/phase6_viz.yaml` — 6×6 = 36 sats, CZML + HTML + KPI |
| Ops demo | `configs/phase5_ops.yaml` — 3 waves, ~104 sats |
| Compute demo | `configs/phase4_compute.yaml` |
| 10k generation | `configs/walker_10k.yaml` |

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/PROGRESS.md](docs/PROGRESS.md), [docs/VIZ.md](docs/VIZ.md), [docs/VALIDATION.md](docs/VALIDATION.md), [docs/REFERENCES.md](docs/REFERENCES.md).

## Install

```bat
py -3 -m pip install -e ".[dev]"
py -3 -m pytest
```

Optional PNG ground tracks (SVG always works without this):

```bat
py -3 -m pip install -e ".[dev,viz]"
```

## Run on Windows

```bat
scripts\run_demo.bat
scripts\run_phase4.bat
scripts\run_phase5.bat
scripts\run_phase6.bat
```

```powershell
.\scripts\run_phase6.ps1
```

```bat
py -3 -m scs_sim.demo_viz
py -3 -m scs_sim.demo --viz
```

Phase 6 writes (no Cesium API key):

- `out/constellation.czml` — drop into Cesium ion or a local CesiumJS sandbox
- `out/viz_globe.html` — Cesium CDN if online, SVG tracks offline
- `out/ground_tracks.svg` (and `.png` if matplotlib is installed)
- `out/kpi_dashboard.json` + `out/kpi_report.md`

How to load CZML: [docs/VIZ.md](docs/VIZ.md).

Phase 5 writes `out/ops_timeline.json`, `out/ops_events.csv`, and a static `out/ops_timeline.html`.

Optional real-catalog overlay: set `deployment.tle_path` to a CelesTrak Starlink TLE. The sim does not download catalogs.

## License

MIT.
