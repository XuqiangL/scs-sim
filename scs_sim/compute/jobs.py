"""Compute job records.

Phase: 4 (compute)
Completion: 90%
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Job:
    """One onboard GPU/NPU task.

    ``dest_gs``: if set, the scheduler only places the job on a sat that can
    reach that gateway in the current topology snapshot (GSL or multi-hop ISL).
    """

    job_id: str
    flops: float
    dest_gs: str | None = None
    origin_gs: str | None = None
    status: str = "queued"  # queued | running | completed | delayed
    assigned_sat: str | None = None
    remaining_flops: float = 0.0
    submitted_step: int = 0
    started_step: int | None = None
    completed_step: int | None = None
    energy_j: float = 0.0
    delay_reason: str = ""

    def __post_init__(self) -> None:
        if self.remaining_flops <= 0.0:
            self.remaining_flops = float(self.flops)


@dataclass(frozen=True)
class Assignment:
    job_id: str
    sat_id: str


@dataclass
class ScheduleEvent:
    step: int
    t_utc: str
    job_id: str
    sat_id: str
    status: str
    remaining_flops: float
    soc: float
    sunlight: float
    energy_j: float
    notes: str = ""


@dataclass
class ComputeSummary:
    submitted: int = 0
    completed: int = 0
    running: int = 0
    delayed: int = 0
    queued: int = 0
    energy_j: float = 0.0
    events: list[ScheduleEvent] = field(default_factory=list)
