"""SCS-Sim — Starlink-like compute constellation simulator.

Phase: 4 (compute) + 3 (environment complete)
Completion: 50% of full product
"""

from scs_sim.config import SimConfig, load_config

__version__ = "0.4.0"
__phase__ = 4
__completion_pct__ = 50

__all__ = ["SimConfig", "load_config", "__version__"]
