"""Onboard compute-node inventory.

Phase: 4 (compute)
Completion: 90%
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

import numpy as np


@dataclass
class ComputeNode:
    """One satellite computer."""

    sat_id: str
    flops: float
    memory_bytes: int
    idle_w: float
    busy_w: float
    busy: bool = False
    remaining_flops: float = 0.0
    job_id: str | None = None

    def __post_init__(self) -> None:
        if self.busy_w < self.idle_w:
            raise ValueError(f"{self.sat_id}: busy_w must be >= idle_w")
        if self.flops <= 0:
            raise ValueError(f"{self.sat_id}: flops must be positive")


class ComputeNodePort(Protocol):
    def capacity_flops(self, sat_id: str) -> float: ...

    def available(self, sat_id: str) -> bool: ...


class ComputeFleet:
    """Parallel node arrays used by the scheduler and power bus."""

    def __init__(self, sat_ids: Sequence[str], node: ComputeNode) -> None:
        self.sat_id = np.array(list(sat_ids), dtype=object)
        n = len(self.sat_id)
        self.flops = np.full(n, float(node.flops), dtype=float)
        self.memory_bytes = int(node.memory_bytes)
        self.idle_w = float(node.idle_w)
        self.busy_w = float(node.busy_w)
        self.idle_w_sat = np.full(n, self.idle_w, dtype=float)
        self.busy_w_sat = np.full(n, self.busy_w, dtype=float)
        self.power_draw_w = np.full(n, np.nan, dtype=float)
        self.busy = np.zeros(n, dtype=bool)
        self.remaining_flops = np.zeros(n, dtype=float)
        self.job_id: list[str | None] = [None] * n
        self.index = {str(s): i for i, s in enumerate(self.sat_id)}

    def __len__(self) -> int:
        return int(self.sat_id.shape[0])

    def load_w(self) -> np.ndarray:
        base = np.where(self.busy, self.busy_w_sat, self.idle_w_sat)
        return np.where(np.isfinite(self.power_draw_w), self.power_draw_w, base)

    def assign(self, sat_id: str, job_id: str, flops: float) -> None:
        i = self.index[sat_id]
        self.busy[i] = True
        self.remaining_flops[i] = float(flops)
        self.job_id[i] = job_id

    def clear(self, sat_id: str) -> None:
        i = self.index[sat_id]
        self.busy[i] = False
        self.remaining_flops[i] = 0.0
        self.job_id[i] = None

    def capacity_flops(self, sat_id: str) -> float:
        return float(self.flops[self.index[sat_id]])

    def available(self, sat_id: str) -> bool:
        return not bool(self.busy[self.index[sat_id]])

    def nodes(self) -> list[ComputeNode]:
        out: list[ComputeNode] = []
        for i, sid in enumerate(self.sat_id):
            out.append(
                ComputeNode(
                    sat_id=str(sid),
                    flops=float(self.flops[i]),
                    memory_bytes=self.memory_bytes,
                    idle_w=self.idle_w,
                    busy_w=self.busy_w,
                    busy=bool(self.busy[i]),
                    remaining_flops=float(self.remaining_flops[i]),
                    job_id=self.job_id[i],
                )
            )
        return out
