"""ECI / ECEF helpers and Keplerian → ECI conversion.

Phase: 1 (core)
Completion: 85%

Phase-1 frames ignore polar motion, nutation, and precession. The ECI frame
is a mean-equator / mean-equinox style inertial frame consistent with the
Kepler+J2 propagator. SGP4 positions are TEME; we treat TEME≈ECI here.
"""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np

from scs_sim.clock import ensure_utc
from scs_sim.constants import J2000_JD, JD_UNIX_EPOCH, SECONDS_PER_DAY


def julian_date(dt: datetime) -> float:
    """UTC datetime → Julian Date (days)."""
    dt = ensure_utc(dt)
    return dt.timestamp() / SECONDS_PER_DAY + JD_UNIX_EPOCH


def gmst_rad(dt: datetime) -> float:
    """Greenwich mean sidereal time (IAU-82 / Vallado approx), radians."""
    dt = ensure_utc(dt)
    d = julian_date(dt) - J2000_JD
    # Vallado, Fundamentals of Astrodynamics, GMST in degrees
    theta_deg = 280.46061837 + 360.98564736629 * d
    return np.deg2rad(np.mod(theta_deg, 360.0))


def eci_to_ecef(r_eci: np.ndarray, dt: datetime) -> np.ndarray:
    """Rotate ECI → ECEF about +Z by GMST. ``r_eci`` shape (3,) or (N, 3)."""
    g = gmst_rad(dt)
    c, s = np.cos(g), np.sin(g)
    r = np.asarray(r_eci, dtype=float)
    if r.ndim == 1:
        x, y, z = r
        return np.array([c * x + s * y, -s * x + c * y, z], dtype=float)
    x, y, z = r[:, 0], r[:, 1], r[:, 2]
    out = np.empty_like(r)
    out[:, 0] = c * x + s * y
    out[:, 1] = -s * x + c * y
    out[:, 2] = z
    return out


def ecef_to_eci(r_ecef: np.ndarray, dt: datetime) -> np.ndarray:
    """Inverse of :func:`eci_to_ecef`."""
    g = gmst_rad(dt)
    c, s = np.cos(g), np.sin(g)
    r = np.asarray(r_ecef, dtype=float)
    if r.ndim == 1:
        x, y, z = r
        return np.array([c * x - s * y, s * x + c * y, z], dtype=float)
    x, y, z = r[:, 0], r[:, 1], r[:, 2]
    out = np.empty_like(r)
    out[:, 0] = c * x - s * y
    out[:, 1] = s * x + c * y
    out[:, 2] = z
    return out


def eccentric_anomaly(M: np.ndarray, e: np.ndarray, *, tol: float = 1e-12, n_iter: int = 16) -> np.ndarray:
    """Vectorized Newton-Raphson Kepler equation (elliptic)."""
    M = np.mod(np.asarray(M, dtype=float), 2.0 * np.pi)
    e = np.asarray(e, dtype=float)
    E = np.where(e < 0.8, M, np.pi * np.ones_like(M))
    for _ in range(n_iter):
        f = E - e * np.sin(E) - M
        dE = f / (1.0 - e * np.cos(E))
        E = E - dE
        if np.max(np.abs(dE)) < tol:
            break
    return E


def keplerian_to_eci_m(
    a_m: np.ndarray,
    e: np.ndarray,
    i_rad: np.ndarray,
    raan_rad: np.ndarray,
    argp_rad: np.ndarray,
    m_rad: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Convert classical elements to ECI position (m) and velocity (m/s).

    Returns
    -------
    r_eci_m : (N, 3)
    v_eci_m_s : (N, 3)
    """
    from scs_sim.constants import MU_EARTH_M3_S2

    a = np.asarray(a_m, dtype=float)
    e = np.asarray(e, dtype=float)
    i = np.asarray(i_rad, dtype=float)
    raan = np.asarray(raan_rad, dtype=float)
    argp = np.asarray(argp_rad, dtype=float)
    M = np.asarray(m_rad, dtype=float)

    E = eccentric_anomaly(M, e)
    sin_E, cos_E = np.sin(E), np.cos(E)
    sqrt_1e2 = np.sqrt(np.maximum(1.0 - e * e, 0.0))
    # True anomaly
    nu = np.arctan2(sqrt_1e2 * sin_E, cos_E - e)
    r_mag = a * (1.0 - e * cos_E)

    cos_u = np.cos(argp + nu)
    sin_u = np.sin(argp + nu)
    cos_raan, sin_raan = np.cos(raan), np.sin(raan)
    cos_i, sin_i = np.cos(i), np.sin(i)

    r = np.empty((a.shape[0], 3), dtype=float)
    r[:, 0] = r_mag * (cos_raan * cos_u - sin_raan * sin_u * cos_i)
    r[:, 1] = r_mag * (sin_raan * cos_u + cos_raan * sin_u * cos_i)
    r[:, 2] = r_mag * (sin_u * sin_i)

    # Vis-viva / PQW velocity then same rotation
    # Perifocal velocity
    vx_pqw = -np.sqrt(MU_EARTH_M3_S2 * a) / r_mag * sin_E
    vy_pqw = np.sqrt(MU_EARTH_M3_S2 * a) / r_mag * sqrt_1e2 * cos_E
    # Rotate PQW → ECI using ω, i, Ω (ν already in r; use ω+ν frame for r,
    # so velocity uses the same PQW axes: e_r / e_θ via ω then i, Ω)
    # Standard: rotate (vx_pqw, vy_pqw, 0) by R3(Ω) R1(i) R3(ω)
    cos_w, sin_w = np.cos(argp), np.sin(argp)
    px = cos_w * vx_pqw - sin_w * vy_pqw
    py = sin_w * vx_pqw + cos_w * vy_pqw
    v = np.empty_like(r)
    v[:, 0] = cos_raan * px - sin_raan * cos_i * py
    v[:, 1] = sin_raan * px + cos_raan * cos_i * py
    v[:, 2] = sin_i * py
    return r, v


def utc_now_dummy() -> datetime:
    """Timezone helper kept for tests."""
    return datetime.now(timezone.utc)
