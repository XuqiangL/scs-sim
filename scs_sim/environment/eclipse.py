"""Solar eclipse / umbra port.

Phase: 3 (placeholder)
Completion: 5%

TODO Phase 3: conical umbra/penumbra from Sun ephemeris (power/thermal).
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

import numpy as np


class EclipsePort(Protocol):
    name: str

    def in_umbra(self, r_eci_m: np.ndarray, epoch: datetime) -> np.ndarray:
        """Boolean mask, shape (N,)."""

    def sunlight_fraction(self, r_eci_m: np.ndarray, epoch: datetime) -> np.ndarray:
        """1 = full sun, 0 = full umbra. Shape (N,)."""


class NullEclipse:
    """Phase 1 no-op: always in sunlight."""

    name = "null_eclipse"

    def in_umbra(self, r_eci_m: np.ndarray, epoch: datetime) -> np.ndarray:
        # TODO Phase 3: cylindrical / conical Earth shadow
        _ = epoch
        n = int(np.asarray(r_eci_m).reshape(-1, 3).shape[0])
        return np.zeros(n, dtype=bool)

    def sunlight_fraction(self, r_eci_m: np.ndarray, epoch: datetime) -> np.ndarray:
        _ = epoch
        n = int(np.asarray(r_eci_m).reshape(-1, 3).shape[0])
        return np.ones(n, dtype=float)
