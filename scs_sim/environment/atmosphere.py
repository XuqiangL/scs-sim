"""Exponential thermosphere + cannonball drag acceleration.

Phase: 3 (environment)
Completion: 75%

Density is a single-scale-height stub, not NRLMSISE-00. Drag acceleration
is available as a hook; the Kepler+J2 stepper applies it only when
``environment.apply_drag`` is true (off by default).
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

import numpy as np

from scs_sim.constants import OMEGA_EARTH_RAD_S, R_EARTH_M


class AtmospherePort(Protocol):
    """Hexagonal port for thermospheric density and drag acceleration."""

    name: str

    def density_kg_m3(self, r_ecef_m: np.ndarray, epoch: datetime) -> np.ndarray:
        """Mass density at ECEF positions, shape (N,)."""

    def drag_acceleration_eci_m_s2(
        self,
        r_eci_m: np.ndarray,
        v_eci_m_s: np.ndarray,
        epoch: datetime,
        *,
        cd: float = 2.2,
        area_m2: float = 1.0,
        mass_kg: float = 300.0,
    ) -> np.ndarray:
        """Specific force in ECI, shape (N, 3)."""


class NullAtmosphere:
    """Vacuum."""

    name = "null_atmosphere"

    def density_kg_m3(self, r_ecef_m: np.ndarray, epoch: datetime) -> np.ndarray:
        _ = epoch
        n = int(np.asarray(r_ecef_m).reshape(-1, 3).shape[0])
        return np.zeros(n, dtype=float)

    def drag_acceleration_eci_m_s2(
        self,
        r_eci_m: np.ndarray,
        v_eci_m_s: np.ndarray,
        epoch: datetime,
        *,
        cd: float = 2.2,
        area_m2: float = 1.0,
        mass_kg: float = 300.0,
    ) -> np.ndarray:
        _ = (v_eci_m_s, epoch, cd, area_m2, mass_kg)
        r = np.asarray(r_eci_m, dtype=float).reshape(-1, 3)
        return np.zeros_like(r)


class ExponentialAtmosphere:
    """ρ = ρ_ref · exp(-(h − h_ref) / H). Defaults tuned for ~500–550 km LEO."""

    name = "exponential"

    def __init__(
        self,
        rho_ref_kg_m3: float = 6.0e-13,
        h_ref_m: float = 500_000.0,
        scale_height_m: float = 60_000.0,
    ) -> None:
        self.rho_ref_kg_m3 = rho_ref_kg_m3
        self.h_ref_m = h_ref_m
        self.scale_height_m = scale_height_m

    def density_kg_m3(self, r_ecef_m: np.ndarray, epoch: datetime) -> np.ndarray:
        _ = epoch
        r = np.asarray(r_ecef_m, dtype=float).reshape(-1, 3)
        h = np.linalg.norm(r, axis=1) - R_EARTH_M
        return self.rho_ref_kg_m3 * np.exp(-(h - self.h_ref_m) / self.scale_height_m)

    def drag_acceleration_eci_m_s2(
        self,
        r_eci_m: np.ndarray,
        v_eci_m_s: np.ndarray,
        epoch: datetime,
        *,
        cd: float = 2.2,
        area_m2: float = 1.0,
        mass_kg: float = 300.0,
    ) -> np.ndarray:
        r = np.asarray(r_eci_m, dtype=float).reshape(-1, 3)
        v = np.asarray(v_eci_m_s, dtype=float).reshape(-1, 3)
        rho = self.density_kg_m3(r, epoch)
        omega = np.array([0.0, 0.0, OMEGA_EARTH_RAD_S])
        v_rel = v - np.cross(np.broadcast_to(omega, r.shape), r)
        speed = np.linalg.norm(v_rel, axis=1, keepdims=True)
        ballistic = (cd * area_m2 / max(mass_kg, 1e-9))
        return (-0.5 * rho[:, None] * ballistic) * speed * v_rel


def make_atmosphere(name: str) -> AtmospherePort:
    key = (name or "exponential").strip().lower()
    if key in {"null", "none", "off"}:
        return NullAtmosphere()
    if key in {"exponential", "exp"}:
        return ExponentialAtmosphere()
    raise ValueError(f"unknown atmosphere {name!r}")
