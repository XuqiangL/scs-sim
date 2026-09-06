"""Phase 3 eclipse / atmosphere sanity.

Phase: 3 (tests)
Completion: 100%
"""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np

from scs_sim.constants import R_EARTH_M
from scs_sim.environment.atmosphere import ExponentialAtmosphere
from scs_sim.environment.eclipse import CylindricalEclipse


def test_cylindrical_umbra_and_sun() -> None:
    epoch = datetime(2026, 9, 6, tzinfo=timezone.utc)
    ecl = CylindricalEclipse(sun_hat=np.array([1.0, 0.0, 0.0]))
    night = np.array([[-8000_000.0, 0.0, 0.0]])
    day = np.array([[8000_000.0, 0.0, 0.0]])
    grazing = np.array([[-8000_000.0, R_EARTH_M + 200_000.0, 0.0]])
    assert ecl.in_umbra(night, epoch)[0]
    assert ecl.sunlight_fraction(night, epoch)[0] == 0.0
    assert not ecl.in_umbra(day, epoch)[0]
    assert ecl.sunlight_fraction(day, epoch)[0] == 1.0
    assert ecl.label(grazing, epoch)[0] == "sun"


def test_exponential_density_decreases_with_altitude() -> None:
    atm = ExponentialAtmosphere()
    epoch = datetime(2026, 9, 6, tzinfo=timezone.utc)
    low = np.array([[R_EARTH_M + 400_000.0, 0.0, 0.0]])
    high = np.array([[R_EARTH_M + 600_000.0, 0.0, 0.0]])
    rho_lo = atm.density_kg_m3(low, epoch)[0]
    rho_hi = atm.density_kg_m3(high, epoch)[0]
    assert rho_lo > rho_hi > 0.0
    v = np.array([[0.0, 7600.0, 0.0]])
    a = atm.drag_acceleration_eci_m_s2(low, v, epoch, cd=2.2, area_m2=4.0, mass_kg=300.0)
    assert a.shape == (1, 3)
    # Drag opposes velocity
    assert float(a[0, 1]) < 0.0
