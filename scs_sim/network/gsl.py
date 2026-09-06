"""Ground-to-satellite link port.

Phase: 2 (placeholder)
Completion: 5%

TODO Phase 2: gateway catalog, elevation mask, contact windows.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, Sequence


class GSLPort(Protocol):
    name: str

    def visible_gateways(self, sat_id: str, when: datetime) -> Sequence[str]:
        """Gateway ids with elevation above mask."""


class NullGSL:
    """Phase 1 empty ground segment."""

    name = "null_gsl"

    def visible_gateways(self, sat_id: str, when: datetime) -> Sequence[str]:
        # TODO Phase 2: ECEF gateway vs sat LOS + min elevation
        _ = (sat_id, when)
        return ()
