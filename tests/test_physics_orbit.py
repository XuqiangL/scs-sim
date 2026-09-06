"""Textbook / Vallado orbit accuracy (Kepler, J2, frames, SGP4)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pytest

from scs_sim.config import ShellConfig
from scs_sim.constants import J2, MU_EARTH_M3_S2, R_EARTH_M
from scs_sim.constellation.walker import generate_walker_shell
from scs_sim.orbit.frames import ecef_to_eci, eci_to_ecef, gmst_rad
from scs_sim.orbit.kepler import KeplerJ2Propagator, j2_secular_rates, orbital_period_s
from scs_sim.orbit.propagator import make_propagator

REPO = Path(__file__).resolve().parents[1]
METRICS = REPO / "out" / "physics_metrics.json"

A_550 = R_EARTH_M + 550_000.0
PERIOD_REL_LIMIT = 1e-12
RADIUS_REL_LIMIT = 1e-4
J2_RATE_REL_LIMIT = 1e-12


def _shell(alt_km: float = 550.0, i_deg: float = 53.0, p: int = 1, s: int = 1) -> ShellConfig:
    return ShellConfig(
        id="phy",
        altitude_km=alt_km,
        inclination_deg=i_deg,
        n_planes=p,
        n_sats_per_plane=s,
        phasing_f=0,
    )


def test_kepler_period_550km_relative_error() -> None:
    impl = float(orbital_period_s(A_550))
    ref = 2.0 * np.pi * np.sqrt(A_550**3 / MU_EARTH_M3_S2)
    err = abs(impl - ref) / ref
    assert err <= PERIOD_REL_LIMIT
    assert 90 * 60 < impl < 100 * 60


def test_j2_raan_precession_vallado_sign_and_magnitude() -> None:
    a = np.array([A_550])
    e = np.array([0.0])
    i = np.array([np.deg2rad(53.0)])
    raan_dot, _w, _m = j2_secular_rates(a, e, i)
    n = np.sqrt(MU_EARTH_M3_S2 / A_550**3)
    p = A_550 * (1.0 - 0.0)
    fac = 1.5 * n * J2 * (R_EARTH_M / p) ** 2
    analytical = float(-fac * np.cos(i[0]))
    err = abs(float(raan_dot[0]) - analytical) / abs(analytical)
    deg_day = abs(float(raan_dot[0])) * 86400.0 * 180.0 / np.pi
    assert float(raan_dot[0]) < 0.0  # prograde mid-inclination: westward nodal regression
    assert err <= J2_RATE_REL_LIMIT
    assert 2.0 < deg_day < 8.0


def test_near_circular_radius_over_several_periods() -> None:
    epoch = datetime(2026, 9, 6, tzinfo=timezone.utc)
    el = generate_walker_shell(_shell(), epoch)
    prop = KeplerJ2Propagator()
    period = float(orbital_period_s(float(el.a_m[0])))
    worst = 0.0
    for k in range(5):
        r = prop.positions_eci_m(el, k * period)
        rel = abs(float(np.linalg.norm(r[0])) - float(el.a_m[0])) / float(el.a_m[0])
        worst = max(worst, rel)
    assert worst <= RADIUS_REL_LIMIT


def test_eci_ecef_preserves_norm_and_rotation_orthonormal() -> None:
    when = datetime(2026, 9, 6, 12, 0, tzinfo=timezone.utc)
    r = np.array([[A_550, 15_000.0, -8_000.0], [0.0, A_550, 1_000.0]])
    ecef = eci_to_ecef(r, when)
    assert np.allclose(np.linalg.norm(r, axis=1), np.linalg.norm(ecef, axis=1), rtol=0, atol=1e-8)
    back = ecef_to_eci(ecef, when)
    assert np.allclose(r, back, atol=1e-7)
    g = gmst_rad(when)
    c, s = np.cos(g), np.sin(g)
    rot = np.array([[c, s, 0.0], [-s, c, 0.0], [0.0, 0.0, 1.0]])
    assert np.allclose(rot @ rot.T, np.eye(3), atol=1e-12)
    assert abs(np.linalg.det(rot) - 1.0) < 1e-12


def test_sgp4_and_kepler_both_leo_short_term() -> None:
    epoch = datetime(2026, 9, 6, tzinfo=timezone.utc)
    el = generate_walker_shell(_shell(p=2, s=2), epoch)
    kj = make_propagator("kepler_j2")
    sg = make_propagator("sgp4")
    rk = kj.positions_eci_m(el, 60.0)
    rs = sg.positions_eci_m(el, 60.0)
    rk_km = np.linalg.norm(rk, axis=1) / 1000.0
    rs_km = np.linalg.norm(rs, axis=1) / 1000.0
    assert np.all((rk_km > 6600.0) & (rk_km < 7300.0))
    assert np.all((rs_km > 6600.0) & (rs_km < 7300.0))
    # Mapped-element SGP4 vs Kepler+J2: short-arc radii stay close; positions may drift.
    # Qualitative: both produce LEO; mean |r| differ by less than 50 km after 60 s.
    assert abs(float(rk_km.mean()) - float(rs_km.mean())) < 50.0


def test_write_orbit_metrics() -> None:
    impl = float(orbital_period_s(A_550))
    ref = 2.0 * np.pi * np.sqrt(A_550**3 / MU_EARTH_M3_S2)
    a = np.array([A_550])
    raan_dot, _, _ = j2_secular_rates(a, np.array([0.0]), np.array([np.deg2rad(53.0)]))
    METRICS.parent.mkdir(parents=True, exist_ok=True)
    payload = {}
    if METRICS.is_file():
        try:
            payload = json.loads(METRICS.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {}
    payload.update(
        {
            "period_rel_error": abs(impl - ref) / ref,
            "period_rel_limit": PERIOD_REL_LIMIT,
            "j2_raan_deg_per_day": float(raan_dot[0]) * 86400.0 * 180.0 / np.pi,
            "radius_rel_limit": RADIUS_REL_LIMIT,
        }
    )
    METRICS.write_text(json.dumps(payload, indent=2), encoding="utf-8")
