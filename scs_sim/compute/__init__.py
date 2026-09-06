"""Onboard compute + job scheduler.

Phase: 4 (placeholder)
Completion: 5%

TODO Phase 4: node energy/thermal-aware scheduling (orbital-compute inspired).
"""

from scs_sim.compute.node import ComputeNode, ComputeNodePort
from scs_sim.compute.scheduler import NullScheduler, SchedulerPort

__all__ = ["ComputeNode", "ComputeNodePort", "NullScheduler", "SchedulerPort"]
