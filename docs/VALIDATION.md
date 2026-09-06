# Validation

Phase 6 adds a small, license-free harness. It checks **our** models against
textbook formulas and the YAML Walker count. It does **not** vendor Hypatia,
LEOCraft, or StarPerf, and it does **not** fail CI when those baselines are
absent.

Run:

```bat
py -3 -m pytest
```

```bash
python3 -m pytest tests/test_validation.py
```

Implementation: `scs_sim/validation/checks.py` and `tests/test_validation.py`.

## Hard checks (always run)

| Check | What | Tolerance | Why |
|-------|------|-----------|-----|
| Kepler period | `orbital_period_s(a)` vs `T = 2π √(a³/μ)` | relative **1e-12** | two-body period is the clock for LEO demos |
| Walker T | `sum(P × S)` and generated batch length vs `n_sats_configured` | **exact** | `walker_10k.yaml` must stay 10008; `phase6_viz.yaml` is 6×6 = 36 |
| Radius ≈ a | `max ‖r‖ − a / a` after Kepler+J2 | relative **1e-4** | near-circular shells (`e = 0`) should sit on the SMA sphere |

Constants (`μ`, `Rₑ`) live in `scs_sim/constants.py` (WGS-84 / EGM96-ish).
J2 secular rates change Ω, ω, M — they do **not** change `a`, so radius stays
≈ `a` for `e = 0`.

## Optional literature comparisons (do not hard-fail)

Drop JSON files into `tests/baselines/` when you want a numeric alignment.
If a file is missing, pytest **skips** that test.

### Hypatia RTT (future)

File: `tests/baselines/hypatia_rtt.json`

```json
{
  "source": "hypatia",
  "note": "vacuum 2L/c proxy; Hypatia ns-3 RTT includes queuing",
  "pairs": [
    {"src": "london", "dst": "singapore", "path_km": 12000, "rtt_ms": 80}
  ]
}
```

SCS-Sim proxy: `rtt_ms = 2 · path_km / c` (`scs_sim.validation.rtt_ms_from_path_km`).
This is **propagation delay only**. Hypatia’s published RTT traces include
queuing and MAC — expect tens of percent difference even when topologies match.
The test uses a loose 50% relative band so it is a sanity check, not a paper
reproduction.

### LEOCraft stretch (future)

File: `tests/baselines/leocraft_stretch.json`

```json
{
  "source": "leocraft",
  "mean_stretch": 1.35,
  "note": "GS↔GS path / geodesic for a named shell snapshot"
}
```

SCS-Sim already records stretch in topology snapshots and
`out/kpi_dashboard.json` (`stretch.mean`, histogram). When a LEOCraft table
is available, compare those fields offline; do not copy LEOCraft sources.

## What this does *not* claim

- Bit-identical ephemeris vs SGP4 / Orekit (different force models).
- Population coverage maps (KPI “coverage” = **GS with ≥1 GSL**).
- Licensed Cesium ion assets at generation time.

See `docs/VIZ.md` for CZML / HTML artifacts and `docs/REFERENCES.md` for the
clean-room policy.
