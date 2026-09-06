# SCS-Sim

**EN** — Windows-first Python simulator for a Starlink-like **compute** constellation (target 10 000 satellites). Phases 1–3: Walker orbits, time-varying +Grid ISL / GSL topology, GS↔GS routing metrics, cylindrical eclipse, exponential atmosphere. Product progress **~32%**. Cesium, compute scheduling, and ops packaging are not built.

**中文** — 工业级类星链计算星座仿真器（目标约 1 万星）。已完成轨道 / Walker、+Grid 星间链路与信关站、快照路由、圆柱地影与指数大气。完整产品约 **32%**。不含 Cesium、机上调度或运维打包。

## Status

| | |
|---|---|
| Product progress | **32%** (Phase 1+2 done, Phase 3 minimal) |
| Default demo | 100 sats from first 10k shell × 12 × 60 s + 4 topology snapshots |
| Compact network demo | `configs/phase2_network.yaml` (12×10 = 120) |

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/PROGRESS.md](docs/PROGRESS.md), [docs/REFERENCES.md](docs/REFERENCES.md).

## Requirements

- Python 3.11+ (3.12 OK)
- Windows 10/11 (primary), Linux/macOS for CI

Optional later: `jax` / jaxsgp4 — **not required**.

## Install

```bat
py -3 -m pip install -e .
```

```bash
pip install -e ".[dev]"
pytest
```

## Run on Windows

Phase 1–3 (default 10k config, subsampled):

```bat
scripts\run_demo.bat
```

```powershell
.\scripts\run_demo.ps1
```

Denser complete +Grid (120 sats):

```bat
scripts\run_phase2.bat
```

```powershell
.\scripts\run_phase2.ps1
```

Any platform:

```bash
python -m scs_sim.demo
python -m scs_sim.demo --config configs/phase2_network.yaml
python -m scs_sim.demo --no-network
```

Writes:

- `out/ephemeris_demo.csv` — ECI/ECEF (Phase 1) plus `eclipse`, `sunlight`, `density_kg_m3`
- `out/topology_demo.json` — ISL/GSL snapshots + routing summary
- `out/topology_edges.csv` — edge list

## Layout

```
scs_sim/config.py          # YAML (constellation + ISL/GSL + environment)
scs_sim/clock.py           # discrete time
scs_sim/orbit/             # Kepler+J2, SGP4, frames
scs_sim/constellation/     # Walker-delta
scs_sim/network/           # +Grid ISL, GSL, topology, routing
scs_sim/environment/       # eclipse, exponential atmosphere; radiation TODO
scs_sim/compute/           # Phase 4 ports only
scs_sim/demo.py
configs/walker_10k.yaml
configs/phase2_network.yaml
```

## License

MIT. Third-party GPL simulators (Hypatia ns-3, DSNS) are **references only** — not vendored.
