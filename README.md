# SCS-Sim

**EN** — Windows-first Python simulator for a Starlink-like **compute** constellation (target 10 000 satellites). Phases 1–8: Walker orbits, ISL/GSL, environment, onboard jobs, launch waves, CZML / KPI, local ops API, **live /ui control panel** (fleet + per-sat), twin compare, CelesTrak TLE alignment (opt-in fetch), 10k timing bench. Product progress **~98%**. No signed MSI, no paid Cesium, no Java/Orekit in CI.

**中文** — 工业级类星链**算力**星座仿真器。已完成轨道、网络、环境、机上调度、运维、可视化、本地 API、**交互控制台（星座级 + 单星）**、TLE 对齐与 10k 性能钩子。完整产品约 **98%**。不含已签名 MSI、付费 Cesium 或 CI 中的 Orekit/Java。

## Status

```
███████████████████████████████████████░░░  98%
```

| | |
|---|---|
| Product progress | **98%** (see [ACCEPTANCE.md](docs/ACCEPTANCE.md)) |
| 10k generation | `configs/walker_10k.yaml` — T=10008 |
| TLE align | `tests/fixtures/starlink_sample.tle` → `out/tle_align_report.json` |
| Ops API | `python -m scs_sim.api` — OpenAPI `/docs` + control `/ui` |

Docs: [ARCHITECTURE](docs/ARCHITECTURE.md) · [PROGRESS](docs/PROGRESS.md) · [ACCEPTANCE](docs/ACCEPTANCE.md) · [TLE](docs/TLE.md) · [PERFORMANCE](docs/PERFORMANCE.md) · [API](docs/API.md) · [CONTROL](docs/CONTROL.md) · [WINDOWS](docs/WINDOWS.md) · [VIZ](docs/VIZ.md) · [VALIDATION](docs/VALIDATION.md) · [REFERENCES](docs/REFERENCES.md)

## Install (Windows)

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install_windows.ps1
.\.venv\Scripts\python.exe -m pytest
```

```bat
py -3 -m pip install -e ".[dev,viz,api]"
py -3 -m pytest
py -3 -m pytest -m slow
scripts\run_acceptance.bat
```

Acceptance report: [docs/TEST_REPORT.md](docs/TEST_REPORT.md).

## Quickstart by phase

| Phase | Command | Writes / serves |
|------:|---------|-----------------|
| 1–6 | `scripts\run_all_demos.bat` | sequential small demos (stop on fail) |
| 1 | `scripts\run_demo.bat` | `out/ephemeris_demo.csv` |
| 4 | `scripts\run_phase4.bat` | `out/compute_schedule.csv` |
| 5 | `scripts\run_phase5.bat` | ops timeline HTML |
| 6 | `scripts\run_phase6.bat` | CZML, `viz_globe.html`, KPI |
| 7 | `scripts\run_api.bat` | `http://127.0.0.1:18765/docs` |
| 7 | `scripts\run_ui.bat` | `http://127.0.0.1:18765/ui` |
| 8 | `py -3 -m scs_sim.catalog` | `out/tle_align_report.json` |
| 8 | `scripts\run_bench.bat` | `out/bench.json` (N=10008) |

```bat
scs-sim.cmd catalog --tle tests\fixtures\starlink_sample.tle
scs-sim.cmd bench --n-sats 64 --steps 2
```

Full Starlink catalog: download on Windows and set `deployment.tle_path` — [docs/TLE.md](docs/TLE.md). Fetch is **opt-in** (`--fetch-tle` / `catalog.fetch: true`). CI stays offline.

Phase 6 needs **no Cesium key**. Do not invent a signed MSI or paid Ion token.

## License

MIT.
