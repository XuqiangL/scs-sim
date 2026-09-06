"""Telemetry CSV schema: sat_id, t, lat, lon, alt, soc, state.

``alt`` is kilometres (LEO ~350–1100). ``t`` is ISO-8601 UTC.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from scs_sim.clock import ensure_utc


def _parse_t(value: str) -> datetime:
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    return ensure_utc(datetime.fromisoformat(text))


@dataclass(frozen=True)
class TelemetryRow:
    sat_id: str
    t: datetime
    lat_deg: float
    lon_deg: float
    alt_km: float
    soc: float
    state: str

    def t_iso(self) -> str:
        return self.t.strftime("%Y-%m-%dT%H:%M:%SZ")


def load_telemetry_csv(path: str | Path) -> list[TelemetryRow]:
    """Load the twin telemetry / sim-state CSV schema."""
    p = Path(path)
    rows: list[TelemetryRow] = []
    with p.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        required = {"sat_id", "t", "lat", "lon", "alt", "soc", "state"}
        if reader.fieldnames is None:
            raise ValueError(f"{p}: empty CSV")
        have = {h.strip() for h in reader.fieldnames}
        missing = required - have
        if missing:
            raise ValueError(f"{p}: missing columns {sorted(missing)}; expected {sorted(required)}")
        for raw in reader:
            if not raw.get("sat_id"):
                continue
            rows.append(
                TelemetryRow(
                    sat_id=str(raw["sat_id"]).strip(),
                    t=_parse_t(raw["t"]),
                    lat_deg=float(raw["lat"]),
                    lon_deg=float(raw["lon"]),
                    alt_km=float(raw["alt"]),
                    soc=float(raw["soc"]),
                    state=str(raw.get("state") or "").strip() or "unknown",
                )
            )
    return rows


def write_telemetry_csv(path: str | Path, rows: list[TelemetryRow]) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["sat_id", "t", "lat", "lon", "alt", "soc", "state"])
        for r in rows:
            w.writerow(
                [r.sat_id, r.t_iso(), f"{r.lat_deg:.6f}", f"{r.lon_deg:.6f}", f"{r.alt_km:.6f}", f"{r.soc:.4f}", r.state]
            )
    return p
