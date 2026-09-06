# Progress log

Claimed product completion at end of this log: **~62%** (Phases 1–4 + Phase 5 ops core).

## 2026-09-06 — Phase 5 insertion + constellation operations (~62%)

Continued on `main`. Shipped deployment waves, lifecycle, ops actions, TLE hook, timeline exports.

- YAML `deployment.waves[]` with parking→operational altitude ramp and commission hold.
- States: planned / ascending / commissioning / operational / decommissioning / retired.
- Replenish, retire, station-keeping (mean-anomaly nudge), conjunction subsample warnings.
- `out/ops_timeline.json`, `out/ops_events.csv`, static `out/ops_timeline.html`.
- CelesTrak-style TLE parser + fixture; optional `deployment.tle_path`.
- `configs/phase5_ops.yaml` (3 waves, 104 sats + 8 replenish); `python -m scs_sim.demo_ops`.
- Windows `scripts/run_phase5.bat` / `.ps1`.
- Tests: wave state machine, retired excluded from ISL, TLE fixture loads.

**Still not built:** Cesium globe, MSI, Orekit, K8s.

```
Phase 1–3 ██████████  done
Phase 4   ████████░░  core scheduler
Phase 5   ████████░░  ops / insertion core
Phase 6   ░░░░░░░░░░  Cesium / MSI
Product   █████████████████████████  62%
```

## 2026-09-06 — Phase 3 finish + Phase 4 onboard compute (~50%)

Continued on `main`. Quota still open — shipped power/thermal/radiation and the compute constellation core.

**Phase 3 remaining (done):**

- Solar + battery SoC with eclipse drain; SoC clipped to [0, 1].
- Lumped Stefan–Boltzmann temperature per sat.
- SAA lat/lon heuristic + dose accumulator (NullRadiation replaced as default).
- `out/environment_demo.csv`; demo prints mean SoC, % eclipse, mean T.
- Tests: eclipse flag consistency, SoC bounds, SAA peak, thermal range.

**Phase 4 (core, done):**

- `ComputeNode` / `ComputeFleet`: FLOPs, memory, idle/busy watts.
- `Job` with optional `dest_gs`.
- `GreedyEclipseScheduler`: sunlight now + next step, SoC, dest-GS reachability; never assigns SoC < `min_soc`.
- Topology integration via `reachable_gateways`.
- `out/compute_schedule.csv` + completed / delayed / energy summary.
- `configs/phase4_compute.yaml` (6×8 = 48) and Windows `scripts/run_phase4.bat` / `.ps1`.
- Tests: idle < busy; empty battery skipped; sunny job completes.

**Still not built:** Cesium, ops/MSI, Orekit, full multi-resource packer.

```
Phase 1 ██████████  done
Phase 2 ██████████  done
Phase 3 ██████████  done   power / thermal / SAA
Phase 4 ████████░░  ~90%   greedy look-ahead core
Phase 5 ░░░░░░░░░░  0%     Cesium
Phase 6 ░░░░░░░░░░  0%     ops
Product ████████████████████  50%
```

## 2026-09-06 — Phase 2 network + Phase 3 stubs→minimal physics (~32%)

Continued on `main` after Phase 1. User approved more work through a ~10% Cursor/Grok Bot quota — **not** a Phase-1 freeze.

**Phase 2 (working, not placeholders):**

- +Grid ISL: intra-plane ±1, inter-plane ±1; Earth-sphere occlusion; `isl.max_range_km`.
- Optional geometric fill to `max_degree` so first-shell / subsampled demos stay useful.
- GSL: YAML ground stations (lat/lon/alt), elevation mask, nearest-visible attach.
- Topology snapshots on `demo.topology_steps`; `out/topology_demo.json` + edges CSV.
- Dijkstra GS↔GS path stretch and hop count (Floyd–Warshall in the same module).
- Config: `configs/walker_10k.yaml` extended; new `configs/phase2_network.yaml` (12×10).
- Tests: ISL count, GSL nadir visibility, connected routing path.
- Demo still writes Phase 1 `out/ephemeris_demo.csv` (extra eclipse columns appended).
- Windows `scripts/run_phase2.bat` / `.ps1`.

**Phase 3 (minimal physics):**

- Cylindrical umbra/penumbra from a low-precision Sun vector.
- Exponential atmosphere + cannonball drag acceleration; propagator hook **off by default**.
- Eclipse / sunlight / density columns on the ephemeris CSV.
- Radiation port remains TODO (`NullRadiation`).

**Still not built:** compute scheduler, power/thermal, Cesium UI, ops packaging, 10k topology at full N.

```
Phase 1 ██████████  done   orbits / Walker
Phase 2 ██████████  done   ISL / GSL / routing
Phase 3 ██████░░░░  ~70%   eclipse + exp. atm; radiation TODO
Phase 4 ░░░░░░░░░░  0%     onboard compute
Phase 5 ░░░░░░░░░░  0%     Cesium
Phase 6 ░░░░░░░░░░  0%     ops / 10k ops workflows
Product █████████████░░░░░  32%
```

## 2026-09-06 — Phase 1 greenfield (~10%)

Shipped the first usable slice of SCS-Sim:

- Python 3.11+ package `scs-sim` (`pyproject.toml`, `requirements.txt`).
- YAML config + Walker-delta generator sized for **10008** satellites (`configs/walker_10k.yaml`); demo subsample via `demo.max_sats` (default 100).
- Discrete `SimClock`; Kepler+J2 vectorized propagator; python-sgp4 adapter; ECI/ECEF helpers.
- Demo: `python -m scs_sim.demo` writes `out/ephemeris_demo.csv` and prints sat count, altitude, period estimate.
- Hexagonal **placeholder ports only** for environment (Phase 3), network (Phase 2), compute (Phase 4).
- pytest: Walker count + one orbit-step radius sanity check.
- Docs: ARCHITECTURE (mermaid + progress table + 10% stop), REFERENCES, this log.
- Windows `scripts/run_demo.bat` / `scripts/run_demo.ps1`.
- MIT license, `.gitignore`.
