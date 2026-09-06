"""Load YAML constellation, network, and environment configuration.

Phase: 2 (network) / 3 (environment keys)
Completion: 95%
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from scs_sim.clock import ensure_utc


@dataclass(frozen=True)
class ShellConfig:
    """One Walker-delta shell (circular, equal altitude / inclination)."""

    id: str
    altitude_km: float
    inclination_deg: float
    n_planes: int
    n_sats_per_plane: int
    phasing_f: int
    eccentricity: float = 0.0
    arg_perigee_deg: float = 0.0
    raan_offset_deg: float = 0.0

    @property
    def n_sats(self) -> int:
        return int(self.n_planes) * int(self.n_sats_per_plane)

    def validate(self) -> None:
        if self.n_planes < 1 or self.n_sats_per_plane < 1:
            raise ValueError(f"shell {self.id}: planes and sats_per_plane must be >= 1")
        if not (0 <= self.phasing_f < self.n_planes):
            raise ValueError(
                f"shell {self.id}: phasing_f must satisfy 0 <= F < P "
                f"(got F={self.phasing_f}, P={self.n_planes})"
            )
        if self.altitude_km <= 0:
            raise ValueError(f"shell {self.id}: altitude_km must be positive")
        if not (0.0 <= self.eccentricity < 1.0):
            raise ValueError(f"shell {self.id}: eccentricity must be in [0, 1)")


@dataclass(frozen=True)
class GroundStationConfig:
    id: str
    lat_deg: float
    lon_deg: float
    alt_km: float = 0.0


@dataclass(frozen=True)
class ISLConfig:
    """+Grid / geometric ISL parameters."""

    pattern: str = "plus_grid"
    max_range_km: float = 2500.0
    earth_occlusion: bool = True
    fill_geometric: bool = True
    max_degree: int = 4


@dataclass(frozen=True)
class GSLConfig:
    min_elevation_deg: float = 25.0
    max_attach: int = 2


@dataclass(frozen=True)
class EnvironmentConfig:
    """Phase 3 environment switches. Drag integration is off by default."""

    eclipse: bool = True
    atmosphere: str = "exponential"  # exponential | null
    apply_drag: bool = False
    cd: float = 2.2
    area_m2: float = 4.0
    mass_kg: float = 300.0


@dataclass(frozen=True)
class DemoConfig:
    steps: int = 12
    dt_seconds: float = 60.0
    max_sats: int | None = 100
    output: str = "out/ephemeris_demo.csv"
    subsample: str = "first_shell"  # first_shell | stride
    network: bool = True
    topology_steps: int | None = 4
    topology_output: str = "out/topology_demo.json"
    eclipse_columns: bool = True


@dataclass(frozen=True)
class EarthConfig:
    model: str = "wgs84"


@dataclass(frozen=True)
class SimConfig:
    """Top-level constellation + network + demo configuration."""

    name: str
    epoch: datetime
    propagator: str
    shells: tuple[ShellConfig, ...]
    demo: DemoConfig = field(default_factory=DemoConfig)
    earth: EarthConfig = field(default_factory=EarthConfig)
    isl: ISLConfig = field(default_factory=ISLConfig)
    gsl: GSLConfig = field(default_factory=GSLConfig)
    ground_stations: tuple[GroundStationConfig, ...] = ()
    environment: EnvironmentConfig = field(default_factory=EnvironmentConfig)
    description: str = ""
    path: Path | None = None

    @property
    def n_sats_configured(self) -> int:
        return sum(s.n_sats for s in self.shells)

    def validate(self) -> None:
        if self.propagator not in {"kepler_j2", "sgp4"}:
            raise ValueError(
                f"unknown propagator {self.propagator!r}; expected kepler_j2 or sgp4"
            )
        if not self.shells:
            raise ValueError("at least one shell is required")
        for shell in self.shells:
            shell.validate()
        if self.isl.pattern not in {"plus_grid", "geometric"}:
            raise ValueError(f"unknown ISL pattern {self.isl.pattern!r}")
        if self.isl.max_range_km <= 0:
            raise ValueError("isl.max_range_km must be positive")
        if self.demo.subsample not in {"first_shell", "stride"}:
            raise ValueError("demo.subsample must be first_shell or stride")


def _parse_epoch(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        return ensure_utc(value)
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return ensure_utc(dt)


def _shell_from_dict(raw: dict[str, Any]) -> ShellConfig:
    return ShellConfig(
        id=str(raw["id"]),
        altitude_km=float(raw["altitude_km"]),
        inclination_deg=float(raw["inclination_deg"]),
        n_planes=int(raw["n_planes"]),
        n_sats_per_plane=int(raw["n_sats_per_plane"]),
        phasing_f=int(raw.get("phasing_f", 0)),
        eccentricity=float(raw.get("eccentricity", 0.0)),
        arg_perigee_deg=float(raw.get("arg_perigee_deg", 0.0)),
        raan_offset_deg=float(raw.get("raan_offset_deg", 0.0)),
    )


def _gs_from_dict(raw: dict[str, Any]) -> GroundStationConfig:
    return GroundStationConfig(
        id=str(raw["id"]),
        lat_deg=float(raw["lat_deg"]),
        lon_deg=float(raw["lon_deg"]),
        alt_km=float(raw.get("alt_km", 0.0)),
    )


def load_config(path: str | Path) -> SimConfig:
    """Load and validate a constellation YAML file."""
    cfg_path = Path(path)
    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{cfg_path}: expected a YAML mapping")

    demo_raw = raw.get("demo") or {}
    max_sats = demo_raw.get("max_sats", 100)
    topo_steps = demo_raw.get("topology_steps", 4)
    demo = DemoConfig(
        steps=int(demo_raw.get("steps", 12)),
        dt_seconds=float(demo_raw.get("dt_seconds", 60.0)),
        max_sats=None if max_sats in (None, "all", "none") else int(max_sats),
        output=str(demo_raw.get("output", "out/ephemeris_demo.csv")),
        subsample=str(demo_raw.get("subsample", "first_shell")),
        network=bool(demo_raw.get("network", True)),
        topology_steps=None if topo_steps in (None, "all") else int(topo_steps),
        topology_output=str(demo_raw.get("topology_output", "out/topology_demo.json")),
        eclipse_columns=bool(demo_raw.get("eclipse_columns", True)),
    )
    earth_raw = raw.get("earth") or {}
    earth = EarthConfig(model=str(earth_raw.get("model", "wgs84")))
    shells = tuple(_shell_from_dict(s) for s in raw.get("shells") or [])
    isl_raw = raw.get("isl") or {}
    isl = ISLConfig(
        pattern=str(isl_raw.get("pattern", "plus_grid")),
        max_range_km=float(isl_raw.get("max_range_km", 2500.0)),
        earth_occlusion=bool(isl_raw.get("earth_occlusion", True)),
        fill_geometric=bool(isl_raw.get("fill_geometric", True)),
        max_degree=int(isl_raw.get("max_degree", 4)),
    )
    gsl_raw = raw.get("gsl") or {}
    gsl = GSLConfig(
        min_elevation_deg=float(gsl_raw.get("min_elevation_deg", 25.0)),
        max_attach=int(gsl_raw.get("max_attach", 2)),
    )
    stations = tuple(_gs_from_dict(g) for g in raw.get("ground_stations") or [])
    env_raw = raw.get("environment") or {}
    environment = EnvironmentConfig(
        eclipse=bool(env_raw.get("eclipse", True)),
        atmosphere=str(env_raw.get("atmosphere", "exponential")),
        apply_drag=bool(env_raw.get("apply_drag", False)),
        cd=float(env_raw.get("cd", 2.2)),
        area_m2=float(env_raw.get("area_m2", 4.0)),
        mass_kg=float(env_raw.get("mass_kg", 300.0)),
    )

    cfg = SimConfig(
        name=str(raw.get("name", cfg_path.stem)),
        epoch=_parse_epoch(raw.get("epoch", "2026-01-01T00:00:00Z")),
        propagator=str(raw.get("propagator", "kepler_j2")),
        shells=shells,
        demo=demo,
        earth=earth,
        isl=isl,
        gsl=gsl,
        ground_stations=stations,
        environment=environment,
        description=str(raw.get("description", "")).strip(),
        path=cfg_path,
    )
    cfg.validate()
    return cfg
