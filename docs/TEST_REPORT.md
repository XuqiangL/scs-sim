# Test report

Generated **2026-09-06T12:00:33Z** (Python 3.12.3).

## Counts

| Pass | Fail | Error | Skip | Total |
|-----:|-----:|------:|-----:|------:|
| 65 | 0 | 0 | 2 | 67 |

Fast (`-m "not slow"`): 64 passed / 0 failed / 2 skipped.  
Slow (`-m slow`): 1 passed / 0 failed / 0 skipped.

Exit codes: not-slow=0, slow=0.

## New modules this campaign

- `tests/test_physics_orbit.py`
- `tests/test_physics_env.py`
- `tests/test_physics_link.py`
- `tests/test_physics_walker.py`
- `tests/test_e2e_api.py`
- `tests/test_e2e_demos.py`
- `tests/test_property_chaos.py`
- `tests/test_bench_slow.py`

## Physics measured vs limits

| Metric | Value | Limit / note |
|--------|-------|----------------|
| Kepler period relative error | 0.0 | ≤ 1e-12 |
| J2 RAAN rate | -4.489193506364322 deg/day | negative; ~2–8 deg/day at 550 km / 53° |
| Radius relative limit | — | ≤ 0.0001 |
| ρ(550 km) | 2.607589251042469e-13 kg/m³ | > ρ(800 km) > 0 |
| ρ(800 km) | 4.04276819945128e-15 kg/m³ | positive |

## E2E

- FastAPI `/docs`, `/openapi.json`, load → step → sats → job → KPI → twin: covered in `test_e2e_api.py`.
- Demos phase2/4/5/6 + catalog + bench + `run_all_demos` equivalent: `test_e2e_demos.py`.
- CZML document packet, KPI keys, topology snapshots validated.

## Known gaps

- Orekit propagate is a stub (NotImplementedError) — not a numeric gold standard.
- Signed MSI / production auth / paid Cesium ion are out of scope.
- SGP4 vs Kepler+J2 is a short-arc LEO-radius check, not a bit-identical ephemeris match.
- CelesTrak HTTP fetch is opt-in and is not exercised in this campaign.

## Failed cases

none

## Windows acceptance

**Ready** — all non-skipped tests passed. Run `scripts\run_all_demos.bat` then `py -3 -m pytest`.
