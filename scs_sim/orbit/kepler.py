"""Kepler + J2 secular propagator (vectorized, Windows-friendly).

Phase: 1 (core) + Phase 3 optional drag hook
Completion: 92%

Clean-room implementation of Vallado-style J2 secular rates. Not derived
from Orekit, poliastro, or GPL constellation simulators.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np

from scs_sim.constants import J2, MU_EARTH_M3_S2, R_EARTH_M
from scs_sim.orbit.elements import KeplerianBatch
from scs_sim.orbit.frames import eci_to_ecef, keplerian_to_eci_m


def orbital_period_s(a_m: float | np.ndarray) -> float | np.ndarray:
    """Keplerian period T = 2π √(a³/μ)."""
    a = np.asarray(a_m, dtype=float)
    return 2.0 * np.pi * np.sqrt(a**3 / MU_EARTH_M3_S2)


def j2_secular_rates(
    a_m: np.ndarray,
    e: np.ndarray,
    i_rad: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (Ω̇, ω̇, Ṁ) in rad/s including Keplerian mean motion in Ṁ."""
    n = np.sqrt(MU_EARTH_M3_S2 / np.asarray(a_m, dtype=float) ** 3)
    e = np.asarray(e, dtype=float)
    i = np.asarray(i_rad, dtype=float)
    p = a_m * (1.0 - e * e)
    fac = 1.5 * n * J2 * (R_EARTH_M / p) ** 2
    c = np.cos(i)
    raan_dot = -fac * c
    argp_dot = 0.5 * fac * (5.0 * c * c - 1.0)
    m_dot = n + 0.5 * fac * np.sqrt(np.maximum(1.0 - e * e, 0.0)) * (3.0 * c * c - 1.0)
    return raan_dot, argp_dot, m_dot


class KeplerJ2Propagator:
    """Closed-form two-body + J2 secular rates. Default Phase 1 engine.

    Optional Phase 3 drag: when ``apply_drag`` and an atmosphere are set,
    semi-major axis is decayed with a first-order energy kick
    ``da = 2 a² / μ · (a_drag · v) · dt``. Off by default.
    """

    name = "kepler_j2"

    def __init__(self, atmosphere: object | None = None, apply_drag: bool = False) -> None:
        self.atmosphere = atmosphere
        self.apply_drag = bool(apply_drag)

    def elements_at(self, elements: KeplerianBatch, elapsed_s: float) -> KeplerianBatch:
        raan_dot, argp_dot, m_dot = j2_secular_rates(elements.a_m, elements.e, elements.i_rad)
        dt = float(elapsed_s)
        out = elements.copy()
        out.raan_rad = np.mod(elements.raan_rad + raan_dot * dt, 2.0 * np.pi)
        out.argp_rad = np.mod(elements.argp_rad + argp_dot * dt, 2.0 * np.pi)
        out.m_rad = np.mod(elements.m_rad + m_dot * dt, 2.0 * np.pi)
        if self.apply_drag and self.atmosphere is not None and dt != 0.0:
            r, v = keplerian_to_eci_m(
                out.a_m, out.e, out.i_rad, out.raan_rad, out.argp_rad, out.m_rad
            )
            a_drag = self.atmosphere.drag_acceleration_eci_m_s2(r, v, elements.epoch)
            power = np.sum(a_drag * v, axis=1)
            out.a_m = out.a_m + (2.0 * out.a_m**2 / MU_EARTH_M3_S2) * power * dt
        return out

    def state_eci_m(
        self, elements: KeplerianBatch, elapsed_s: float
    ) -> tuple[np.ndarray, np.ndarray]:
        el = self.elements_at(elements, elapsed_s)
        return keplerian_to_eci_m(el.a_m, el.e, el.i_rad, el.raan_rad, el.argp_rad, el.m_rad)

    def positions_eci_m(self, elements: KeplerianBatch, elapsed_s: float) -> np.ndarray:
        r, _v = self.state_eci_m(elements, elapsed_s)
        return r

    def positions_ecef_m(
        self,
        elements: KeplerianBatch,
        epoch: datetime,
        elapsed_s: float,
    ) -> np.ndarray:
        r_eci = self.positions_eci_m(elements, elapsed_s)
        when = epoch + timedelta(seconds=float(elapsed_s))
        return eci_to_ecef(r_eci, when)
