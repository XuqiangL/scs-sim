"""Phase 4 compute node + scheduler tests.

Phase: 4 (tests)
Completion: 100%
"""

from __future__ import annotations

import numpy as np

from scs_sim.compute.engine import apply_assignments, finalize_summary, tick_compute
from scs_sim.compute.jobs import ComputeSummary, Job
from scs_sim.compute.node import ComputeFleet, ComputeNode
from scs_sim.compute.scheduler import GreedyEclipseScheduler


def test_idle_power_less_than_busy() -> None:
    node = ComputeNode(
        sat_id="s0",
        flops=2e13,
        memory_bytes=32 * 1024**3,
        idle_w=90.0,
        busy_w=450.0,
    )
    assert node.idle_w < node.busy_w
    fleet = ComputeFleet(["a", "b"], node)
    assert np.all(fleet.load_w() == 90.0)
    fleet.assign("a", "job", 1e12)
    assert fleet.load_w()[0] == 450.0
    assert fleet.load_w()[1] == 90.0


def test_scheduler_skips_empty_battery() -> None:
    sched = GreedyEclipseScheduler(min_soc=0.12)
    jobs = [Job(job_id="j1", flops=1e12)]
    sat_ids = ["dead", "ok"]
    assigns = sched.place(
        jobs,
        sat_ids,
        soc=np.array([0.0, 0.8]),
        sunlight=np.array([1.0, 1.0]),
        sunlight_next=np.array([1.0, 1.0]),
        reachable={"dead": frozenset(), "ok": frozenset()},
        busy=[False, False],
    )
    assert len(assigns) == 1
    assert assigns[0].sat_id == "ok"


def test_job_completes_in_sunny_scenario() -> None:
    node = ComputeNode(
        sat_id="_",
        flops=2.0e13,
        memory_bytes=8,
        idle_w=80.0,
        busy_w=200.0,
    )
    fleet = ComputeFleet(["sat-sun"], node)
    jobs = [Job(job_id="quick", flops=1.0e12)]
    sched = GreedyEclipseScheduler(min_soc=0.1)
    assigns = sched.place(
        jobs,
        ["sat-sun"],
        soc=np.array([0.9]),
        sunlight=np.array([1.0]),
        sunlight_next=np.array([1.0]),
        reachable={"sat-sun": frozenset()},
        busy=fleet.busy,
    )
    assert assigns
    apply_assignments(jobs, fleet, assigns, step=0)
    summary = ComputeSummary()
    tick_compute(
        jobs,
        fleet,
        soc=np.array([0.9]),
        dt_s=60.0,
        step=0,
        t_utc="2026-09-06T00:00:00Z",
        sunlight=np.array([1.0]),
        summary=summary,
    )
    finalize_summary(jobs, summary)
    assert jobs[0].status == "completed"
    assert summary.completed == 1
    assert summary.energy_j > 0.0
