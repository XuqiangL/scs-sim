"""In-memory ops session used by the local REST API."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Any

import numpy as np

from scs_sim.clock import SimClock
from scs_sim.compute.engine import apply_assignments, finalize_summary, tick_compute
from scs_sim.compute.jobs import ComputeSummary, Job
from scs_sim.compute.node import ComputeFleet, ComputeNode
from scs_sim.compute.scheduler import GreedyEclipseScheduler
from scs_sim.config import SimConfig, load_config
from scs_sim.constellation.walker import generate_constellation
from scs_sim.environment.atmosphere import make_atmosphere
from scs_sim.environment.eclipse import CylindricalEclipse, NullEclipse
from scs_sim.environment.power import BatteryBank
from scs_sim.environment.thermal import ThermalState
from scs_sim.network.reachability import reachable_gateways
from scs_sim.network.routing import build_weighted_graph
from scs_sim.network.topology import TopologyBuilder
from scs_sim.ops.deployment import OpsFleet
from scs_sim.ops.lifecycle import count_states
from scs_sim.orbit.frames import ecef_to_geodetic_n
from scs_sim.orbit.propagator import make_propagator
from scs_sim.viz.kpi import build_kpi, write_kpi
from scs_sim.viz.samples import GeodeticSeries, VizBundle


class SimSession:
    """Load a YAML config and step a compact Walker / ops fleet in memory."""

    def __init__(self) -> None:
        self.cfg: SimConfig | None = None
        self.config_path: Path | None = None
        self.elements = None
        self.prop = None
        self.clock: SimClock | None = None
        self.batteries: BatteryBank | None = None
        self.thermal: ThermalState | None = None
        self.eclipse = None
        self.builder: TopologyBuilder | None = None
        self.fleet: ComputeFleet | None = None
        self.jobs: list[Job] = []
        self.summary = ComputeSummary()
        self.scheduler = GreedyEclipseScheduler()
        self.ops: OpsFleet | None = None
        self.snapshots: list = []
        self.series: dict[str, GeodeticSeries] = {}
        self.soc_mean: list[float] = []
        self.soc_min: list[float] = []
        self.soc_max: list[float] = []
        self.last_kpi: dict[str, Any] | None = None
        self.events: list[dict[str, Any]] = []

    @property
    def loaded(self) -> bool:
        return self.cfg is not None and self.elements is not None

    def _require(self) -> None:
        if not self.loaded or self.cfg is None or self.clock is None:
            raise RuntimeError("no config loaded — POST /config/load first")

    def load(self, path: str | Path, *, max_sats: int | None = None) -> dict[str, Any]:
        cfg_path = Path(path)
        if not cfg_path.is_file():
            raise FileNotFoundError(f"config not found: {cfg_path}")
        cfg = load_config(cfg_path)
        self.cfg = cfg
        self.config_path = cfg_path
        if cfg.deployment.waves:
            self.ops = OpsFleet.from_waves(cfg.deployment.waves, cfg.epoch, cfg.deployment)
            self.elements = self.ops.elements
        else:
            self.ops = None
            self.elements = generate_constellation(cfg, max_sats=max_sats)
        n = len(self.elements)
        atm = make_atmosphere(cfg.environment.atmosphere)
        self.prop = make_propagator(
            cfg.propagator,
            atmosphere=atm,
            apply_drag=cfg.environment.apply_drag,
        )
        self.clock = SimClock(epoch=cfg.epoch, dt_seconds=cfg.demo.dt_seconds)
        self.eclipse = CylindricalEclipse() if cfg.environment.eclipse else NullEclipse()
        self.batteries = BatteryBank(n, cfg.power)
        self.thermal = ThermalState(n, cfg.thermal)
        self.builder = TopologyBuilder(cfg.isl, cfg.gsl, cfg.ground_stations)
        sat_ids = [str(s) for s in self.elements.sat_id]
        template = ComputeNode(
            sat_id="_",
            flops=cfg.compute.flops,
            memory_bytes=int(cfg.compute.memory_gib * 1024**3),
            idle_w=cfg.compute.idle_w,
            busy_w=cfg.compute.busy_w,
        )
        self.fleet = ComputeFleet(sat_ids, template)
        self.jobs = [
            Job(job_id=j.id, flops=j.flops, dest_gs=j.dest_gs, origin_gs=j.origin_gs)
            for j in cfg.compute.jobs
        ]
        self.summary = ComputeSummary()
        self.scheduler = GreedyEclipseScheduler(min_soc=cfg.compute.min_soc)
        self.snapshots = []
        self.series = {sid: GeodeticSeries(sat_id=sid) for sid in sat_ids}
        self.soc_mean = []
        self.soc_min = []
        self.soc_max = []
        self.last_kpi = None
        self.events = []
        return self.status()

    def _sat_ids(self) -> list[str]:
        assert self.elements is not None
        return [str(s) for s in self.elements.sat_id]

    def _states(self) -> dict[str, str]:
        if self.ops is not None:
            return {r.sat_id: r.state for r in self.ops.records}
        return {sid: "operational" for sid in self._sat_ids()}

    def _record_sample(self, lon: np.ndarray, lat: np.ndarray, alt_m: np.ndarray) -> None:
        assert self.clock is not None
        elapsed = self.clock.elapsed_seconds
        for i, sid in enumerate(self._sat_ids()):
            ser = self.series.setdefault(sid, GeodeticSeries(sat_id=sid))
            ser.elapsed_s.append(float(elapsed))
            ser.lon_deg.append(float(lon[i]))
            ser.lat_deg.append(float(lat[i]))
            ser.alt_m.append(float(alt_m[i]))

    def step(self, n: int = 1) -> dict[str, Any]:
        self._require()
        assert self.cfg is not None and self.clock is not None
        assert self.elements is not None and self.prop is not None
        assert self.batteries is not None and self.thermal is not None
        assert self.builder is not None and self.eclipse is not None
        if n < 1:
            raise ValueError("n must be >= 1")
        cfg = self.cfg
        sat_ids = self._sat_ids()
        gs_ids = [g.id for g in cfg.ground_stations]
        for _ in range(int(n)):
            if self.ops is not None:
                ev = self.ops.tick(self.clock.now, self.clock.step)
                self.elements = self.ops.elements
                self.ops.apply_station_keeping()
                for e in ev:
                    self.events.append(
                        {"t_utc": e.t_utc, "step": e.step, "kind": e.kind, "sat_id": e.sat_id, "detail": e.detail}
                    )
                sat_ids = self._sat_ids()
                if self.fleet is not None and len(self.fleet) != len(sat_ids):
                    template = ComputeNode(
                        sat_id="_",
                        flops=cfg.compute.flops,
                        memory_bytes=int(cfg.compute.memory_gib * 1024**3),
                        idle_w=cfg.compute.idle_w,
                        busy_w=cfg.compute.busy_w,
                    )
                    self.fleet = ComputeFleet(sat_ids, template)
                    self.batteries = BatteryBank(len(sat_ids), cfg.power)
                    self.thermal = ThermalState(len(sat_ids), cfg.thermal)
                    self.series = {sid: self.series.get(sid, GeodeticSeries(sat_id=sid)) for sid in sat_ids}

            elapsed = self.clock.elapsed_seconds
            r_eci = self.prop.positions_eci_m(self.elements, elapsed)
            r_ecef = self.prop.positions_ecef_m(self.elements, cfg.epoch, elapsed)
            lat, lon, alt = ecef_to_geodetic_n(r_ecef)
            self._record_sample(lon, lat, alt)
            t_iso = self.clock.now.strftime("%Y-%m-%dT%H:%M:%SZ")
            sun_frac = self.eclipse.sunlight_fraction(r_eci, self.clock.now)

            topo_el = self.ops.topology_elements() if self.ops is not None else self.elements
            if topo_el is not None and len(topo_el) > 0:
                r_eci_t = self.prop.positions_eci_m(topo_el, elapsed)
                r_ecef_t = self.prop.positions_ecef_m(topo_el, cfg.epoch, elapsed)
                snap = self.builder.snapshot(
                    topo_el, r_eci_t, r_ecef_t, when=self.clock.now, step=self.clock.step, route=True
                )
            else:
                snap = self.builder.snapshot(
                    self.elements, r_eci, r_ecef, when=self.clock.now, step=self.clock.step, route=True
                )
            self.snapshots.append(snap)
            adj = build_weighted_graph(
                ((e.a, e.b, e.range_km) for e in snap.isl_edges),
                ((e.gs, e.sat, e.range_km) for e in snap.gsl_edges),
            )
            last_reach = reachable_gateways(sat_ids, gs_ids, adj)

            if self.fleet is not None and self.jobs:
                r_next = self.prop.positions_eci_m(self.elements, elapsed + cfg.demo.dt_seconds)
                sun_next = self.eclipse.sunlight_fraction(
                    r_next, self.clock.now + timedelta(seconds=cfg.demo.dt_seconds)
                )
                assigns = self.scheduler.place(
                    self.jobs,
                    sat_ids,
                    soc=self.batteries.soc,
                    sunlight=sun_frac,
                    sunlight_next=sun_next,
                    reachable=last_reach,
                    busy=self.fleet.busy,
                    min_soc=cfg.compute.min_soc,
                )
                apply_assignments(self.jobs, self.fleet, assigns, self.clock.step)
                tick_compute(
                    self.jobs,
                    self.fleet,
                    soc=self.batteries.soc,
                    dt_s=cfg.demo.dt_seconds,
                    step=self.clock.step,
                    t_utc=t_iso,
                    sunlight=sun_frac,
                    summary=self.summary,
                )
                payload_w = self.fleet.load_w()
            else:
                payload_w = np.zeros(len(sat_ids))

            load_w = cfg.power.platform_idle_w + payload_w
            self.batteries.step(sun_frac, load_w, cfg.demo.dt_seconds)
            self.thermal.step(sun_frac, load_w, cfg.demo.dt_seconds)
            self.soc_mean.append(float(self.batteries.soc.mean()))
            self.soc_min.append(float(self.batteries.soc.min()))
            self.soc_max.append(float(self.batteries.soc.max()))
            self.clock.advance()

        if self.jobs:
            finalize_summary(self.jobs, self.summary)
        self.last_kpi = self._build_kpi()
        write_kpi(Path(cfg.demo.kpi_json), Path(cfg.demo.kpi_md), self.last_kpi)
        return self.status()

    def _build_kpi(self) -> dict[str, Any]:
        assert self.cfg is not None and self.clock is not None and self.batteries is not None
        cfg = self.cfg
        sat_ids = self._sat_ids()
        last_isl = list(self.snapshots[-1].isl_edges) if self.snapshots else []
        if self.jobs:
            finalize_summary(self.jobs, self.summary)
        bundle = VizBundle(
            epoch_iso=cfg.epoch.strftime("%Y-%m-%dT%H:%M:%SZ"),
            end_iso=self.clock.now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            dt_seconds=float(cfg.demo.dt_seconds),
            sat_ids=sat_ids,
            series=self.series,
            stations=cfg.ground_stations,
            snapshots=self.snapshots,
            last_isl=last_isl,
            soc_mean_by_step=self.soc_mean,
            soc_min_by_step=self.soc_min,
            soc_max_by_step=self.soc_max,
            last_soc=self.batteries.soc.copy(),
            n_jobs_submitted=len(self.jobs),
            n_jobs_completed=self.summary.completed,
            n_jobs_running=self.summary.running,
            n_jobs_delayed=self.summary.delayed,
            n_jobs_queued=self.summary.queued,
            compute_energy_j=self.summary.energy_j,
            config_name=cfg.name,
            config_path=str(self.config_path or ""),
            n_sats=len(sat_ids),
            n_steps=self.clock.step,
            propagator=getattr(self.prop, "name", cfg.propagator),
        )
        return build_kpi(bundle)

    def kpi(self) -> dict[str, Any]:
        self._require()
        if self.last_kpi is None:
            self.last_kpi = self._build_kpi()
            assert self.cfg is not None
            write_kpi(Path(self.cfg.demo.kpi_json), Path(self.cfg.demo.kpi_md), self.last_kpi)
        return self.last_kpi

    def sat_states(self, *, limit: int | None = None) -> list[dict[str, Any]]:
        self._require()
        assert self.cfg is not None and self.clock is not None
        assert self.elements is not None and self.prop is not None and self.batteries is not None
        r_ecef = self.prop.positions_ecef_m(self.elements, self.cfg.epoch, self.clock.elapsed_seconds)
        lat, lon, alt = ecef_to_geodetic_n(r_ecef)
        states = self._states()
        busy = {str(s): bool(self.fleet.busy[i]) for i, s in enumerate(self.fleet.sat_id)} if self.fleet else {}
        out: list[dict[str, Any]] = []
        ids = self._sat_ids()
        n = len(ids) if limit is None else min(len(ids), int(limit))
        for i in range(n):
            sid = ids[i]
            out.append(
                {
                    "sat_id": sid,
                    "lat_deg": float(lat[i]),
                    "lon_deg": float(lon[i]),
                    "alt_km": float(alt[i]) / 1000.0,
                    "soc": float(self.batteries.soc[i]),
                    "state": states.get(sid, "operational"),
                    "busy": bool(busy.get(sid, False)),
                }
            )
        return out

    def submit_job(self, job_id: str, flops: float, dest_gs: str | None = None) -> dict[str, Any]:
        self._require()
        if any(j.job_id == job_id for j in self.jobs):
            raise ValueError(f"job {job_id!r} already exists")
        if flops <= 0:
            raise ValueError("flops must be positive")
        job = Job(job_id=job_id, flops=float(flops), dest_gs=dest_gs)
        job.submitted_step = self.clock.step if self.clock else 0
        self.jobs.append(job)
        self.summary.submitted = len(self.jobs)
        return self._job_dict(job)

    def list_jobs(self) -> list[dict[str, Any]]:
        return [self._job_dict(j) for j in self.jobs]

    def _job_dict(self, job: Job) -> dict[str, Any]:
        return {
            "job_id": job.job_id,
            "flops": job.flops,
            "dest_gs": job.dest_gs,
            "status": job.status,
            "assigned_sat": job.assigned_sat,
            "remaining_flops": job.remaining_flops,
        }

    def waves(self) -> dict[str, Any]:
        if self.ops is None:
            return {"waves": [], "counts": {}, "note": "no deployment.waves in this config"}
        by_wave: dict[str, list] = {}
        for rec in self.ops.records:
            by_wave.setdefault(rec.wave_id, []).append(rec)
        waves = []
        for wid, recs in by_wave.items():
            waves.append({"wave_id": wid, "n_sats": len(recs), "states": count_states(recs)})
        return {"waves": waves, "counts": self.ops.counts()}

    def status(self) -> dict[str, Any]:
        if not self.loaded or self.cfg is None or self.clock is None:
            return {"loaded": False}
        return {
            "loaded": True,
            "config": self.cfg.name,
            "config_path": str(self.config_path),
            "n_sats": len(self.elements) if self.elements is not None else 0,
            "step": self.clock.step,
            "t_utc": self.clock.now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "dt_seconds": self.clock.dt_seconds,
            "propagator": getattr(self.prop, "name", self.cfg.propagator),
            "n_jobs": len(self.jobs),
            "waves": self.waves(),
        }
