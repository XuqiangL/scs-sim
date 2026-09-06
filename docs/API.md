# Ops REST API (Phase 7)

Local FastAPI console for a loaded YAML constellation. **CORS is open**
(`Access-Control-Allow-Origin: *`) so a file:// or localhost dashboard can call
it. There is **no auth and no TLS** — bind to `127.0.0.1` only.

OpenAPI UI: `http://127.0.0.1:18765/docs` (FastAPI default).

Interactive control panel: `http://127.0.0.1:18765/ui` (alias `/control`).
Mutations hit the running session. See [CONTROL.md](CONTROL.md).

## Install and run (Windows)

```bat
scripts\install_windows.ps1
scripts\run_api.bat
```

```bat
py -3 -m pip install -e ".[api]"
py -3 -m scs_sim.api --config configs\phase6_viz.yaml --port 18765
scs-sim.cmd api --config configs\phase6_viz.yaml
```

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Name, version, links |
| GET | `/health` `/version` | Liveness + completion % |
| POST | `/config/load` | `{path, max_sats?}` load YAML, build Walker / waves |
| GET | `/config` `/sim/status` | Clock, n_sats, wave counts |
| POST | `/sim/step` | `{n}` advance n discrete steps |
| GET | `/waves` | Per-wave lifecycle counts |
| GET | `/sats` | sat_id, lat, lon, alt, soc, state |
| GET | `/sats/{sat_id}` | One row |
| GET | `/kpi` | Latest KPI JSON (also written to `out/kpi_dashboard.json`) |
| GET | `/jobs` | Queued / running compute jobs |
| POST | `/jobs` | `{job_id, flops, dest_gs?}` submit a job |
| POST | `/twin/compare` | Telemetry CSV vs sim table or live propagator |
| GET | `/ui` `/control` | Dark industrial control panel (HTML) |
| GET | `/control/state` | Fleet sliders + per-sat live readouts |
| POST | `/control/fleet` | Runtime fleet physics / network / compute |
| POST | `/control/sat/{sat_id}` | Per-sat a, e, i, RAAN, SoC, watts, FLOPs, state |
| POST | `/control/sat/{sat_id}/reset` | Restore that sat to last YAML baseline |
| POST | `/config/reload` | Reload the last YAML (clears overrides) |
| POST | `/kpi/export` | Rewrite KPI JSON (optional `path`) |

`GET /kpi` falls back to `out/kpi_dashboard.json` if no session is loaded
(e.g. after `python -m scs_sim.demo_viz`).

## Example

```bat
curl -X POST http://127.0.0.1:18765/config/load -H "Content-Type: application/json" -d "{\"path\":\"configs/phase6_viz.yaml\",\"max_sats\":12}"
curl -X POST http://127.0.0.1:18765/sim/step -H "Content-Type: application/json" -d "{\"n\":2}"
curl http://127.0.0.1:18765/sats
curl -X POST http://127.0.0.1:18765/jobs -H "Content-Type: application/json" -d "{\"job_id\":\"edge-1\",\"flops\":1e14}"
curl http://127.0.0.1:18765/kpi
```

## Out of scope

Production auth, multi-user sessions, live CelesTrak download, Kubernetes.
