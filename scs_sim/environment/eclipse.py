"""Cylindrical umbra / penumbra (Sun–Earth shadow).

Phase: 3 (environment)
Completion: 90%

Simple cylinder + solar-angular-radius penumbra annulus. Not a conical
Orekit-grade model. Power and thermal consume ``sunlight_fraction``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

import numpy as np

from scs_sim.constants import R_EARTH_M
from scs_sim.environment.sun import sun_unit_eci

# Mean solar angular radius (rad) ≈ 0.266 deg
SOLAR_ANGULAR_RADIUS_RAD = 0.004654


class EclipsePort(Protocol):
    name: str

    def in_umbra(self, r_eci_m: np.ndarray, epoch: datetime) -> np.ndarray:
        """Boolean mask, shape (N,)."""

    def sunlight_fraction(self, r_eci_m: np.ndarray, epoch: datetime) -> np.ndarray:
        """1 = full sun, 0 = full umbra. Shape (N,)."""


class NullEclipse:
    """Always in sunlight."""

    name = "null_eclipse"

    def in_umbra(self, r_eci_m: np.ndarray, epoch: datetime) -> np.ndarray:
        _ = epoch
        n = int(np.asarray(r_eci_m).reshape(-1, 3).shape[0])
        return np.zeros(n, dtype=bool)

    def sunlight_fraction(self, r_eci_m: np.ndarray, epoch: datetime) -> np.ndarray:
        _ = epoch
        n = int(np.asarray(r_eci_m).reshape(-1, 3).shape[0])
        return np.ones(n, dtype=float)

    def label(self, r_eci_m: np.ndarray, epoch: datetime) -> list[str]:
        _ = epoch
        n = int(np.asarray(r_eci_m).reshape(-1, 3).shape[0])
        return ["sun"] * n


class CylindricalEclipse:
    """Night-side cylinder of radius R_earth; penumbra is a slightly fatter cylinder."""

    name = "cylindrical_eclipse"

    def __init__(self, sun_hat: np.ndarray | None = None) -> None:
        self._sun_hat = None if sun_hat is None else np.asarray(sun_hat, dtype=float)

    def _hat(self, epoch: datetime) -> np.ndarray:
        if self._sun_hat is not None:
            return self._sun_hat
        return sun_unit_eci(epoch)

    def classify(self, r_eci_m: np.ndarray, epoch: datetime) -> np.ndarray:
        """0 = sun, 1 = penumbra, 2 = umbra. Shape (N,)."""
        r = np.asarray(r_eci_m, dtype=float).reshape(-1, 3)
        s = self._hat(epoch)
        along = r @ s
        perp = r - along[:, None] * s
        p = np.linalg.norm(perp, axis=1)
        behind = along < 0.0
        umbra = behind & (p < R_EARTH_M)
        pen_r = R_EARTH_M + SOLAR_ANGULAR_RADIUS_RAD * np.abs(along)
        penumbra = behind & (p < pen_r) & ~umbra
        out = np.zeros(r.shape[0], dtype=np.int8)
        out[penumbra] = 1
        out[umbra] = 2
        return out

    def in_umbra(self, r_eci_m: np.ndarray, epoch: datetime) -> np.ndarray:
        return self.classify(r_eci_m, epoch) == 2

    def in_penumbra(self, r_eci_m: np.ndarray, epoch: datetime) -> np.ndarray:
        return self.classify(r_eci_m, epoch) == 1

    def sunlight_fraction(self, r_eci_m: np.ndarray, epoch: datetime) -> np.ndarray:
        cls = self.classify(r_eci_m, epoch)
        frac = np.ones(cls.shape[0], dtype=float)
        frac[cls == 1] = 0.5
        frac[cls == 2] = 0.0
        return frac

    def label(self, r_eci_m: np.ndarray, epoch: datetime) -> list[str]:
        names = {0: "sun", 1: "penumbra", 2: "umbra"}
        return [names[int(c)] for c in self.classify(r_eci_m, epoch)]
