# SCS-Sim

**EN** — Windows-first Python simulator for a Starlink-like **compute** constellation (target 10 000 satellites). Phases 1–7: Walker orbits, ISL/GSL, power/thermal, onboard jobs, launch waves, CZML / KPI, **local ops REST API, digital-twin CSV compare, Orekit port stub**. Product progress **~91%**. No signed MSI; Orekit is a documented stub (no Java in CI).

**中文** — 工业级类星链**算力**星座仿真器。已完成轨道、网络、电源热、机上调度、发射运维、可视化校验、**本地运维 API 与数字孪生对比**。完整产品约 **91%**。不含已签名 MSI；Orekit 仅为接口桩。

## Status

```
████████████████████████████████████░░░░  91%
```

| | |
|---|---|
| Product progress | **91%** (Phases 1–7 core; no signed MSI / live Orekit) |
| Ops API | `python -m scs_sim.api` — OpenAPI at `/docs` |
| Viz demo | `configs/phase6_viz.yaml` — CZML + HTML + KPI |
| Ops demo | `configs/phase5_ops.yaml` — 3 waves |
| 10k generation | `configs/walker_10k.yaml` |

Docs: [ARCHITECTURE](docs/ARCHITECTURE.md) · [PROGRESS](docs/PROGRESS.md) · [API](docs/API.md) · [WINDOWS](docs/WINDOWS.md) · [VIZ](docs/VIZ.md) · [VALIDATION](docs/VALIDATION.md) · [REFERENCES](docs/REFERENCES.md)

## Install (Windows)

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install_windows.ps1
.\.venv\Scripts\python.exe -m pytest
```

```bat
py -3 -m pip install -e ".[dev,viz,api]"
py -3 -m pytest
```

## Quickstart by phase

| Phase | Command | Writes / serves |
|------:|---------|-----------------|
| 1 | `scripts\run_demo.bat` | `out/ephemeris_demo.csv` |
| 2 | `scripts\run_phase2.bat` | topology JSON |
| 4 | `scripts\run_phase4.bat` | `out/compute_schedule.csv` |
| 5 | `scripts\run_phase5.bat` | ops timeline HTML |
| 6 | `scripts\run_phase6.bat` | CZML, `viz_globe.html`, KPI |
| 7 | `scripts\run_api.bat` | `http://127.0.0.1:18765/docs` |
| 7 | `scs-sim.cmd twin --telemetry tests\fixtures\telemetry_sample.csv --sim tests\fixtures\sim_state_sample.csv` | `out/twin_compare.json` |

```bat
scs-sim.cmd demo
scs-sim.cmd viz
scs-sim.cmd api
```

```bat
py -3 -m scs_sim.demo --viz
py -3 -m scs_sim.demo --ops
py -3 -m scs_sim.api --config configs\phase6_viz.yaml
```

Phase 6 artifacts need **no Cesium key**. Phase 7 API is local-only (CORS open, no auth).

Optional catalog overlay: set `deployment.tle_path` to a CelesTrak TLE file. The sim does not download catalogs.

## License

MIT.
