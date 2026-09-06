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
from scs_sim.constants import FLATTENING, J2000_JD, JD_UNIX_EPOCH, R_EARTH_M, SECONDS_PER_DAY


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


def geodetic_to_ecef_m(
    lat_deg: float | np.ndarray,
    lon_deg: float | np.ndarray,
    alt_m: float | np.ndarray = 0.0,
) -> np.ndarray:
    """WGS-84 geodetic → ECEF metres. Returns (3,) or (N, 3)."""
    lat = np.deg2rad(np.asarray(lat_deg, dtype=float))
    lon = np.deg2rad(np.asarray(lon_deg, dtype=float))
    alt = np.asarray(alt_m, dtype=float)
    e2 = FLATTENING * (2.0 - FLATTENING)
    sl, cl = np.sin(lat), np.cos(lat)
    n_prime = R_EARTH_M / np.sqrt(1.0 - e2 * sl * sl)
    x = (n_prime + alt) * cl * np.cos(lon)
    y = (n_prime + alt) * cl * np.sin(lon)
    z = (n_prime * (1.0 - e2) + alt) * sl
    stacked = np.stack(np.broadcast_arrays(x, y, z), axis=-1)
    if stacked.ndim == 1:
        return stacked
    if stacked.shape == (3,):
        return stacked
    return np.asarray(stacked, dtype=float)


def ecef_to_geodetic_n(r_ecef_m: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """ECEF (N, 3) metres → lat_deg, lon_deg, alt_m arrays (WGS-84 Bowring)."""
    r = np.asarray(r_ecef_m, dtype=float).reshape(-1, 3)
    x, y, z = r[:, 0], r[:, 1], r[:, 2]
    e2 = FLATTENING * (2.0 - FLATTENING)
    lon = np.arctan2(y, x)
    p = np.hypot(x, y)
    lat = np.arctan2(z, p * (1.0 - e2))
    for _ in range(10):
        sl = np.sin(lat)
        n_prime = R_EARTH_M / np.sqrt(1.0 - e2 * sl * sl)
        lat = np.arctan2(z + e2 * n_prime * sl, p)
    sl = np.sin(lat)
    cl = np.cos(lat)
    n_prime = R_EARTH_M / np.sqrt(1.0 - e2 * sl * sl)
    alt = np.where(
        np.abs(cl) > 1e-12,
        p / cl - n_prime,
        np.abs(z) / np.maximum(np.abs(sl), 1e-16) - n_prime * (1.0 - e2),
    )
    return np.rad2deg(lat), np.rad2deg(lon), alt


def ecef_to_geodetic(r_ecef_m: np.ndarray) -> tuple[float, float, float]:
    """ECEF metres → (lat_deg, lon_deg, alt_m), WGS-84 Bowring iteration."""
    lat, lon, alt = ecef_to_geodetic_n(np.asarray(r_ecef_m, dtype=float).reshape(1, 3))
    return float(lat[0]), float(lon[0]), float(alt[0])


def elevation_deg(r_gs_ecef_m: np.ndarray, r_sat_ecef_m: np.ndarray) -> np.ndarray:
    """Elevation of sat(s) above the local geodetic horizon at a ground station.

    ``r_sat_ecef_m`` is (3,) or (N, 3). Uses the ellipsoidal surface normal at
    the station (from ECEF→geodetic) rather than the geocentric radius.
    """
    gs = np.asarray(r_gs_ecef_m, dtype=float).reshape(3)
    sat = np.asarray(r_sat_ecef_m, dtype=float).reshape(-1, 3)
    lat_deg, lon_deg, _alt = ecef_to_geodetic(gs)
    lat, lon = np.deg2rad(lat_deg), np.deg2rad(lon_deg)
    up = np.array(
        [np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)],
        dtype=float,
    )
    rho = sat - gs
    norm = np.linalg.norm(rho, axis=1)
    norm = np.maximum(norm, 1e-9)
    sine = (rho @ up) / norm
    return np.rad2deg(np.arcsin(np.clip(sine, -1.0, 1.0)))


def haversine_m(lat1_deg: float, lon1_deg: float, lat2_deg: float, lon2_deg: float) -> float:
    """Great-circle distance on the WGS-84 sphere (mean radius ≈ R_EARTH)."""
    lat1, lon1, lat2, lon2 = np.deg2rad([lat1_deg, lon1_deg, lat2_deg, lon2_deg])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0) ** 2
    return float(2.0 * R_EARTH_M * np.arcsin(np.sqrt(min(1.0, a))))


def utc_now_dummy() -> datetime:
    """Timezone helper kept for tests."""
    return datetime.now(timezone.utc)
