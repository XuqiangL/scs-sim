"""Propagator port (hexagonal boundary).

Phase: 1 (core)
Completion: 90%

Later adapters (Orekit, jaxsgp4, poliastro) implement this protocol.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

import numpy as np

from scs_sim.orbit.elements import KeplerianBatch


class PropagatorPort(Protocol):
    """Advance Keplerian batches and return ECI / ECEF positions."""

    name: str

    def elements_at(self, elements: KeplerianBatch, elapsed_s: float) -> KeplerianBatch:
        """Return elements at ``epoch + elapsed_s`` (secular rates applied)."""

    def positions_eci_m(self, elements: KeplerianBatch, elapsed_s: float) -> np.ndarray:
        """ECI positions in metres, shape (N, 3)."""

    def positions_ecef_m(
        self,
        elements: KeplerianBatch,
        epoch: datetime,
        elapsed_s: float,
    ) -> np.ndarray:
        """ECEF positions in metres, shape (N, 3)."""
