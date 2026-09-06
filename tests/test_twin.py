"""Digital-twin CSV compare (synthetic fixture, no live catalog)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from scs_sim.config import ShellConfig
from scs_sim.constellation.walker import generate_walker_shell
from scs_sim.orbit.frames import ecef_to_geodetic_n
from scs_sim.orbit.kepler import KeplerJ2Propagator
from scs_sim.twin.compare import compare_tables, compare_to_propagator, write_twin_compare
from scs_sim.twin.io import TelemetryRow, load_telemetry_csv

REPO = Path(__file__).resolve().parents[1]
FIX = REPO / "tests" / "fixtures"


def test_fixture_rmse_small(tmp_path: Path) -> None:
    sim = load_telemetry_csv(FIX / "sim_state_sample.csv")
    tel = load_telemetry_csv(FIX / "telemetry_sample.csv")
    report = compare_tables(sim, tel)
    assert report["n_matched"] == 4
    assert report["n_unmatched_telemetry"] == 0
    assert report["rmse_position_km"] == pytest.approx(3.5, abs=2.5)
    assert report["rmse_soc"] == pytest.approx(0.02, abs=0.005)
    assert report["state_match_rate"] == 1.0
    out = write_twin_compare(tmp_path / "twin_compare.json", report)
    assert out.is_file()
    text = out.read_text(encoding="utf-8")
    assert "rmse_position_km" in text


def test_propagator_twin_near_zero() -> None:
    epoch = datetime(2026, 9, 6, tzinfo=timezone.utc)
    el = generate_walker_shell(
        ShellConfig(
            id="tw",
            altitude_km=550.0,
            inclination_deg=53.0,
            n_planes=1,
            n_sats_per_plane=2,
            phasing_f=0,
        ),
        epoch,
    )
    prop = KeplerJ2Propagator()
    tel: list[TelemetryRow] = []
    for elapsed in (0.0, 90.0):
        r = prop.positions_ecef_m(el, epoch, elapsed)
        lat, lon, alt = ecef_to_geodetic_n(r)
        when = datetime(2026, 9, 6, tzinfo=timezone.utc)
        if elapsed:
            from datetime import timedelta

            when = when + timedelta(seconds=elapsed)
        for i, sid in enumerate(el.sat_id):
            tel.append(
                TelemetryRow(
                    sat_id=str(sid),
                    t=when,
                    lat_deg=float(lat[i]) + 0.002,
                    lon_deg=float(lon[i]) - 0.002,
                    alt_km=float(alt[i]) / 1000.0 + 0.05,
                    soc=0.8,
                    state="operational",
                )
            )
    report = compare_to_propagator(tel, el, prop, epoch, soc_by_sat={}, state_by_sat={})
    assert report["n_matched"] == 4
    # ~0.002 deg at LEO is a few hundred metres
    assert report["rmse_position_km"] < 2.0
