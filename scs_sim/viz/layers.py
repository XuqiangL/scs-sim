"""Orbital reference geometry for 3D globe layers (equator, planes, shells).

Phase: vNext 3D
Completion: 80%
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from scs_sim.constants import R_EARTH_M


def equator_ring(*, n: int = 128, radius_m: float | None = None) -> list[list[float]]:
    """Return ECEF polyline [x,y,z] meters for the Earth equator."""
    r = float(R_EARTH_M if radius_m is None else radius_m)
    ang = np.linspace(0.0, 2.0 * math.pi, int(n), endpoint=False)
    xs = r * np.cos(ang)
    ys = r * np.sin(ang)
    zs = np.zeros_like(xs)
    return np.column_stack([xs, ys, zs]).tolist()


def orbital_plane_disk(
    *,
    inclination_deg: float,
    raan_deg: float = 0.0,
    radius_m: float,
    n: int = 96,
) -> list[list[float]]:
    """Inclined circular ring in ECEF-ish inertial frame (demo geometry)."""
    i = math.radians(float(inclination_deg))
    O = math.radians(float(raan_deg))
    # R3(O) * R1(i)
    cO, sO = math.cos(O), math.sin(O)
    ci, si = math.cos(i), math.sin(i)
    # rotation matrix rows
    R = np.array(
        [
            [cO, -sO * ci, sO * si],
            [sO, cO * ci, -cO * si],
            [0.0, si, ci],
        ],
        dtype=float,
    )
    ang = np.linspace(0.0, 2.0 * math.pi, int(n), endpoint=False)
    local = np.column_stack([radius_m * np.cos(ang), radius_m * np.sin(ang), np.zeros(n)])
    ecef = local @ R.T
    return ecef.tolist()


def shell_ring(*, altitude_km: float, n: int = 128) -> list[list[float]]:
    r = float(R_EARTH_M) + float(altitude_km) * 1000.0
    return equator_ring(n=n, radius_m=r)


def scene_layers_from_config(shells: list[Any]) -> dict[str, Any]:
    """Build reference layers from Walker shell configs."""
    equator = equator_ring()
    planes: list[dict[str, Any]] = []
    shell_rings: list[dict[str, Any]] = []
    for sh in shells:
        alt = float(getattr(sh, "altitude_km", None) or sh.get("altitude_km"))
        inc = float(getattr(sh, "inclination_deg", None) or sh.get("inclination_deg"))
        planes_n = int(getattr(sh, "planes", None) or sh.get("planes") or 1)
        r = float(R_EARTH_M) + alt * 1000.0
        shell_rings.append({"altitude_km": alt, "ring_ecef_m": shell_ring(altitude_km=alt)})
        # sample a few orbital planes by RAAN spacing
        sample = min(planes_n, 8)
        for k in range(sample):
            raan = 360.0 * k / planes_n
            planes.append(
                {
                    "altitude_km": alt,
                    "inclination_deg": inc,
                    "raan_deg": raan,
                    "ring_ecef_m": orbital_plane_disk(
                        inclination_deg=inc, raan_deg=raan, radius_m=r
                    ),
                }
            )
    return {
        "equator_ecef_m": equator,
        "orbital_planes": planes,
        "shell_rings": shell_rings,
        "earth_radius_m": float(R_EARTH_M),
    }
