"""Compare telemetry to a sim table or live propagator (RMSE position / SoC)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from scs_sim.orbit.elements import KeplerianBatch
from scs_sim.orbit.frames import geodetic_to_ecef_m
from scs_sim.orbit.ports import PropagatorPort
from scs_sim.twin.io import TelemetryRow


def _key(row: TelemetryRow) -> tuple[str, str]:
    return row.sat_id, row.t_iso()


def _ecef_km(row: TelemetryRow) -> np.ndarray:
    return geodetic_to_ecef_m(row.lat_deg, row.lon_deg, row.alt_km * 1000.0) / 1000.0


def compare_tables(
    sim_rows: Iterable[TelemetryRow],
    tel_rows: Iterable[TelemetryRow],
) -> dict[str, Any]:
    """Align on (sat_id, t) and compute position RMSE (km) and SoC RMSE."""
    sim_map = {_key(r): r for r in sim_rows}
    tel_list = list(tel_rows)
    matched: list[tuple[TelemetryRow, TelemetryRow]] = []
    unmatched_tel = 0
    for trow in tel_list:
        srow = sim_map.get(_key(trow))
        if srow is None:
            unmatched_tel += 1
            continue
        matched.append((srow, trow))

    pos_err: list[float] = []
    soc_err: list[float] = []
    state_ok = 0
    for srow, trow in matched:
        ds = _ecef_km(srow) - _ecef_km(trow)
        pos_err.append(float(np.linalg.norm(ds)))
        soc_err.append(float(srow.soc - trow.soc))
        if srow.state == trow.state:
            state_ok += 1

    n = len(matched)
    rmse_pos = float(np.sqrt(np.mean(np.square(pos_err)))) if pos_err else float("nan")
    rmse_soc = float(np.sqrt(np.mean(np.square(soc_err)))) if soc_err else float("nan")
    mean_soc_delta = float(np.mean(soc_err)) if soc_err else float("nan")
    return {
        "n_sim": len(sim_map),
        "n_telemetry": len(tel_list),
        "n_matched": n,
        "n_unmatched_telemetry": unmatched_tel,
        "rmse_position_km": rmse_pos,
        "rmse_soc": rmse_soc,
        "mean_soc_delta": mean_soc_delta,
        "max_position_km": float(np.max(pos_err)) if pos_err else float("nan"),
        "state_match_rate": (state_ok / n) if n else float("nan"),
        "schema": ["sat_id", "t", "lat", "lon", "alt", "soc", "state"],
    }


def compare_to_propagator(
    tel_rows: Iterable[TelemetryRow],
    elements: KeplerianBatch,
    prop: PropagatorPort,
    epoch: datetime,
    *,
    soc_by_sat: dict[str, float] | None = None,
    state_by_sat: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Propagate the batch to each telemetry epoch and compare (digital twin)."""
    from scs_sim.orbit.frames import ecef_to_geodetic_n

    idx = {str(s): i for i, s in enumerate(elements.sat_id)}
    sim_rows: list[TelemetryRow] = []
    soc_by_sat = soc_by_sat or {}
    state_by_sat = state_by_sat or {}
    for trow in tel_rows:
        i = idx.get(trow.sat_id)
        if i is None:
            continue
        elapsed = (trow.t - epoch).total_seconds()
        r_ecef = prop.positions_ecef_m(elements, epoch, elapsed)
        lat, lon, alt_m = ecef_to_geodetic_n(r_ecef[i : i + 1])
        sim_rows.append(
            TelemetryRow(
                sat_id=trow.sat_id,
                t=trow.t,
                lat_deg=float(lat[0]),
                lon_deg=float(lon[0]),
                alt_km=float(alt_m[0]) / 1000.0,
                soc=float(soc_by_sat.get(trow.sat_id, trow.soc)),
                state=state_by_sat.get(trow.sat_id, trow.state),
            )
        )
    report = compare_tables(sim_rows, tel_rows)
    report["mode"] = "propagator"
    return report


def write_twin_compare(path: str | Path, report: dict[str, Any]) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return p
