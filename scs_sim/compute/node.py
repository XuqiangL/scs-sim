"""Onboard compute-node interface.

Phase: 4 (placeholder)
Completion: 5%

TODO Phase 4: FLOPs, memory, duty cycle, power draw, thermal headroom.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class ComputeNode:
    """Inventory record for one satellite computer. Unused in Phase 1."""

    sat_id: str
    flops: float = 0.0
    memory_bytes: int = 0
    energy_j: float = 0.0
    notes: str = "TODO Phase 4: bind to power/thermal models"


class ComputeNodePort(Protocol):
    def capacity_flops(self, sat_id: str) -> float: ...

    def available(self, sat_id: str) -> bool: ...


class NullComputeInventory:
    """Phase 1 empty inventory."""

    def capacity_flops(self, sat_id: str) -> float:
        # TODO Phase 4
        _ = sat_id
        return 0.0

    def available(self, sat_id: str) -> bool:
        _ = sat_id
        return False

    def nodes(self) -> list[ComputeNode]:
        return []
