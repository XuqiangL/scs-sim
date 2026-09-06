"""Launch waves, altitude ramp, and ops fleet.

Phase: 5 (ops)
Completion: 90%
"""

from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np

from scs_sim.config import DeploymentConfig, ReplenishAction, WaveConfig
from scs_sim.constellation.walker import concat_batches, generate_walker_shell
from scs_sim.constants import R_EARTH_M
from scs_sim.config import ShellConfig
from scs_sim.ops.lifecycle import (
    EPHEMERIS_STATES,
    TOPOLOGY_STATES,
    OpsEvent,
    SatRecord,
    count_states,
)
from scs_sim.orbit.elements import KeplerianBatch


def _factor_planes(n_sats: int, n_planes: int | None, n_sats_per_plane: int | None) -> tuple[int, int]:
    if n_planes and n_sats_per_plane:
        return int(n_planes), int(n_sats_per_plane)
    if n_planes:
        p = int(n_planes)
        s = max(1, n_sats // p)
        return p, s
    s = min(8, max(1, n_sats))
    while n_sats % s != 0 and s > 1:
        s -= 1
    return max(1, n_sats // s), s


def wave_to_shell(wave: WaveConfig, *, n_sats: int | None = None) -> ShellConfig:
    n = int(n_sats if n_sats is not None else wave.n_sats)
    p, s = _factor_planes(n, wave.n_planes, wave.n_sats_per_plane)
    f = min(int(wave.phasing_f), max(0, p - 1))
    return ShellConfig(
        id=wave.shell_id or wave.wave_id,
        altitude_km=wave.operational_altitude_km,
        inclination_deg=wave.inclination_deg,
        n_planes=p,
        n_sats_per_plane=s,
        phasing_f=f,
        raan_offset_deg=wave.raan_offset_deg,
    )


def generate_wave_batch(wave: WaveConfig, epoch: datetime, sat_id_offset: int = 0) -> KeplerianBatch:
    shell = wave_to_shell(wave)
    batch = generate_walker_shell(shell, epoch, sat_id_offset=sat_id_offset)
    if len(batch) > wave.n_sats:
        batch = batch.take(np.arange(wave.n_sats))
    batch.a_m[:] = R_EARTH_M + wave.parking_altitude_km * 1000.0
    return batch


class OpsFleet:
    """Lifecycle + element batch for a deploying constellation."""

    def __init__(
        self,
        elements: KeplerianBatch,
        records: list[SatRecord],
        cfg: DeploymentConfig,
    ) -> None:
        self.elements = elements
        self.records = records
        self.cfg = cfg
        self._id_to_i = {r.sat_id: i for i, r in enumerate(records)}

    @classmethod
    def from_waves(cls, waves: tuple[WaveConfig, ...], epoch: datetime, cfg: DeploymentConfig) -> OpsFleet:
        batches: list[KeplerianBatch] = []
        records: list[SatRecord] = []
        offset = 0
        for wave in waves:
            batch = generate_wave_batch(wave, epoch, sat_id_offset=offset)
            batches.append(batch)
            for k in range(len(batch)):
                sid = str(batch.sat_id[k])
                records.append(
                    SatRecord(
                        sat_id=sid,
                        wave_id=wave.wave_id,
                        shell_id=wave.shell_id or wave.wave_id,
                        state="planned",
                        launch=wave.launch_epoch,
                        parking_alt_km=wave.parking_altitude_km,
                        operational_alt_km=wave.operational_altitude_km,
                        ramp_s=wave.ramp_seconds,
                        commission_s=wave.commission_seconds,
                        index=offset + k,
                    )
                )
            offset += len(batch)
        if not batches:
            raise ValueError("deployment.waves is empty")
        return cls(concat_batches(batches, epoch), records, cfg)

    def tick(self, now: datetime, step: int) -> list[OpsEvent]:
        events: list[OpsEvent] = []
        decomm_s = self.cfg.decommission_hours * 3600.0
        launched: set[str] = set()
        for rec in self.records:
            prev = rec.state
            nxt = rec.desired_state(now, decomm_s)
            if prev == "ascending" and nxt in {"commissioning", "operational"} and rec.arrived_at is None:
                rec.arrived_at = now
                nxt = rec.desired_state(now, decomm_s)
            if nxt != prev:
                rec.state = nxt
                events.append(
                    OpsEvent(
                        t_utc=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        step=step,
                        kind="state_change",
                        sat_id=rec.sat_id,
                        wave_id=rec.wave_id,
                        detail=f"{prev}->{nxt}",
                    )
                )
                if prev == "planned" and nxt != "planned":
                    launched.add(rec.wave_id)
            alt = rec.altitude_km(now)
            self.elements.a_m[rec.index] = R_EARTH_M + alt * 1000.0
        for wave_id in launched:
            n = sum(1 for r in self.records if r.wave_id == wave_id and r.state != "planned")
            events.append(
                OpsEvent(
                    t_utc=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    step=step,
                    kind="wave_launch",
                    sat_id="*",
                    wave_id=wave_id,
                    detail=f"wave {wave_id} inserted {n} sats",
                )
            )
        return events

    def apply_station_keeping(self) -> None:
        if not self.cfg.station_keeping:
            return
        nudge = np.deg2rad(self.cfg.phase_nudge_deg)
        for rec in self.records:
            if rec.state == "operational":
                self.elements.m_rad[rec.index] = np.mod(
                    self.elements.m_rad[rec.index] + nudge, 2.0 * np.pi
                )

    def request_retire(self, n: int, now: datetime, step: int, wave_id: str | None = None) -> list[OpsEvent]:
        events: list[OpsEvent] = []
        picked = 0
        for rec in self.records:
            if picked >= n:
                break
            if rec.state != "operational":
                continue
            if wave_id and rec.wave_id != wave_id:
                continue
            rec.retire_requested = True
            rec.retire_at = now
            rec.state = "decommissioning"
            picked += 1
            events.append(
                OpsEvent(
                    t_utc=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    step=step,
                    kind="retire",
                    sat_id=rec.sat_id,
                    wave_id=rec.wave_id,
                    detail="operational->decommissioning",
                )
            )
        return events

    def replenish(self, action: ReplenishAction, now: datetime, step: int) -> list[OpsEvent]:
        from scs_sim.config import WaveConfig

        wave = WaveConfig(
            wave_id=f"replenish-{step}",
            launch_epoch=now,
            n_sats=action.n_sats,
            parking_altitude_km=action.parking_altitude_km,
            operational_altitude_km=action.operational_altitude_km,
            inclination_deg=action.inclination_deg,
            shell_id=action.shell_id or "replenish",
            ramp_hours=action.ramp_hours,
            commission_hours=action.commission_hours,
        )
        offset = len(self.records)
        batch = generate_wave_batch(wave, self.elements.epoch, sat_id_offset=offset)
        self.elements = concat_batches([self.elements, batch], self.elements.epoch)
        events: list[OpsEvent] = []
        for k in range(len(batch)):
            sid = str(batch.sat_id[k])
            rec = SatRecord(
                sat_id=sid,
                wave_id=wave.wave_id,
                shell_id=wave.shell_id,
                state="planned",
                launch=now,
                parking_alt_km=wave.parking_altitude_km,
                operational_alt_km=wave.operational_altitude_km,
                ramp_s=wave.ramp_seconds,
                commission_s=wave.commission_seconds,
                index=offset + k,
            )
            rec.state = rec.desired_state(now, self.cfg.decommission_hours * 3600.0)
            self.records.append(rec)
            self._id_to_i[sid] = rec.index
            events.append(
                OpsEvent(
                    t_utc=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    step=step,
                    kind="replenish",
                    sat_id=sid,
                    wave_id=wave.wave_id,
                    detail=f"added at parking {wave.parking_altitude_km:.0f} km",
                )
            )
        return events

    def mask(self, states: set[str]) -> np.ndarray:
        return np.array([r.state in states for r in self.records], dtype=bool)

    def elements_in(self, states: set[str]) -> KeplerianBatch | None:
        idx = np.array([r.index for r in self.records if r.state in states], dtype=int)
        if idx.size == 0:
            return None
        return self.elements.take(idx)

    def topology_elements(self) -> KeplerianBatch | None:
        return self.elements_in(set(TOPOLOGY_STATES))

    def ephemeris_elements(self) -> KeplerianBatch | None:
        return self.elements_in(set(EPHEMERIS_STATES))

    def attach_catalog(
        self,
        batch: KeplerianBatch,
        *,
        wave_id: str = "tle-catalog",
        now: datetime,
    ) -> list[OpsEvent]:
        """Ingest already-on-orbit sats (TLE catalog) as operational."""
        offset = len(self.records)
        self.elements = concat_batches([self.elements, batch], self.elements.epoch)
        events: list[OpsEvent] = []
        for k in range(len(batch)):
            sid = str(batch.sat_id[k])
            rec = SatRecord(
                sat_id=sid,
                wave_id=wave_id,
                shell_id="tle",
                state="operational",
                launch=now,
                parking_alt_km=float(batch.a_m[k] / 1000.0 - R_EARTH_M / 1000.0),
                operational_alt_km=float(batch.a_m[k] / 1000.0 - R_EARTH_M / 1000.0),
                ramp_s=0.0,
                commission_s=0.0,
                arrived_at=now,
                index=offset + k,
            )
            self.records.append(rec)
            events.append(
                OpsEvent(
                    t_utc=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    step=0,
                    kind="tle_ingest",
                    sat_id=sid,
                    wave_id=wave_id,
                    detail="CelesTrak-style TLE mapped to operational elements",
                )
            )
        return events

    def counts(self) -> dict[str, int]:
        return count_states(self.records)
