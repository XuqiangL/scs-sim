"""Low-precision Sun unit vector in ECI (mean-equinox).

Phase: 3 (environment)
Completion: 80%
"""

from __future__ import annotations

from datetime import datetime

import numpy as np

from scs_sim.orbit.frames import julian_date


def sun_unit_eci(dt: datetime) -> np.ndarray:
    """Approximate Sun direction (Meeus / Astronomical Almanac low-precision)."""
    n = julian_date(dt) - 2_451_545.0
    L = np.deg2rad(np.mod(280.460 + 0.9856474 * n, 360.0))
    g = np.deg2rad(np.mod(357.528 + 0.9856003 * n, 360.0))
    lam = L + np.deg2rad(1.915) * np.sin(g) + np.deg2rad(0.020) * np.sin(2.0 * g)
    eps = np.deg2rad(23.439 - 3.56e-7 * n)
    vec = np.array(
        [np.cos(lam), np.cos(eps) * np.sin(lam), np.sin(eps) * np.sin(lam)],
        dtype=float,
    )
    return vec / np.linalg.norm(vec)
