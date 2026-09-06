"""TLE → SGP4 vs Kepler Walker shell stats → ``out/tle_align_report.json``."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from sgp4.api import Satrec, jday

from scs_sim.config import SimConfig
from scs_sim.constants import R_EARTH_M
from scs_sim.constellation.walker import generate_walker_shell
from scs_sim.ops.tle import TleRecord, tle_to_elements
from scs_sim.orbit.kepler import KeplerJ2Propagator


def propagate_tle_eci_m(records: list[TleRecord], when: datetime) -> np.ndarray:
    """SGP4 from the raw two-line sets (not the Kepler mapping)."""
    jd, fr = jday(
        when.year,
        when.month,
        when.day,
        when.hour,
        when.minute,
        when.second + when.microsecond * 1e-6,
    )
    out = np.empty((len(records), 3), dtype=float)
    for i, rec in enumerate(records):
        sat = Satrec.twoline2rv(rec.line1, rec.line2)
        err, r_km, _v = sat.sgp4(jd, fr)
        if err != 0:
            raise RuntimeError(f"SGP4 error {err} for {rec.name} ({rec.satnum})")
        out[i, :] = np.asarray(r_km, dtype=float) * 1000.0
    return out


def align_tle_to_walker(
    records: list[TleRecord],
    cfg: SimConfig,
    *,
    source: str,
    fetched: bool = False,
    when: datetime | None = None,
) -> dict[str, Any]:
    """Compare catalog count / altitude / inclination to the primary Walker shell."""
    if not records:
        raise ValueError("no TLE records")
    epoch = when or cfg.epoch
    if epoch.tzinfo is None:
        epoch = epoch.replace(tzinfo=timezone.utc)
    elements = tle_to_elements(records, epoch)
    r_eci = propagate_tle_eci_m(records, epoch)
    r_km = np.linalg.norm(r_eci, axis=1) / 1000.0
    alt_km = r_km - R_EARTH_M / 1000.0
    a_alt_km = elements.a_m / 1000.0 - R_EARTH_M / 1000.0
    inc_deg = np.rad2deg(elements.i_rad)

    shell = cfg.shells[0]
    walker = generate_walker_shell(shell, cfg.epoch)
    walker_alt = float(shell.altitude_km)
    band_lo, band_hi = walker_alt - 80.0, walker_alt + 80.0
    in_band = int(np.sum((alt_km >= band_lo) & (alt_km <= band_hi)))

    prop = KeplerJ2Propagator()
    r_w = prop.positions_eci_m(walker, 0.0)
    walker_r = float(np.mean(np.linalg.norm(r_w, axis=1)) / 1000.0)

    return {
        "source": source,
        "fetched": bool(fetched),
        "n_tle": len(records),
        "n_walker_shell": len(walker),
        "walker_shell_id": shell.id,
        "walker_configured_T": int(shell.n_sats),
        "tle_mean_alt_km": float(np.mean(alt_km)),
        "tle_mean_sma_alt_km": float(np.mean(a_alt_km)),
        "tle_alt_min_km": float(np.min(alt_km)),
        "tle_alt_max_km": float(np.max(alt_km)),
        "walker_alt_km": walker_alt,
        "altitude_band_km": [band_lo, band_hi],
        "n_tle_in_walker_band": in_band,
        "fraction_in_walker_band": in_band / len(records),
        "tle_mean_inc_deg": float(np.mean(inc_deg)),
        "walker_inc_deg": float(shell.inclination_deg),
        "inc_delta_deg": float(np.mean(inc_deg) - shell.inclination_deg),
        "sgp4_step_ok": True,
        "sgp4_mean_radius_km": float(np.mean(r_km)),
        "kepler_walker_mean_radius_km": walker_r,
        "notes": [
            "Sample catalog vs primary Walker shell (count is not expected to match).",
            "Altitude from SGP4 r at the report epoch; SMA alt from TLE mean motion.",
            "Network fetch is opt-in (catalog.fetch / --fetch-tle).",
        ],
    }


def write_align_report(path: str | Path, report: dict[str, Any]) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return p
