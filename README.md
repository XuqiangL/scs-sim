# SCS-Sim

**EN** — Phase 1 of a Windows-first Python simulator for a Starlink-like **compute** constellation (target 10 000 satellites). This release is orbit geometry + propagation only (~**10%** of the full product).

**中文** — 工业级类星链计算星座仿真器的第一阶段：Walker 星座生成、Kepler+J2 / SGP4 外推、ECI/ECEF。完整产品约 **10%**，不含星间路由、电源热、算力子系统或 Cesium。

## Status

| | |
|---|---|
| Product progress | **10%** (Phase 1 stop line) |
| Default demo | 100 of 10008 configured sats × 12 × 60 s |
| Configured constellation | `configs/walker_10k.yaml` (10008) |

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/PROGRESS.md](docs/PROGRESS.md), [docs/REFERENCES.md](docs/REFERENCES.md).

## Requirements

- Python 3.11+ (3.12 OK)
- Windows 10/11 (primary), Linux/macOS for CI

Optional later: `jax` / jaxsgp4 for GPU-batch SGP4 — **not required** for Phase 1.

## Install

```bat
py -3 -m pip install -e .
```

```bash
pip install -e .
```

With tests:

```bash
pip install -e ".[dev]"
pytest
```

## Run the demo

**Windows (recommended):**

```bat
scripts\run_demo.bat
```

or PowerShell:

```powershell
.\scripts\run_demo.ps1
```

**Any platform:**

```bash
python -m scs_sim.demo
python -m scs_sim.demo --max-sats 100 --steps 12
```

Writes `out/ephemeris_demo.csv` and prints satellite count, mean altitude, and a Keplerian period estimate.

Full 10k (slower CSV):

```bash
python -m scs_sim.demo --max-sats 10008
```

## Layout

```
scs_sim/config.py          # YAML
scs_sim/clock.py           # discrete time
scs_sim/orbit/             # Kepler+J2, SGP4, frames
scs_sim/constellation/     # Walker-delta
scs_sim/environment/       # Phase 3 ports (empty models)
scs_sim/network/           # Phase 2 ports (ISL/GSL)
scs_sim/compute/           # Phase 4 ports (node/scheduler)
scs_sim/demo.py
configs/walker_10k.yaml
```

## License

MIT. Third-party GPL simulators (Hypatia ns-3, DSNS) are **references only** — not vendored.
