"""Collected geodetic samples and last-snapshot topology for Phase 6 export."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from scs_sim.config import GroundStationConfig
from scs_sim.network.isl import ISLEdge
from scs_sim.network.topology import TopologySnapshot


@dataclass
class GeodeticSeries:
    """Lon/lat/alt time series for one satellite (CZML / ground tracks)."""

    sat_id: str
    elapsed_s: list[float] = field(default_factory=list)
    lon_deg: list[float] = field(default_factory=list)
    lat_deg: list[float] = field(default_factory=list)
    alt_m: list[float] = field(default_factory=list)


@dataclass
class VizBundle:
    """Everything the Phase 6 writers need from a short demo window."""

    epoch_iso: str
    end_iso: str
    dt_seconds: float
    sat_ids: list[str]
    series: dict[str, GeodeticSeries]
    stations: tuple[GroundStationConfig, ...]
    snapshots: list[TopologySnapshot]
    last_isl: list[ISLEdge]
    soc_mean_by_step: list[float]
    soc_min_by_step: list[float]
    soc_max_by_step: list[float]
    last_soc: np.ndarray
    n_jobs_submitted: int = 0
    n_jobs_completed: int = 0
    n_jobs_running: int = 0
    n_jobs_delayed: int = 0
    n_jobs_queued: int = 0
    compute_energy_j: float = 0.0
    config_name: str = ""
    config_path: str = ""
    n_sats: int = 0
    n_steps: int = 0
    propagator: str = "kepler_j2"
