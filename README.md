# SCS-Sim

**EN** — Windows-first Python simulator for a Starlink-like **compute** constellation (target 10 000 satellites). Phases 1–4: Walker orbits, +Grid ISL/GSL routing, power/thermal/SAA, onboard job scheduler. Product progress **~50%**. Cesium and ops packaging are not built.

**中文** — 工业级类星链**算力**星座仿真器（目标约 1 万星）。已完成轨道、星间/信关站、电源热与 SAA、机上作业调度。完整产品约 **50%**。不含 Cesium 或运维安装包。

## Status

| | |
|---|---|
| Product progress | **50%** (Phases 1–3 done, Phase 4 core) |
| Default demo | 100 sats + environment + a few jobs |
| Compute demo | `configs/phase4_compute.yaml` (48 sats, 10 jobs) |

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/PROGRESS.md](docs/PROGRESS.md), [docs/REFERENCES.md](docs/REFERENCES.md).

## Requirements

- Python 3.11+ (3.12 OK)
- Windows 10/11 (primary), Linux/macOS for CI

## Install

```bat
py -3 -m pip install -e ".[dev]"
pytest
```

## Run on Windows

```bat
scripts\run_demo.bat
scripts\run_phase2.bat
scripts\run_phase4.bat
```

```powershell
.\scripts\run_demo.ps1
.\scripts\run_phase4.ps1
```

```bash
python -m scs_sim.demo
python -m scs_sim.demo --config configs/phase4_compute.yaml
python -m scs_sim.demo --no-network --no-compute
```

Writes:

- `out/ephemeris_demo.csv` — ECI/ECEF + eclipse columns
- `out/environment_demo.csv` — SoC, temperature, load, SAA flux/dose
- `out/topology_demo.json` / `out/topology_edges.csv`
- `out/compute_schedule.csv` — job placement and completions

## Layout

```
scs_sim/orbit/             # Kepler+J2, SGP4, frames
scs_sim/constellation/     # Walker-delta
scs_sim/network/           # +Grid ISL, GSL, routing, reachability
scs_sim/environment/       # eclipse, atmosphere, power, thermal, SAA
scs_sim/compute/           # nodes, jobs, greedy eclipse scheduler
configs/phase4_compute.yaml
```

## License

MIT. Third-party GPL simulators are references only — not vendored.
