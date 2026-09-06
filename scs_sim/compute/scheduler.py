"""Greedy + eclipse look-ahead scheduler.

Phase: 4 (compute)
Completion: 90%

Prefer sunlight now *and next step*, high SoC, and a path to ``dest_gs``.
Never assign onto SoC below ``min_soc`` or a busy node.
Inspired by orbital-compute look-ahead — clean-room implementation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Mapping, Protocol, Sequence

import numpy as np

from scs_sim.compute.jobs import Assignment, Job
from scs_sim.compute.node import ComputeNode


class SchedulerPort(Protocol):
    name: str

    def schedule(
        self,
        nodes: Sequence[ComputeNode],
        jobs: Sequence[Job],
        now: datetime,
    ) -> list[Assignment]:
        """Legacy port. Prefer :meth:`GreedyEclipseScheduler.place`."""


class NullScheduler:
    name = "null_scheduler"

    def schedule(
        self,
        nodes: Sequence[ComputeNode],
        jobs: Sequence[Job],
        now: datetime,
    ) -> list[Assignment]:
        _ = (nodes, jobs, now)
        return []


class GreedyEclipseScheduler:
    """Score-ranked greedy placer."""

    name = "greedy_eclipse"

    def __init__(self, min_soc: float = 0.12) -> None:
        self.min_soc = float(min_soc)

    def place(
        self,
        pending: Sequence[Job],
        sat_ids: Sequence[str],
        *,
        soc: np.ndarray,
        sunlight: np.ndarray,
        sunlight_next: np.ndarray | None,
        reachable: Mapping[str, frozenset[str]],
        busy: Sequence[bool] | np.ndarray,
        min_soc: float | None = None,
    ) -> list[Assignment]:
        floor = self.min_soc if min_soc is None else float(min_soc)
        sun = np.asarray(sunlight, dtype=float)
        sun_n = sun if sunlight_next is None else np.asarray(sunlight_next, dtype=float)
        soc_a = np.asarray(soc, dtype=float)
        busy_a = np.asarray(busy, dtype=bool)
        taken = set(int(i) for i in np.where(busy_a)[0])
        assignments: list[Assignment] = []
        queued = [j for j in pending if j.status == "queued"]
        queued.sort(key=lambda j: (-float(j.flops), j.job_id))
        for job in queued:
            best_i: int | None = None
            best_score = -1e18
            for i, sid in enumerate(sat_ids):
                if i in taken:
                    continue
                if soc_a[i] < floor:
                    continue
                dest = job.dest_gs
                if dest:
                    if dest not in reachable.get(str(sid), frozenset()):
                        continue
                score = (
                    3.0 * sun[i]
                    + 2.0 * sun_n[i]
                    + 4.0 * soc_a[i]
                    + (5.0 if dest else 0.0)
                    - (4.0 if sun[i] < 0.25 else 0.0)
                )
                if score > best_score:
                    best_score = score
                    best_i = i
            if best_i is None:
                continue
            sid = str(sat_ids[best_i])
            taken.add(best_i)
            assignments.append(Assignment(job_id=job.job_id, sat_id=sid))
        return assignments

    def schedule(
        self,
        nodes: Sequence[ComputeNode],
        jobs: Sequence[Job],
        now: datetime,
    ) -> list[Assignment]:
        _ = now
        sat_ids = [n.sat_id for n in nodes]
        soc = np.ones(len(nodes))
        sun = np.ones(len(nodes))
        busy = [n.busy for n in nodes]
        reach = {n.sat_id: frozenset() for n in nodes}
        return self.place(
            jobs,
            sat_ids,
            soc=soc,
            sunlight=sun,
            sunlight_next=sun,
            reachable=reach,
            busy=busy,
        )
