"""Space environment models.

Phase: 3 (placeholder)
Completion: 5%

TODO Phase 3: atmosphere drag, eclipse, radiation. Interfaces only.
"""

from scs_sim.environment.atmosphere import AtmospherePort, NullAtmosphere
from scs_sim.environment.eclipse import EclipsePort, NullEclipse
from scs_sim.environment.radiation import NullRadiation, RadiationPort

__all__ = [
    "AtmospherePort",
    "EclipsePort",
    "NullAtmosphere",
    "NullEclipse",
    "NullRadiation",
    "RadiationPort",
]
