# SCS-Sim

**EN** — Windows-first Python simulator for a Starlink-like **compute** constellation (target 10 000 satellites). Phases 1–5: Walker orbits, ISL/GSL, power/thermal, onboard jobs, **launch waves and fleet ops**. Product progress **~62%**. Full Cesium and MSI are not built.

**中文** — 工业级类星链**算力**星座仿真器。已完成轨道、网络、电源热、机上调度、发射波次与星座运维。完整产品约 **62%**。不含完整 Cesium 或 MSI。

## Status

| | |
|---|---|
| Product progress | **62%** (Phases 1–4 + Phase 5 ops core) |
| Ops demo | `configs/phase5_ops.yaml` — 3 waves, ~104 sats |
| Compute demo | `configs/phase4_compute.yaml` |
| 10k generation | `configs/walker_10k.yaml` |

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/PROGRESS.md](docs/PROGRESS.md), [docs/REFERENCES.md](docs/REFERENCES.md).

## Install

```bat
py -3 -m pip install -e ".[dev]"
pytest
```

## Run on Windows

```bat
scripts\run_demo.bat
scripts\run_phase4.bat
scripts\run_phase5.bat
```

```powershell
.\scripts\run_phase5.ps1
```

```bash
python -m scs_sim.demo_ops
python -m scs_sim.demo --ops
```

Phase 5 writes `out/ops_timeline.json`, `out/ops_events.csv`, and a static `out/ops_timeline.html`.

Optional real-catalog overlay: set `deployment.tle_path` to a CelesTrak Starlink TLE. The sim does not download catalogs.

## License

MIT.
