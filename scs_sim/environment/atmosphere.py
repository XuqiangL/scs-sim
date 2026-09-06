"""Atmosphere / drag port.

Phase: 3 (placeholder)
Completion: 5%

TODO Phase 3: NRLMSISE-00 or Harris-Priester density + cannonball drag.
Do not couple into the Phase 1 Kepler+J2 / SGP4 loop yet.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

import numpy as np


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
    """Phase 1 no-op atmosphere (vacuum)."""

    name = "null_atmosphere"

    def density_kg_m3(self, r_ecef_m: np.ndarray, epoch: datetime) -> np.ndarray:
        # TODO Phase 3: evaluate density model
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
        # TODO Phase 3:  -0.5 ρ Cd A/m |v_rel| v_rel
        _ = (v_eci_m_s, epoch, cd, area_m2, mass_kg)
        r = np.asarray(r_eci_m, dtype=float).reshape(-1, 3)
        return np.zeros_like(r)
