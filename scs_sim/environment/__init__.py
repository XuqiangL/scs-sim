"""Space environment models.

Phase: 3 (environment)
Completion: 90%
"""

from scs_sim.environment.atmosphere import (
    AtmospherePort,
    ExponentialAtmosphere,
    NullAtmosphere,
    make_atmosphere,
)
from scs_sim.environment.eclipse import CylindricalEclipse, EclipsePort, NullEclipse
from scs_sim.environment.power import BatteryBank, PowerConfig
from scs_sim.environment.radiation import (
    DoseAccumulator,
    NullRadiation,
    RadiationPort,
    SAARadiation,
    make_radiation,
)
from scs_sim.environment.sun import sun_unit_eci
from scs_sim.environment.thermal import ThermalConfig, ThermalState

__all__ = [
    "AtmospherePort",
    "BatteryBank",
    "CylindricalEclipse",
    "DoseAccumulator",
    "EclipsePort",
    "ExponentialAtmosphere",
    "NullAtmosphere",
    "NullEclipse",
    "NullRadiation",
    "PowerConfig",
    "RadiationPort",
    "SAARadiation",
    "ThermalConfig",
    "ThermalState",
    "make_atmosphere",
    "make_radiation",
    "sun_unit_eci",
]
