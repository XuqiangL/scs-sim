"""Inter-satellite and ground-to-satellite links.

Phase: 2 (placeholder)
Completion: 5%

TODO Phase 2: +Grid ISL, GSL visibility, routing (Hypatia / StarPerf / LEOPath).
"""

from scs_sim.network.gsl import GSLPort, NullGSL
from scs_sim.network.isl import ISLTopologyPort, NullISL

__all__ = ["GSLPort", "ISLTopologyPort", "NullGSL", "NullISL"]
