"""SCS-Sim — Starlink-like compute constellation simulator.

Phase: 5 (ops / insertion)
Completion: 62% of full product
"""

from scs_sim.config import SimConfig, load_config

__version__ = "0.5.0"
__phase__ = 5
__completion_pct__ = 62

__all__ = ["SimConfig", "load_config", "__version__"]
