"""Load YAML constellation, network, environment, compute, ops, viz, and catalog configuration.

Phase: 1–8
Completion: 97%
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from scs_sim.clock import ensure_utc
from scs_sim.environment.power import PowerConfig
from scs_sim.environment.thermal import ThermalConfig


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
    atmosphere_scale: float = 1.0  # multiplies exponential ρ_ref (UI / runtime)


@dataclass(frozen=True)
class RadiationConfig:
    model: str = "saa_heuristic"
    peak_flux_cm2_s: float = 2000.0


@dataclass(frozen=True)
class JobConfig:
    id: str
    flops: float
    dest_gs: str | None = None
    origin_gs: str | None = None


@dataclass(frozen=True)
class ComputeConfig:
    enabled: bool = False
    flops: float = 2.0e13
    memory_gib: float = 32.0
    idle_w: float = 90.0
    busy_w: float = 450.0
    min_soc: float = 0.12
    jobs: tuple[JobConfig, ...] = ()


@dataclass(frozen=True)
class DemoConfig:
    steps: int = 12
    dt_seconds: float = 60.0
    max_sats: int | None = 100
    output: str = "out/ephemeris_demo.csv"
    subsample: str = "first_shell"  # first_shell | stride | spread_planes
    network: bool = True
    topology_steps: int | None = 4
    topology_output: str = "out/topology_demo.json"
    eclipse_columns: bool = True
    environment_output: str = "out/environment_demo.csv"
    compute_output: str = "out/compute_schedule.csv"
    ops_timeline: str = "out/ops_timeline.json"
    ops_events: str = "out/ops_events.csv"
    ops_html: str = "out/ops_timeline.html"
    czml_output: str = "out/constellation.czml"
    viz_html: str = "out/viz_globe.html"
    tracks_png: str = "out/ground_tracks.png"
    tracks_svg: str = "out/ground_tracks.svg"
    kpi_json: str = "out/kpi_dashboard.json"
    kpi_md: str = "out/kpi_report.md"
    max_isl_czml: int = 16


@dataclass(frozen=True)
class WaveConfig:
    wave_id: str
    launch_epoch: datetime
    n_sats: int
    parking_altitude_km: float
    operational_altitude_km: float
    inclination_deg: float
    shell_id: str = ""
    n_planes: int | None = None
    n_sats_per_plane: int | None = None
    phasing_f: int = 1
    ramp_days: float = 0.0
    ramp_hours: float = 12.0
    commission_days: float = 0.0
    commission_hours: float = 4.0
    raan_offset_deg: float = 0.0

    @property
    def ramp_seconds(self) -> float:
        if self.ramp_days > 0:
            return float(self.ramp_days) * 86400.0
        return float(self.ramp_hours) * 3600.0

    @property
    def commission_seconds(self) -> float:
        if self.commission_days > 0:
            return float(self.commission_days) * 86400.0
        return float(self.commission_hours) * 3600.0


@dataclass(frozen=True)
class ReplenishAction:
    step: int
    n_sats: int
    shell_id: str = ""
    parking_altitude_km: float = 350.0
    operational_altitude_km: float = 550.0
    inclination_deg: float = 53.0
    ramp_hours: float = 2.0
    commission_hours: float = 1.0


@dataclass(frozen=True)
class RetireAction:
    step: int
    n_sats: int
    wave_id: str | None = None


@dataclass(frozen=True)
class DeploymentConfig:
    waves: tuple[WaveConfig, ...] = ()
    replenish: tuple[ReplenishAction, ...] = ()
    retire: tuple[RetireAction, ...] = ()
    tle_path: str | None = None
    station_keeping: bool = True
    phase_nudge_deg: float = 0.02
    conjunction: bool = True
    conjunction_threshold_km: float = 40.0
    conjunction_sample: int = 40
    decommission_hours: float = 1.0


@dataclass(frozen=True)
class CatalogConfig:
    """CelesTrak / local TLE. ``fetch`` is opt-in so CI stays offline."""

    fetch: bool = False
    url: str = "https://celestrak.org/NORAD/elements/gp.php?GROUP=starlink&FORMAT=tle"
    cache_path: str = "out/starlink.tle"
    tle_path: str | None = None


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
    power: PowerConfig = field(default_factory=PowerConfig)
    thermal: ThermalConfig = field(default_factory=ThermalConfig)
    radiation: RadiationConfig = field(default_factory=RadiationConfig)
    compute: ComputeConfig = field(default_factory=ComputeConfig)
    deployment: DeploymentConfig = field(default_factory=DeploymentConfig)
    catalog: CatalogConfig = field(default_factory=CatalogConfig)
    description: str = ""
    path: Path | None = None

    @property
    def n_sats_configured(self) -> int:
        return sum(s.n_sats for s in self.shells)

    def validate(self) -> None:
        if self.propagator not in {"kepler_j2", "kepler_j2_gpu", "gpu", "cuda", "kepler_gpu", "sgp4", "orekit"}:
            raise ValueError(
                f"unknown propagator {self.propagator!r}; expected kepler_j2, kepler_j2_gpu, sgp4, or orekit"
            )
        if not self.shells:
            raise ValueError("at least one shell is required")
        for shell in self.shells:
            shell.validate()
        if self.isl.pattern not in {"plus_grid", "geometric"}:
            raise ValueError(f"unknown ISL pattern {self.isl.pattern!r}")
        if self.isl.max_range_km <= 0:
            raise ValueError("isl.max_range_km must be positive")
        if self.demo.subsample not in {"first_shell", "stride", "spread_planes"}:
            raise ValueError("demo.subsample must be first_shell, stride, or spread_planes")
        if self.compute.enabled and self.compute.busy_w < self.compute.idle_w:
            raise ValueError("compute.busy_w must be >= idle_w")
        if not (0.0 <= self.power.initial_soc <= 1.0):
            raise ValueError("power.initial_soc must be in [0, 1]")
        if self.environment.atmosphere_scale < 0.0:
            raise ValueError("environment.atmosphere_scale must be >= 0")


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
        environment_output=str(demo_raw.get("environment_output", "out/environment_demo.csv")),
        compute_output=str(demo_raw.get("compute_output", "out/compute_schedule.csv")),
        ops_timeline=str(demo_raw.get("ops_timeline", "out/ops_timeline.json")),
        ops_events=str(demo_raw.get("ops_events", "out/ops_events.csv")),
        ops_html=str(demo_raw.get("ops_html", "out/ops_timeline.html")),
        czml_output=str(demo_raw.get("czml_output", "out/constellation.czml")),
        viz_html=str(demo_raw.get("viz_html", "out/viz_globe.html")),
        tracks_png=str(demo_raw.get("tracks_png", "out/ground_tracks.png")),
        tracks_svg=str(demo_raw.get("tracks_svg", "out/ground_tracks.svg")),
        kpi_json=str(demo_raw.get("kpi_json", "out/kpi_dashboard.json")),
        kpi_md=str(demo_raw.get("kpi_md", "out/kpi_report.md")),
        max_isl_czml=int(demo_raw.get("max_isl_czml", 16)),
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
        atmosphere_scale=float(env_raw.get("atmosphere_scale", 1.0)),
    )
    pwr_raw = raw.get("power") or {}
    power = PowerConfig(
        panel_area_m2=float(pwr_raw.get("panel_area_m2", 8.0)),
        panel_efficiency=float(pwr_raw.get("panel_efficiency", 0.28)),
        solar_constant_w_m2=float(pwr_raw.get("solar_constant_w_m2", 1361.0)),
        battery_capacity_wh=float(pwr_raw.get("battery_capacity_wh", 200.0)),
        initial_soc=float(pwr_raw.get("initial_soc", 0.75)),
        charge_efficiency=float(pwr_raw.get("charge_efficiency", 0.95)),
        platform_idle_w=float(pwr_raw.get("platform_idle_w", 50.0)),
        max_charge_w=float(pwr_raw.get("max_charge_w", 600.0)),
    )
    th_raw = raw.get("thermal") or {}
    thermal = ThermalConfig(
        mass_kg=float(th_raw.get("mass_kg", 300.0)),
        cp_j_kg_k=float(th_raw.get("cp_j_kg_k", 900.0)),
        area_m2=float(th_raw.get("area_m2", 6.0)),
        absorptivity=float(th_raw.get("absorptivity", 0.65)),
        emissivity=float(th_raw.get("emissivity", 0.80)),
        initial_temp_k=float(th_raw.get("initial_temp_k", 290.0)),
        solar_constant_w_m2=float(th_raw.get("solar_constant_w_m2", 1361.0)),
    )
    rad_raw = raw.get("radiation") or {}
    radiation = RadiationConfig(
        model=str(rad_raw.get("model", "saa_heuristic")),
        peak_flux_cm2_s=float(rad_raw.get("peak_flux_cm2_s", 2000.0)),
    )
    cmp_raw = raw.get("compute") or {}
    jobs = tuple(
        JobConfig(
            id=str(j["id"]),
            flops=float(j["flops"]),
            dest_gs=None if j.get("dest_gs") in (None, "", "none") else str(j.get("dest_gs")),
            origin_gs=None if j.get("origin_gs") in (None, "", "none") else str(j.get("origin_gs")),
        )
        for j in (cmp_raw.get("jobs") or [])
    )
    compute = ComputeConfig(
        enabled=bool(cmp_raw.get("enabled", bool(jobs))),
        flops=float(cmp_raw.get("flops", 2.0e13)),
        memory_gib=float(cmp_raw.get("memory_gib", 32.0)),
        idle_w=float(cmp_raw.get("idle_w", 90.0)),
        busy_w=float(cmp_raw.get("busy_w", 450.0)),
        min_soc=float(cmp_raw.get("min_soc", 0.12)),
        jobs=jobs,
    )
    dep_raw = raw.get("deployment") or {}
    waves = tuple(
        WaveConfig(
            wave_id=str(w["wave_id"]),
            launch_epoch=_parse_epoch(w.get("launch_epoch", raw.get("epoch", "2026-01-01T00:00:00Z"))),
            n_sats=int(w["n_sats"]),
            parking_altitude_km=float(w.get("parking_altitude_km", 350.0)),
            operational_altitude_km=float(w.get("operational_altitude_km", 550.0)),
            inclination_deg=float(w.get("inclination_deg", 53.0)),
            shell_id=str(w.get("shell_id") or w["wave_id"]),
            n_planes=None if w.get("n_planes") is None else int(w["n_planes"]),
            n_sats_per_plane=None if w.get("n_sats_per_plane") is None else int(w["n_sats_per_plane"]),
            phasing_f=int(w.get("phasing_f", 1)),
            ramp_days=float(w.get("ramp_days", 0.0)),
            ramp_hours=float(w.get("ramp_hours", 12.0)),
            commission_days=float(w.get("commission_days", 0.0)),
            commission_hours=float(w.get("commission_hours", 4.0)),
            raan_offset_deg=float(w.get("raan_offset_deg", 0.0)),
        )
        for w in (dep_raw.get("waves") or [])
    )
    replenish = tuple(
        ReplenishAction(
            step=int(a["step"]),
            n_sats=int(a["n_sats"]),
            shell_id=str(a.get("shell_id") or ""),
            parking_altitude_km=float(a.get("parking_altitude_km", 350.0)),
            operational_altitude_km=float(a.get("operational_altitude_km", 550.0)),
            inclination_deg=float(a.get("inclination_deg", 53.0)),
            ramp_hours=float(a.get("ramp_hours", 2.0)),
            commission_hours=float(a.get("commission_hours", 1.0)),
        )
        for a in (dep_raw.get("replenish") or [])
    )
    retire = tuple(
        RetireAction(
            step=int(a["step"]),
            n_sats=int(a["n_sats"]),
            wave_id=None if a.get("wave_id") in (None, "", "none") else str(a["wave_id"]),
        )
        for a in (dep_raw.get("retire") or [])
    )
    tle_path = dep_raw.get("tle_path")
    deployment = DeploymentConfig(
        waves=waves,
        replenish=replenish,
        retire=retire,
        tle_path=None if tle_path in (None, "", "none") else str(tle_path),
        station_keeping=bool(dep_raw.get("station_keeping", True)),
        phase_nudge_deg=float(dep_raw.get("phase_nudge_deg", 0.02)),
        conjunction=bool(dep_raw.get("conjunction", True)),
        conjunction_threshold_km=float(dep_raw.get("conjunction_threshold_km", 40.0)),
        conjunction_sample=int(dep_raw.get("conjunction_sample", 40)),
        decommission_hours=float(dep_raw.get("decommission_hours", 1.0)),
    )
    cat_raw = raw.get("catalog") or {}
    cat_tle = cat_raw.get("tle_path")
    catalog = CatalogConfig(
        fetch=bool(cat_raw.get("fetch", False)),
        url=str(cat_raw.get("url", CatalogConfig.url)),
        cache_path=str(cat_raw.get("cache_path", "out/starlink.tle")),
        tle_path=None if cat_tle in (None, "", "none") else str(cat_tle),
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
        power=power,
        thermal=thermal,
        radiation=radiation,
        compute=compute,
        deployment=deployment,
        catalog=catalog,
        description=str(raw.get("description", "")).strip(),
        path=cfg_path,
    )
    cfg.validate()
    return cfg
