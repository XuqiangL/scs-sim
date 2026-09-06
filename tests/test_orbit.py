"""One orbit-step sanity check.

Phase: 1 (tests)
Completion: 100%
"""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pytest

from scs_sim.config import ShellConfig
from scs_sim.constellation.walker import generate_walker_shell
from scs_sim.constants import MU_EARTH_M3_S2, R_EARTH_M
from scs_sim.orbit.frames import eci_to_ecef, ecef_to_eci
from scs_sim.orbit.kepler import KeplerJ2Propagator, orbital_period_s
from scs_sim.orbit.propagator import make_propagator


def test_orbit_step_preserves_radius_and_moves() -> None:
    epoch = datetime(2026, 9, 6, tzinfo=timezone.utc)
    shell = ShellConfig(
        id="one",
        altitude_km=550.0,
        inclination_deg=53.0,
        n_planes=1,
        n_sats_per_plane=1,
        phasing_f=0,
    )
    el = generate_walker_shell(shell, epoch)
    prop = KeplerJ2Propagator()
    r0 = prop.positions_eci_m(el, 0.0)
    r1 = prop.positions_eci_m(el, 60.0)

    a = float(el.a_m[0])
    assert np.linalg.norm(r0[0]) == pytest.approx(a, rel=1e-6)
    assert np.linalg.norm(r1[0]) == pytest.approx(a, rel=1e-4)
    # 60 s at LEO is tens of kilometres along-track
    assert np.linalg.norm(r1[0] - r0[0]) > 50_000.0

    period = float(orbital_period_s(a))
    expected = 2.0 * np.pi * np.sqrt(a**3 / MU_EARTH_M3_S2)
    assert period == pytest.approx(expected, rel=1e-12)
    assert 90.0 * 60 < period < 100.0 * 60  # ~95 min at 550 km


def test_eci_ecef_roundtrip() -> None:
    when = datetime(2026, 9, 6, 12, 0, tzinfo=timezone.utc)
    r = np.array([[R_EARTH_M + 550_000.0, 10_000.0, -20_000.0]])
    back = ecef_to_eci(eci_to_ecef(r, when), when)
    assert np.allclose(r, back, rtol=0, atol=1e-6)


def test_factory_names() -> None:
    assert make_propagator("kepler_j2").name == "kepler_j2"
    assert make_propagator("sgp4").name == "sgp4"
