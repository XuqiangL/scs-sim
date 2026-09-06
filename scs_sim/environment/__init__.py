"""Space environment models.

Phase: 3 (minimal physics)
Completion: 70%

Eclipse + exponential atmosphere are implemented. Radiation stays a TODO port.
"""

from scs_sim.environment.atmosphere import (
    AtmospherePort,
    ExponentialAtmosphere,
    NullAtmosphere,
    make_atmosphere,
)
from scs_sim.environment.eclipse import CylindricalEclipse, EclipsePort, NullEclipse
from scs_sim.environment.radiation import NullRadiation, RadiationPort
from scs_sim.environment.sun import sun_unit_eci

__all__ = [
    "AtmospherePort",
    "CylindricalEclipse",
    "EclipsePort",
    "ExponentialAtmosphere",
    "NullAtmosphere",
    "NullEclipse",
    "NullRadiation",
    "RadiationPort",
    "make_atmosphere",
    "sun_unit_eci",
]
