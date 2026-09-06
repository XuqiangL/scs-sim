"""Inter-satellite link topology port.

Phase: 2 (placeholder)
Completion: 5%

TODO Phase 2: +Grid / Walker neighbors, LOS, range, latency. Do NOT implement
routing or flood-fill here in Phase 1.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, Sequence

import numpy as np


class ISLTopologyPort(Protocol):
    name: str

    def neighbors(self, sat_id: str, when: datetime) -> Sequence[str]:
        """Local ISL peers at ``when``."""

    def adjacency(self, when: datetime) -> np.ndarray:
        """Boolean adjacency matrix (N, N)."""


class NullISL:
    """Phase 1 empty ISL fabric."""

    name = "null_isl"

    def neighbors(self, sat_id: str, when: datetime) -> Sequence[str]:
        # TODO Phase 2: intra-plane ±1 and inter-plane ±1 (+Grid)
        _ = (sat_id, when)
        return ()

    def adjacency(self, when: datetime) -> np.ndarray:
        _ = when
        return np.zeros((0, 0), dtype=bool)
