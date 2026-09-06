"""Fleet lifecycle states and transition rules.

Phase: 5 (ops)
Completion: 90%

States: planned → ascending → commissioning → operational
        operational → decommissioning → retired
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Iterable

STATES = (
    "planned",
    "ascending",
    "commissioning",
    "operational",
    "decommissioning",
    "retired",
)

TOPOLOGY_STATES = frozenset({"operational"})
EPHEMERIS_STATES = frozenset({"ascending", "commissioning", "operational", "decommissioning"})


@dataclass
class SatRecord:
    sat_id: str
    wave_id: str
    shell_id: str
    state: str
    launch: datetime
    parking_alt_km: float
    operational_alt_km: float
    ramp_s: float
    commission_s: float
    arrived_at: datetime | None = None
    retire_requested: bool = False
    retire_at: datetime | None = None
    index: int = 0

    def altitude_km(self, now: datetime) -> float:
        """Linear parking → operational ramp after launch."""
        if now < self.launch:
            return self.parking_alt_km
        elapsed = (now - self.launch).total_seconds()
        if self.ramp_s <= 0:
            return self.operational_alt_km
        frac = min(1.0, max(0.0, elapsed / self.ramp_s))
        return self.parking_alt_km + frac * (self.operational_alt_km - self.parking_alt_km)

    def desired_state(self, now: datetime, decommission_s: float) -> str:
        if self.retire_requested:
            if self.retire_at is None:
                return "decommissioning"
            if now >= self.retire_at + timedelta(seconds=decommission_s):
                return "retired"
            return "decommissioning"
        if now < self.launch:
            return "planned"
        alt = self.altitude_km(now)
        if alt < self.operational_alt_km - 0.5:
            return "ascending"
        if self.arrived_at is None:
            return "commissioning"
        if (now - self.arrived_at).total_seconds() < self.commission_s:
            return "commissioning"
        return "operational"


@dataclass
class OpsEvent:
    t_utc: str
    step: int
    kind: str
    sat_id: str
    wave_id: str
    detail: str
    extra: dict = field(default_factory=dict)


def count_states(records: Iterable[SatRecord]) -> dict[str, int]:
    out = {s: 0 for s in STATES}
    for rec in records:
        out[rec.state] = out.get(rec.state, 0) + 1
    return out
