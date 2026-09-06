# Performance (10k hooks)

`python -m scs_sim.bench` times Walker generation, Kepler+J2 steps, and an
optional **subsampled** +Grid ISL. Full ISL at N=10008 with geometric fill
is O(N²) and is **not** the default.

```bat
scripts\run_bench.bat
py -3 -m scs_sim.bench --full --steps 4 --isl-max-sats 64
py -3 -m scs_sim.bench --n-sats 64 --steps 2 --isl-max-sats 32
```

Writes `out/bench.json`: wall times, sat-steps/s, peak RSS when
`resource` (Unix) or `psutil` is available.

## Ballpark — mid-range Windows laptop

Assumptions: 6–8 core CPU, 16 GB RAM, Python 3.12, numpy wheels, no GPU.

| Work | N | Typical |
|------|--:|---------|
| `generate_constellation` Walker-delta | 10 008 | **20–80 ms** |
| Kepler+J2 `positions_eci_m` × 4 steps | 10 008 | **80–400 ms** (~0.1–0.5 M sat-steps/s) |
| +Grid ISL (LOS + fill) | 64 | **50–400 ms** |
| +Grid ISL | 120 | **0.2–1.5 s** |
| +Grid ISL + fill at | 10 008 | **minutes / high RAM — do not run in the default script** |
| Phase 6 viz (36 sats × 12 steps + KPI) | 36 | **under 2 s** |
| Phase 5 ops (≈100 sats × 36 hourly) | ~100 | **a few seconds** |

Peak RSS for the 10k generate+propagate bench is usually **well under 500 MB**.
The heavy part is topology fill, not the propagator.

## Guidance

- Demos stay on `demo.max_sats` 24–120.
- Use `--full` only for the generate/propagate bench.
- Cap ISL with `--isl-max-sats` (0 skips ISL).
- SGP4 is slower (per-sat `Satrec`); keep it for catalog alignment, not 10k ticks.
