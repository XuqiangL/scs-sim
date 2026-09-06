"""Advance running jobs and apply assignments.

Phase: 4 (compute)
Completion: 90%
"""

from __future__ import annotations

from scs_sim.compute.jobs import Assignment, ComputeSummary, Job, ScheduleEvent
from scs_sim.compute.node import ComputeFleet


def apply_assignments(jobs: list[Job], fleet: ComputeFleet, assigns: list[Assignment], step: int) -> None:
    by_id = {j.job_id: j for j in jobs}
    for a in assigns:
        job = by_id.get(a.job_id)
        if job is None or job.status != "queued":
            continue
        if not fleet.available(a.sat_id):
            continue
        job.status = "running"
        job.assigned_sat = a.sat_id
        job.started_step = step
        job.remaining_flops = float(job.flops)
        fleet.assign(a.sat_id, job.job_id, job.flops)


def tick_compute(
    jobs: list[Job],
    fleet: ComputeFleet,
    *,
    soc,
    dt_s: float,
    step: int,
    t_utc: str,
    sunlight,
    summary: ComputeSummary,
) -> None:
    """Progress running jobs; stall if the host battery is empty."""
    import numpy as np

    soc_a = np.asarray(soc, dtype=float)
    sun_a = np.asarray(sunlight, dtype=float)
    for i, sid in enumerate(fleet.sat_id):
        jid = fleet.job_id[i]
        if jid is None:
            continue
        job = next((j for j in jobs if j.job_id == jid), None)
        if job is None:
            fleet.clear(str(sid))
            continue
        if soc_a[i] <= 1e-9:
            job.status = "delayed"
            job.delay_reason = "empty_battery"
            summary.events.append(
                ScheduleEvent(
                    step=step,
                    t_utc=t_utc,
                    job_id=job.job_id,
                    sat_id=str(sid),
                    status=job.status,
                    remaining_flops=job.remaining_flops,
                    soc=float(soc_a[i]),
                    sunlight=float(sun_a[i]),
                    energy_j=job.energy_j,
                    notes="stalled: empty battery",
                )
            )
            continue
        work = float(fleet.flops[i]) * float(dt_s)
        used = min(work, job.remaining_flops)
        job.remaining_flops = max(0.0, job.remaining_flops - used)
        energy = float(fleet.busy_w) * float(dt_s) * (used / work if work > 0 else 1.0)
        job.energy_j += energy
        summary.energy_j += energy
        fleet.remaining_flops[i] = job.remaining_flops
        if job.remaining_flops <= 1e-6:
            job.remaining_flops = 0.0
            job.status = "completed"
            job.completed_step = step
            fleet.clear(str(sid))
            summary.events.append(
                ScheduleEvent(
                    step=step,
                    t_utc=t_utc,
                    job_id=job.job_id,
                    sat_id=str(sid),
                    status="completed",
                    remaining_flops=0.0,
                    soc=float(soc_a[i]),
                    sunlight=float(sun_a[i]),
                    energy_j=job.energy_j,
                    notes="done",
                )
            )
        else:
            summary.events.append(
                ScheduleEvent(
                    step=step,
                    t_utc=t_utc,
                    job_id=job.job_id,
                    sat_id=str(sid),
                    status="running",
                    remaining_flops=job.remaining_flops,
                    soc=float(soc_a[i]),
                    sunlight=float(sun_a[i]),
                    energy_j=job.energy_j,
                    notes="",
                )
            )


def finalize_summary(jobs: list[Job], summary: ComputeSummary) -> ComputeSummary:
    for job in jobs:
        if job.status == "queued":
            job.status = "delayed"
            job.delay_reason = job.delay_reason or "never_placed"
    summary.submitted = len(jobs)
    summary.completed = sum(1 for j in jobs if j.status == "completed")
    summary.running = sum(1 for j in jobs if j.status == "running")
    summary.queued = sum(1 for j in jobs if j.status == "queued")
    summary.delayed = sum(1 for j in jobs if j.status == "delayed")
    return summary
