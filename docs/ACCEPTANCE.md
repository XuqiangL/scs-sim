# Acceptance checklist

Maps the original product goals to modules. **Pass** = implemented and
covered by pytest or a Windows script. Signed MSI and live Orekit/Java
are explicit non-goals.

| Goal | Module / artifact | Gate | Status |
|------|-------------------|------|--------|
| Fly ~10 000 sats (Walker-delta) | `constellation/walker.py`, `configs/walker_10k.yaml` (T=10008) | `test_walker.py`, `scs_sim.bench --full` | **pass** |
| Windows-first, no proprietary license | venv + `scs-sim.cmd`, `docs/WINDOWS.md` | `scripts/install_windows.ps1` | **pass** (no signed MSI) |
| Realistic orbits | Kepler+J2, SGP4 adapter, frames | `test_orbit.py`, `test_validation.py` | **pass** |
| Catalog alignment | `catalog/`, fixture TLE, `out/tle_align_report.json` | `test_catalog.py` (offline) | **pass** |
| ISL / GSL / stretch | `network/` | `test_network.py` | **pass** |
| Eclipse / power / thermal / SAA | `environment/` | `test_environment.py` | **pass** |
| Onboard compute jobs | `compute/`, `phase4_compute.yaml` | `test_compute.py` | **pass** |
| Insertion / ops / TLE overlay | `ops/`, `phase5_ops.yaml` | `test_ops.py` | **pass** |
| Viz without paid Cesium | CZML + SVG/PNG + `viz_globe.html` | `test_viz.py` | **pass** |
| Validation vs textbook | period, Walker T, radius ≈ a | `test_validation.py` | **pass** |
| Digital twin | `twin/` RMSE vs telemetry CSV | `test_twin.py` | **pass** |
| Local ops API | FastAPI `/docs` | `test_api.py` | **pass** |
| Orekit future hook | `OrekitPropagator` stub | `test_orekit.py` | **stub pass** |
| 10k timing | `scs_sim.bench`, `docs/PERFORMANCE.md` | `test_bench.py` (N≤64) | **pass** |
| Sequential demos | `scripts/run_all_demos.bat` | stop on first fail | **pass** |
| Signed MSI | — | out of scope | **n/a** |
| Production auth / K8s | — | out of scope | **n/a** |
| Hypatia ns-3 / paid Cesium ion | — | out of scope | **n/a** |
| Live CelesTrak in CI | `catalog.fetch` default false | offline fixture | **pass** |

Claimed product: **~97%**. Remaining ~3%: live Orekit, signed installer, production API hardening.
