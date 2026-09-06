"""SCS-Sim — Starlink-like compute constellation simulator.

Phase: 1 (core)
Completion: 10% of full product (Phase 1 stop line)
"""

from scs_sim.config import SimConfig, load_config

__version__ = "0.1.0"
__phase__ = 1
__completion_pct__ = 10

__all__ = ["SimConfig", "load_config", "__version__"]
