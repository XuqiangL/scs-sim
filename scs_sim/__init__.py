"""SCS-Sim — Starlink-like compute constellation simulator.

Phase: 2 (network) + 3 (minimal environment)
Completion: 32% of full product
"""

from scs_sim.config import SimConfig, load_config

__version__ = "0.2.0"
__phase__ = 2
__completion_pct__ = 32

__all__ = ["SimConfig", "load_config", "__version__"]
