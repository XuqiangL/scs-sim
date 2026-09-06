"""Ground-to-satellite links: elevation mask + nearest visible attach.

Phase: 2 (network)
Completion: 90%
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, Sequence

import numpy as np

from scs_sim.config import GSLConfig, GroundStationConfig
from scs_sim.orbit.frames import elevation_deg, geodetic_to_ecef_m


class GSLPort(Protocol):
    name: str

    def visible_gateways(self, sat_id: str, when: datetime) -> Sequence[str]:
        """Gateway ids with elevation above mask (after ``links_at``)."""


@dataclass(frozen=True)
class GSLEdge:
    gs: str
    sat: str
    elev_deg: float
    range_km: float


class NullGSL:
    """Empty ground segment."""

    name = "null_gsl"

    def visible_gateways(self, sat_id: str, when: datetime) -> Sequence[str]:
        _ = (sat_id, when)
        return ()


def station_ecef_m(gs: GroundStationConfig) -> np.ndarray:
    return geodetic_to_ecef_m(gs.lat_deg, gs.lon_deg, gs.alt_km * 1000.0)


def visible_sats_for_gs(
    gs: GroundStationConfig,
    sat_ids: np.ndarray,
    r_sat_ecef_m: np.ndarray,
    cfg: GSLConfig,
) -> list[GSLEdge]:
    """Sats above ``min_elevation_deg``, nearest-first, capped by ``max_attach``."""
    r_gs = station_ecef_m(gs)
    r_sat = np.asarray(r_sat_ecef_m, dtype=float).reshape(-1, 3)
    elev = elevation_deg(r_gs, r_sat)
    rng_km = np.linalg.norm(r_sat - r_gs, axis=1) / 1000.0
    vis = np.where(elev >= cfg.min_elevation_deg)[0]
    order = vis[np.argsort(rng_km[vis])]
    picked = order[: cfg.max_attach]
    return [
        GSLEdge(
            gs=gs.id,
            sat=str(sat_ids[int(i)]),
            elev_deg=float(elev[int(i)]),
            range_km=float(rng_km[int(i)]),
        )
        for i in picked
    ]


class ElevationGSL:
    """Working GSL builder."""

    name = "elevation_gsl"

    def __init__(
        self,
        stations: Sequence[GroundStationConfig],
        cfg: GSLConfig | None = None,
    ) -> None:
        self.stations = tuple(stations)
        self.cfg = cfg or GSLConfig()
        self._last_by_sat: dict[str, tuple[str, ...]] = {}

    def links_at(
        self,
        sat_ids: np.ndarray,
        r_sat_ecef_m: np.ndarray,
    ) -> list[GSLEdge]:
        edges: list[GSLEdge] = []
        by_sat: dict[str, list[str]] = {}
        for gs in self.stations:
            for e in visible_sats_for_gs(gs, sat_ids, r_sat_ecef_m, self.cfg):
                edges.append(e)
                by_sat.setdefault(e.sat, []).append(e.gs)
        self._last_by_sat = {k: tuple(v) for k, v in by_sat.items()}
        return edges

    def visible_gateways(self, sat_id: str, when: datetime) -> Sequence[str]:
        _ = when
        return self._last_by_sat.get(sat_id, ())
