"""SCS-Sim — Starlink-like compute constellation simulator.

Phase: 8 (catalog align + 10k bench + acceptance)
Completion: 97% of full product
"""

from scs_sim.config import SimConfig, load_config

__version__ = "0.8.0"
__phase__ = 8
__completion_pct__ = 97

__all__ = ["SimConfig", "load_config", "__version__"]
