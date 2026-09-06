"""Job scheduler port.

Phase: 4 (placeholder)
Completion: 5%

TODO Phase 4: greedy / look-ahead schedulers with eclipse forecasting.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, Sequence

from scs_sim.compute.node import ComputeNode


@dataclass(frozen=True)
class ComputeJob:
    job_id: str
    flops: float
    deadline: datetime | None = None


@dataclass(frozen=True)
class Assignment:
    job_id: str
    sat_id: str


class SchedulerPort(Protocol):
    name: str

    def schedule(
        self,
        nodes: Sequence[ComputeNode],
        jobs: Sequence[ComputeJob],
        now: datetime,
    ) -> list[Assignment]:
        """Assign jobs to nodes. Empty in Phase 1."""


class NullScheduler:
    """Phase 1 no-op scheduler."""

    name = "null_scheduler"

    def schedule(
        self,
        nodes: Sequence[ComputeNode],
        jobs: Sequence[ComputeJob],
        now: datetime,
    ) -> list[Assignment]:
        # TODO Phase 4: implement placement
        _ = (nodes, jobs, now)
        return []
