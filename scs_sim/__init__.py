"""SCS-Sim — Starlink-like compute constellation simulator.

Phase: 7 (ops API + packaging + twin)
Completion: 91% of full product
"""

from scs_sim.config import SimConfig, load_config

__version__ = "0.7.0"
__phase__ = 7
__completion_pct__ = 91

__all__ = ["SimConfig", "load_config", "__version__"]
