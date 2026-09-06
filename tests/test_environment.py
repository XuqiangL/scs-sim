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
from scs_sim.environment.power import BatteryBank, PowerConfig
from scs_sim.environment.radiation import SAARadiation
from scs_sim.environment.thermal import ThermalState


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


def test_eclipse_flag_consistency() -> None:
    epoch = datetime(2026, 9, 6, tzinfo=timezone.utc)
    ecl = CylindricalEclipse(sun_hat=np.array([1.0, 0.0, 0.0]))
    r = np.array(
        [
            [-8000_000.0, 0.0, 0.0],
            [8000_000.0, 0.0, 0.0],
        ]
    )
    labels = ecl.label(r, epoch)
    sun = ecl.sunlight_fraction(r, epoch)
    umbra = ecl.in_umbra(r, epoch)
    assert labels[0] == "umbra"
    assert sun[0] == 0.0
    assert umbra[0]
    assert labels[1] == "sun"
    assert sun[1] == 1.0
    assert not umbra[1]
    # umbra ⇒ no sunlight; full sunlight ⇒ not umbra
    for i, lab in enumerate(labels):
        if lab == "umbra":
            assert sun[i] == 0.0
        if sun[i] == 1.0:
            assert not umbra[i]


def test_battery_soc_stays_in_unit_interval() -> None:
    bank = BatteryBank(2, PowerConfig(initial_soc=0.5, battery_capacity_wh=10.0))
    # Long eclipse + heavy load
    bank.step(np.array([0.0, 0.0]), np.array([500.0, 500.0]), dt_s=10_000.0)
    assert np.all(bank.soc >= 0.0)
    assert np.all(bank.soc <= 1.0)
    assert float(bank.soc.min()) == 0.0
    # Long sunlight + tiny load
    bank.soc[:] = 0.9
    bank.step(np.array([1.0, 1.0]), np.array([1.0, 1.0]), dt_s=50_000.0)
    assert np.all(bank.soc >= 0.0)
    assert np.all(bank.soc <= 1.0)
    assert float(bank.soc.max()) == 1.0


def test_saa_flux_peaks_over_south_atlantic() -> None:
    rad = SAARadiation()
    epoch = datetime(2026, 9, 6, tzinfo=timezone.utc)
    # Rough ECEF points at 550 km: SAA vs mid-Pacific
    r_e = 6_378_137.0 + 550_000.0

    def ecef(lat_deg: float, lon_deg: float) -> np.ndarray:
        lat, lon = np.deg2rad(lat_deg), np.deg2rad(lon_deg)
        return r_e * np.array(
            [np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)]
        )

    saa = rad.proton_flux_cm2_s(ecef(-25.0, -50.0), epoch)[0]
    pac = rad.proton_flux_cm2_s(ecef(0.0, -160.0), epoch)[0]
    assert saa > 10.0 * pac


def test_thermal_stays_physical() -> None:
    th = ThermalState(1)
    th.step(np.array([1.0]), np.array([200.0]), dt_s=60.0)
    assert 150.0 <= float(th.temp_k[0]) <= 400.0
