"""Trapped-particle / SAA radiation port.

Phase: 3 (still TODO)
Completion: 5%

TODO later Phase 3+/4: AP8/AE8 or IRENE flux, South Atlantic Anomaly map,
SEU rates. Not implemented — NullRadiation only.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

import numpy as np


class RadiationPort(Protocol):
    name: str

    def proton_flux_cm2_s(
        self,
        r_ecef_m: np.ndarray,
        epoch: datetime,
    ) -> np.ndarray:
        """Integral proton flux, shape (N,)."""


class NullRadiation:
    """Phase 1 no-op radiation field."""

    name = "null_radiation"

    def proton_flux_cm2_s(self, r_ecef_m: np.ndarray, epoch: datetime) -> np.ndarray:
        # TODO Phase 3: look up trapped-proton maps
        _ = epoch
        n = int(np.asarray(r_ecef_m).reshape(-1, 3).shape[0])
        return np.zeros(n, dtype=float)
