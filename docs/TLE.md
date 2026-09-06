# Starlink TLE / CelesTrak (Windows)

SCS-Sim never downloads a catalog unless you **opt in**. CI and
`pytest` use `tests/fixtures/starlink_sample.tle` (8 public-format
Starlink-style 3-line sets, 24 lines).

## Local file (default)

Point ops at a TLE you already have:

```yaml
# in any constellation YAML
deployment:
  tle_path: data/starlink.tle

catalog:
  fetch: false
  cache_path: out/starlink.tle
  tle_path: data/starlink.tle
```

```bat
py -3 -m scs_sim.catalog --tle tests\fixtures\starlink_sample.tle
py -3 -m scs_sim.demo_ops --config configs\phase5_ops.yaml
```

`out/tle_align_report.json` compares TLE count / altitude band / inclination
to the primary Walker shell, and runs **one SGP4 step** from the two-line sets.

## Download the full Starlink group (opt-in)

CelesTrak: [gp.php?GROUP=starlink&FORMAT=tle](https://celestrak.org/NORAD/elements/gp.php?GROUP=starlink&FORMAT=tle)

```bat
curl -L -o data\starlink.tle "https://celestrak.org/NORAD/elements/gp.php?GROUP=starlink&FORMAT=tle"
```

```powershell
New-Item -ItemType Directory -Force data | Out-Null
Invoke-WebRequest -Uri "https://celestrak.org/NORAD/elements/gp.php?GROUP=starlink&FORMAT=tle" -OutFile data\starlink.tle
```

Or let the sim fetch **once** (not used in CI):

```bat
py -3 -m scs_sim.catalog --fetch-tle --tle out\starlink.tle
```

```yaml
catalog:
  fetch: true
  cache_path: out/starlink.tle
```

Respect [CelesTrak TOS](https://celestrak.org/) — cache the file; do not hammer the endpoint.

Then set `deployment.tle_path: out/starlink.tle` and optionally
`propagator: sgp4` so TEME positions come from python-sgp4.

## What alignment reports

| Field | Meaning |
|-------|---------|
| `n_tle` vs `n_walker_shell` | Sample size vs configured Walker T (not expected equal) |
| `tle_mean_alt_km` | SGP4 radius − Rₑ at the report epoch |
| `fraction_in_walker_band` | Share of TLEs within ±80 km of the primary shell altitude |
| `inc_delta_deg` | Mean TLE inclination − Walker *i* |

This is a catalog-vs-shell sanity check, not a NORAD ID match.
