"""Load YAML constellation configuration.

Phase: 1 (core)
Completion: 90%
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
class DemoConfig:
    steps: int = 12
    dt_seconds: float = 60.0
    max_sats: int | None = 100
    output: str = "out/ephemeris_demo.csv"


@dataclass(frozen=True)
class EarthConfig:
    model: str = "wgs84"


@dataclass(frozen=True)
class SimConfig:
    """Top-level constellation + demo configuration."""

    name: str
    epoch: datetime
    propagator: str
    shells: tuple[ShellConfig, ...]
    demo: DemoConfig = field(default_factory=DemoConfig)
    earth: EarthConfig = field(default_factory=EarthConfig)
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
        if self.n_sats_configured > 10_000 and self.demo.max_sats is None:
            # Allowed — config must support 10000+ — just a reminder for operators.
            pass


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


def load_config(path: str | Path) -> SimConfig:
    """Load and validate a constellation YAML file."""
    cfg_path = Path(path)
    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{cfg_path}: expected a YAML mapping")

    demo_raw = raw.get("demo") or {}
    max_sats = demo_raw.get("max_sats", 100)
    demo = DemoConfig(
        steps=int(demo_raw.get("steps", 12)),
        dt_seconds=float(demo_raw.get("dt_seconds", 60.0)),
        max_sats=None if max_sats in (None, "all", "none") else int(max_sats),
        output=str(demo_raw.get("output", "out/ephemeris_demo.csv")),
    )
    earth_raw = raw.get("earth") or {}
    earth = EarthConfig(model=str(earth_raw.get("model", "wgs84")))
    shells = tuple(_shell_from_dict(s) for s in raw.get("shells") or [])

    cfg = SimConfig(
        name=str(raw.get("name", cfg_path.stem)),
        epoch=_parse_epoch(raw.get("epoch", "2026-01-01T00:00:00Z")),
        propagator=str(raw.get("propagator", "kepler_j2")),
        shells=shells,
        demo=demo,
        earth=earth,
        description=str(raw.get("description", "")).strip(),
        path=cfg_path,
    )
    cfg.validate()
    return cfg
