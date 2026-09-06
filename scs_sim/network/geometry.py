"""ISL line-of-sight and range helpers (spherical Earth).

Phase: 2 (network)
Completion: 90%

Clean-room: chord closest-approach occlusion, not copied from Hypatia/StarPerf.
"""

from __future__ import annotations

import numpy as np

from scs_sim.constants import R_EARTH_M


def earth_occludes_segment(
    r1_m: np.ndarray,
    r2_m: np.ndarray,
    *,
    radius_m: float = R_EARTH_M,
    margin_m: float = 0.0,
) -> np.ndarray:
    """True when the Earth sphere intersects the open segment r1→r2.

    ``r1_m`` and ``r2_m`` are (3,) or (N, 3). Closest-approach test: if the
    foot of the perpendicular from the origin onto the chord lies inside the
    segment and inside the sphere, the link is blocked.
    """
    a = np.asarray(r1_m, dtype=float).reshape(-1, 3)
    b = np.asarray(r2_m, dtype=float).reshape(-1, 3)
    d = b - a
    dd = np.sum(d * d, axis=1)
    t = np.zeros(dd.shape[0], dtype=float)
    ok = dd > 1e-12
    t[ok] = -np.sum(a[ok] * d[ok], axis=1) / dd[ok]
    on_seg = (t > 0.0) & (t < 1.0)
    closest = a + t[:, None] * d
    dist = np.linalg.norm(closest, axis=1)
    return on_seg & (dist < (radius_m + margin_m))


def pairwise_range_m(r_m: np.ndarray, i: np.ndarray, j: np.ndarray) -> np.ndarray:
    """Euclidean range between index pairs."""
    r = np.asarray(r_m, dtype=float).reshape(-1, 3)
    return np.linalg.norm(r[i] - r[j], axis=1)
