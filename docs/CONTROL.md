# Interactive control UI

The Phase 6 globe (`out/viz_globe.html`) is a **static export**. It cannot
change physics. The ops API used to be the same: load YAML, step, read sats /
KPI. Fleet and per-sat parameters lived in YAML only.

`/ui` (alias `/control`) is a live control panel on the running `SimSession`.

## What you can change at runtime

**Fleet (whole constellation)** — `POST /control/fleet`

| Control | Affects |
|---------|---------|
| `dt_seconds` | Clock step; next advances use the new dt (elapsed time does not rewind) |
| `isl_max_range_km` | Rebuilds ISL topology |
| `gsl_min_elevation_deg` | Rebuilds GSL attachments |
| `solar_w` | Peak panel generation (maps to `panel_area_m2`) |
| `battery_capacity_wh` | Battery energy scale (SoC kept) |
| `apply_drag` | Rebuilds Kepler+J2 propagator |
| `atmosphere_scale` | Multiplies exponential ρ_ref |
| `eclipse` | Cylindrical umbra vs always-sun |
| `compute_flops` | All nodes |
| `idle_w` / `busy_w` | Payload bus watts |

**Per satellite** — `POST /control/sat/{sat_id}`

`a_km`, `e`, `i_deg`, `raan_deg`, `soc`, `power_draw_w`, `flops`, `state`.
`POST /control/sat/{sat_id}/reset` restores the values captured at last YAML load.

Overrides are written to `out/overrides.json`. They are **not** the source of
truth — the in-memory session is. Reload YAML (`POST /config/reload`) clears them.

## Windows

```bat
scripts\run_ui.bat
```

Then open `http://127.0.0.1:18765/ui`.

```bat
scs-sim.cmd ui --config configs\phase6_viz.yaml
```
