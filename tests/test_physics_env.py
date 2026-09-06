"""Eclipse, atmosphere, power, and thermal accuracy / sanity."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from scs_sim.constants import R_EARTH_M
from scs_sim.environment.atmosphere import ExponentialAtmosphere
from scs_sim.environment.eclipse import CylindricalEclipse
from scs_sim.environment.power import BatteryBank, PowerConfig
from scs_sim.environment.thermal import ThermalState

REPO = Path(__file__).resolve().parents[1]
METRICS = REPO / "out" / "physics_metrics.json"
EPOCH = datetime(2026, 9, 6, tzinfo=timezone.utc)


def test_eclipse_umbra_vs_sunlit() -> None:
    ecl = CylindricalEclipse(sun_hat=np.array([1.0, 0.0, 0.0]))
    night = np.array([[-R_EARTH_M - 550_000.0, 0.0, 0.0]])
    day = np.array([[R_EARTH_M + 550_000.0, 0.0, 0.0]])
    assert bool(ecl.in_umbra(night, EPOCH)[0])
    assert ecl.sunlight_fraction(night, EPOCH)[0] == 0.0
    assert ecl.label(night, EPOCH)[0] == "umbra"
    assert not bool(ecl.in_umbra(day, EPOCH)[0])
    assert ecl.sunlight_fraction(day, EPOCH)[0] == 1.0
    assert ecl.label(day, EPOCH)[0] == "sun"


def test_atmosphere_density_550_vs_800_positive_and_decreasing() -> None:
    atm = ExponentialAtmosphere()
    r550 = np.array([[R_EARTH_M + 550_000.0, 0.0, 0.0]])
    r800 = np.array([[R_EARTH_M + 800_000.0, 0.0, 0.0]])
    rho550 = float(atm.density_kg_m3(r550, EPOCH)[0])
    rho800 = float(atm.density_kg_m3(r800, EPOCH)[0])
    assert rho550 > 0.0 and rho800 > 0.0
    assert rho550 > rho800
    METRICS.parent.mkdir(parents=True, exist_ok=True)
    payload = {}
    if METRICS.is_file():
        try:
            payload = json.loads(METRICS.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {}
    payload["rho_550_kg_m3"] = rho550
    payload["rho_800_kg_m3"] = rho800
    METRICS.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_soc_sunlight_nondecreasing_eclipse_decreases_clipped() -> None:
    cfg = PowerConfig(initial_soc=0.40, battery_capacity_wh=50.0, platform_idle_w=40.0)
    sun = BatteryBank(3, cfg)
    before = sun.soc.copy()
    sun.step(np.ones(3), np.full(3, 20.0), dt_s=600.0)
    assert np.all(sun.soc >= before - 1e-15)
    assert np.all(sun.soc <= 1.0)
    ecl = BatteryBank(3, PowerConfig(initial_soc=0.60, battery_capacity_wh=50.0))
    before_e = ecl.soc.copy()
    ecl.step(np.zeros(3), np.full(3, 80.0), dt_s=600.0)
    assert np.all(ecl.soc < before_e)
    assert np.all((ecl.soc >= 0.0) & (ecl.soc <= 1.0))
    # clip
    clip = BatteryBank(1, PowerConfig(initial_soc=0.99, battery_capacity_wh=1.0))
    clip.step(np.array([1.0]), np.array([0.0]), dt_s=1e6)
    assert float(clip.soc[0]) == 1.0


def test_thermal_short_leo_demo_kelvin_band() -> None:
    th = ThermalState(4)
    for _ in range(20):
        th.step(np.array([1.0, 1.0, 0.0, 0.5]), np.array([80.0, 200.0, 40.0, 90.0]), dt_s=60.0)
        assert np.all((th.temp_k >= 150.0) & (th.temp_k <= 400.0))
    assert 180.0 <= float(th.temp_k.mean()) <= 360.0
