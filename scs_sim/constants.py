"""WGS-84 / EGM96-ish physical constants used by Phase 1 propagators.

Phase: 1 (core)
Completion: 95%
"""

from __future__ import annotations

# WGS-84
MU_EARTH_M3_S2: float = 3.986004418e14
R_EARTH_M: float = 6_378_137.0
R_EARTH_KM: float = R_EARTH_M / 1000.0
FLATTENING: float = 1.0 / 298.257223563
OMEGA_EARTH_RAD_S: float = 7.2921151467e-5

# Unnormalized J2 (EGM96 / Vallado conventional value)
J2: float = 1.0826266835531513e-3

# Time
SECONDS_PER_DAY: float = 86_400.0
JD_UNIX_EPOCH: float = 2_440_587.5  # 1970-01-01T00:00:00Z
J2000_JD: float = 2_451_545.0
SGP4_EPOCH_JD: float = 2_433_281.5  # 1949-12-31T00:00:00Z

# Minimum eccentricity fed to SGP4 (library is happier than exact 0)
SGP4_MIN_ECC: float = 1.0e-8
