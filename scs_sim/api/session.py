"""In-memory ops session used by the local REST API."""

from __future__ import annotations

import json
import math
from dataclasses import replace
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import numpy as np

from scs_sim.clock import SimClock
from scs_sim.constants import R_EARTH_M
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
from scs_sim.ops.lifecycle import STATES, count_states
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
        self.max_sats: int | None = None
        self.state_lock: dict[str, str] = {}
        self.fleet_overrides: dict[str, Any] = {}
        self.sat_overrides: dict[str, dict[str, Any]] = {}
        self._baseline_elements = None
        self._baseline_soc: np.ndarray | None = None
        self._baseline_temp: np.ndarray | None = None
        self._baseline_flops: np.ndarray | None = None
        self._baseline_states: dict[str, str] = {}
        self.overrides_path = Path("out/overrides.json")

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
        self.max_sats = max_sats
        self.state_lock = {}
        self.fleet_overrides = {}
        self.sat_overrides = {}
        if cfg.deployment.waves:
            self.ops = OpsFleet.from_waves(cfg.deployment.waves, cfg.epoch, cfg.deployment)
            self.elements = self.ops.elements
        else:
            self.ops = None
            self.elements = generate_constellation(cfg, max_sats=max_sats)
        n = len(self.elements)
        atm = make_atmosphere(cfg.environment.atmosphere, rho_scale=cfg.environment.atmosphere_scale)
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
        self._capture_baseline()
        return self.status()

    def _capture_baseline(self) -> None:
        assert self.elements is not None and self.batteries is not None and self.thermal is not None
        self._baseline_elements = self.elements.copy()
        self._baseline_soc = self.batteries.soc.copy()
        self._baseline_temp = self.thermal.temp_k.copy()
        self._baseline_flops = None if self.fleet is None else self.fleet.flops.copy()
        self._baseline_states = dict(self._states())

    def _rebuild_propagator(self) -> None:
        assert self.cfg is not None
        cfg = self.cfg
        atm = make_atmosphere(cfg.environment.atmosphere, rho_scale=cfg.environment.atmosphere_scale)
        self.prop = make_propagator(
            cfg.propagator,
            atmosphere=atm,
            apply_drag=cfg.environment.apply_drag,
        )

    def _rebuild_topology(self) -> None:
        assert self.cfg is not None
        self.builder = TopologyBuilder(self.cfg.isl, self.cfg.gsl, self.cfg.ground_stations)

    def _sat_ids(self) -> list[str]:
        assert self.elements is not None
        return [str(s) for s in self.elements.sat_id]

    def _states(self) -> dict[str, str]:
        if self.ops is not None:
            base = {r.sat_id: r.state for r in self.ops.records}
        else:
            base = {sid: "operational" for sid in self._sat_ids()}
        base.update(self.state_lock)
        return base

    def _apply_state_lock(self) -> None:
        if not self.state_lock or self.ops is None:
            return
        for rec in self.ops.records:
            locked = self.state_lock.get(rec.sat_id)
            if locked is not None:
                rec.state = locked

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
            dt = float(self.clock.dt_seconds)
            if self.ops is not None:
                ev = self.ops.tick(self.clock.now, self.clock.step)
                self.elements = self.ops.elements
                self.ops.apply_station_keeping()
                self._apply_state_lock()
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
                r_next = self.prop.positions_eci_m(self.elements, elapsed + dt)
                sun_next = self.eclipse.sunlight_fraction(
                    r_next, self.clock.now + timedelta(seconds=dt)
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
                    dt_s=dt,
                    step=self.clock.step,
                    t_utc=t_iso,
                    sunlight=sun_frac,
                    summary=self.summary,
                )
                payload_w = self.fleet.load_w()
            else:
                payload_w = np.zeros(len(sat_ids))

            load_w = cfg.power.platform_idle_w + payload_w
            self.batteries.step(sun_frac, load_w, dt)
            self.thermal.step(sun_frac, load_w, dt)
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
            dt_seconds=float(self.clock.dt_seconds),
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
        assert self.thermal is not None and self.eclipse is not None
        elapsed = self.clock.elapsed_seconds
        r_ecef = self.prop.positions_ecef_m(self.elements, self.cfg.epoch, elapsed)
        r_eci = self.prop.positions_eci_m(self.elements, elapsed)
        lat, lon, alt = ecef_to_geodetic_n(r_ecef)
        sun = self.eclipse.sunlight_fraction(r_eci, self.clock.now)
        states = self._states()
        busy = {str(s): bool(self.fleet.busy[i]) for i, s in enumerate(self.fleet.sat_id)} if self.fleet else {}
        degrees = self._isl_degree_map()
        out: list[dict[str, Any]] = []
        ids = self._sat_ids()
        n = len(ids) if limit is None else min(len(ids), int(limit))
        el = self.elements
        for i in range(n):
            sid = ids[i]
            draw = None
            flops = None
            if self.fleet is not None:
                flops = float(self.fleet.flops[i])
                raw = float(self.fleet.power_draw_w[i])
                draw = None if not math.isfinite(raw) else raw
            out.append(
                {
                    "sat_id": sid,
                    "lat_deg": float(lat[i]),
                    "lon_deg": float(lon[i]),
                    "alt_km": float(alt[i]) / 1000.0,
                    "soc": float(self.batteries.soc[i]),
                    "state": states.get(sid, "operational"),
                    "busy": bool(busy.get(sid, False)),
                    "sunlight": float(sun[i]),
                    "in_eclipse": bool(sun[i] < 0.5),
                    "temp_k": float(self.thermal.temp_k[i]),
                    "isl_degree": int(degrees.get(sid, 0)),
                    "a_km": float(el.a_m[i]) / 1000.0,
                    "e": float(el.e[i]),
                    "i_deg": float(np.degrees(el.i_rad[i])),
                    "raan_deg": float(np.degrees(el.raan_rad[i])),
                    "flops": flops,
                    "power_draw_w": draw,
                    "overridden": sid in self.sat_overrides,
                }
            )
        return out

    def _isl_degree_map(self) -> dict[str, int]:
        deg: dict[str, int] = {sid: 0 for sid in self._sat_ids()}
        if not self.snapshots:
            return deg
        for edge in self.snapshots[-1].isl_edges:
            if edge.a in deg:
                deg[edge.a] += 1
            if edge.b in deg:
                deg[edge.b] += 1
        return deg

    def peak_solar_w(self) -> float:
        assert self.cfg is not None
        p = self.cfg.power
        return float(p.panel_area_m2 * p.panel_efficiency * p.solar_constant_w_m2)

    def fleet_params(self) -> dict[str, Any]:
        self._require()
        assert self.cfg is not None and self.clock is not None
        cfg = self.cfg
        return {
            "dt_seconds": float(self.clock.dt_seconds),
            "isl_max_range_km": float(cfg.isl.max_range_km),
            "gsl_min_elevation_deg": float(cfg.gsl.min_elevation_deg),
            "solar_w": self.peak_solar_w(),
            "battery_capacity_wh": float(cfg.power.battery_capacity_wh),
            "apply_drag": bool(cfg.environment.apply_drag),
            "atmosphere_scale": float(cfg.environment.atmosphere_scale),
            "eclipse": bool(cfg.environment.eclipse),
            "compute_flops": float(cfg.compute.flops),
            "idle_w": float(cfg.compute.idle_w),
            "busy_w": float(cfg.compute.busy_w),
        }

    def control_state(self, *, sat_id: str | None = None) -> dict[str, Any]:
        if not self.loaded:
            return {"loaded": False, "states": list(STATES)}
        rows = self.sat_states()
        socs = [r["soc"] for r in rows]
        ecl = [1.0 if r["in_eclipse"] else 0.0 for r in rows]
        temps = [r["temp_k"] for r in rows]
        selected = None
        if sat_id:
            selected = next((r for r in rows if r["sat_id"] == sat_id), None)
            if selected is None:
                raise KeyError(f"unknown sat {sat_id}")
        return {
            **self.status(),
            "states": list(STATES),
            "fleet": self.fleet_params(),
            "fleet_live": {
                "mean_soc": float(np.mean(socs)) if socs else None,
                "min_soc": float(np.min(socs)) if socs else None,
                "eclipse_pct": 100.0 * float(np.mean(ecl)) if ecl else 0.0,
                "mean_temp_k": float(np.mean(temps)) if temps else None,
                "n_isl": len(self.snapshots[-1].isl_edges) if self.snapshots else 0,
            },
            "overrides": {
                "fleet": dict(self.fleet_overrides),
                "sats": {k: dict(v) for k, v in self.sat_overrides.items()},
                "path": str(self.overrides_path),
            },
            "sats": rows,
            "selected": selected,
        }

    def _persist_overrides(self) -> Path:
        self.overrides_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "updated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "config_path": str(self.config_path) if self.config_path else None,
            "fleet": dict(self.fleet_overrides),
            "sats": {k: dict(v) for k, v in self.sat_overrides.items()},
        }
        self.overrides_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return self.overrides_path

    def apply_fleet(self, patch: dict[str, Any]) -> dict[str, Any]:
        self._require()
        assert self.cfg is not None and self.clock is not None and self.batteries is not None
        cfg = self.cfg
        changed: dict[str, Any] = {}
        rebuild_topo = False
        rebuild_prop = False

        if patch.get("dt_seconds") is not None:
            dt = float(patch["dt_seconds"])
            if dt <= 0:
                raise ValueError("dt_seconds must be positive")
            self.clock.dt_seconds = dt
            cfg = replace(cfg, demo=replace(cfg.demo, dt_seconds=dt))
            changed["dt_seconds"] = dt

        if patch.get("isl_max_range_km") is not None:
            rng = float(patch["isl_max_range_km"])
            if rng <= 0:
                raise ValueError("isl_max_range_km must be positive")
            cfg = replace(cfg, isl=replace(cfg.isl, max_range_km=rng))
            changed["isl_max_range_km"] = rng
            rebuild_topo = True

        if patch.get("gsl_min_elevation_deg") is not None:
            elv = float(patch["gsl_min_elevation_deg"])
            if not (-5.0 <= elv <= 90.0):
                raise ValueError("gsl_min_elevation_deg must be in [-5, 90]")
            cfg = replace(cfg, gsl=replace(cfg.gsl, min_elevation_deg=elv))
            changed["gsl_min_elevation_deg"] = elv
            rebuild_topo = True

        if patch.get("solar_w") is not None:
            solar_w = float(patch["solar_w"])
            if solar_w < 0:
                raise ValueError("solar_w must be >= 0")
            p = cfg.power
            denom = max(p.panel_efficiency * p.solar_constant_w_m2, 1e-9)
            new_p = replace(p, panel_area_m2=solar_w / denom)
            cfg = replace(cfg, power=new_p)
            self.batteries.cfg = new_p
            changed["solar_w"] = solar_w

        if patch.get("battery_capacity_wh") is not None:
            cap = float(patch["battery_capacity_wh"])
            if cap <= 0:
                raise ValueError("battery_capacity_wh must be positive")
            new_p = replace(cfg.power, battery_capacity_wh=cap)
            cfg = replace(cfg, power=new_p)
            self.batteries.cfg = new_p
            changed["battery_capacity_wh"] = cap

        if patch.get("apply_drag") is not None:
            drag = bool(patch["apply_drag"])
            cfg = replace(cfg, environment=replace(cfg.environment, apply_drag=drag))
            changed["apply_drag"] = drag
            rebuild_prop = True

        if patch.get("atmosphere_scale") is not None:
            scale = float(patch["atmosphere_scale"])
            if scale < 0:
                raise ValueError("atmosphere_scale must be >= 0")
            cfg = replace(cfg, environment=replace(cfg.environment, atmosphere_scale=scale))
            changed["atmosphere_scale"] = scale
            rebuild_prop = True

        if patch.get("eclipse") is not None:
            on = bool(patch["eclipse"])
            cfg = replace(cfg, environment=replace(cfg.environment, eclipse=on))
            self.eclipse = CylindricalEclipse() if on else NullEclipse()
            changed["eclipse"] = on

        if patch.get("compute_flops") is not None:
            flops = float(patch["compute_flops"])
            if flops <= 0:
                raise ValueError("compute_flops must be positive")
            cfg = replace(cfg, compute=replace(cfg.compute, flops=flops))
            if self.fleet is not None:
                self.fleet.flops[:] = flops
            changed["compute_flops"] = flops

        idle = cfg.compute.idle_w if patch.get("idle_w") is None else float(patch["idle_w"])
        busy = cfg.compute.busy_w if patch.get("busy_w") is None else float(patch["busy_w"])
        if patch.get("idle_w") is not None or patch.get("busy_w") is not None:
            if busy < idle:
                raise ValueError("busy_w must be >= idle_w")
            if idle < 0 or busy < 0:
                raise ValueError("idle_w / busy_w must be >= 0")
            cfg = replace(cfg, compute=replace(cfg.compute, idle_w=idle, busy_w=busy))
            if self.fleet is not None:
                self.fleet.idle_w = idle
                self.fleet.busy_w = busy
                self.fleet.idle_w_sat[:] = idle
                self.fleet.busy_w_sat[:] = busy
            if patch.get("idle_w") is not None:
                changed["idle_w"] = idle
            if patch.get("busy_w") is not None:
                changed["busy_w"] = busy

        self.cfg = cfg
        if rebuild_topo:
            self._rebuild_topology()
        if rebuild_prop:
            self._rebuild_propagator()
        self.fleet_overrides.update(changed)
        self._persist_overrides()
        return self.control_state()

    def apply_sat(self, sat_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        self._require()
        assert self.elements is not None and self.batteries is not None
        ids = self._sat_ids()
        if sat_id not in ids:
            raise KeyError(f"unknown sat {sat_id}")
        i = ids.index(sat_id)
        applied: dict[str, Any] = dict(self.sat_overrides.get(sat_id) or {})
        el = self.elements

        if patch.get("a_km") is not None:
            a_km = float(patch["a_km"])
            if a_km <= R_EARTH_M / 1000.0:
                raise ValueError("a_km must be greater than Earth radius (~6378 km)")
            el.a_m[i] = a_km * 1000.0
            applied["a_km"] = a_km
        if patch.get("e") is not None:
            e = float(patch["e"])
            if not (0.0 <= e < 1.0):
                raise ValueError("e must be in [0, 1)")
            el.e[i] = e
            applied["e"] = e
        if patch.get("i_deg") is not None:
            inc = float(patch["i_deg"])
            el.i_rad[i] = math.radians(inc)
            applied["i_deg"] = inc
        if patch.get("raan_deg") is not None:
            raan = float(patch["raan_deg"])
            el.raan_rad[i] = math.radians(raan)
            applied["raan_deg"] = raan
        if patch.get("soc") is not None:
            soc = float(patch["soc"])
            if not (0.0 <= soc <= 1.0):
                raise ValueError("soc must be in [0, 1]")
            self.batteries.soc[i] = soc
            applied["soc"] = soc
        if "power_draw_w" in patch and self.fleet is not None:
            raw = patch["power_draw_w"]
            if raw is None:
                self.fleet.power_draw_w[i] = np.nan
                applied.pop("power_draw_w", None)
            else:
                watts = float(raw)
                if watts < 0:
                    raise ValueError("power_draw_w must be >= 0")
                self.fleet.power_draw_w[i] = watts
                applied["power_draw_w"] = watts
        if patch.get("flops") is not None and self.fleet is not None:
            flops = float(patch["flops"])
            if flops <= 0:
                raise ValueError("flops must be positive")
            self.fleet.flops[i] = flops
            applied["flops"] = flops
        if patch.get("state") is not None:
            state = str(patch["state"])
            if state not in STATES:
                raise ValueError(f"state must be one of {list(STATES)}")
            self.state_lock[sat_id] = state
            if self.ops is not None:
                for rec in self.ops.records:
                    if rec.sat_id == sat_id:
                        rec.state = state
            applied["state"] = state

        if applied:
            self.sat_overrides[sat_id] = applied
        elif sat_id in self.sat_overrides:
            del self.sat_overrides[sat_id]
        self._persist_overrides()
        return self.control_state(sat_id=sat_id)

    def reset_sat(self, sat_id: str) -> dict[str, Any]:
        self._require()
        assert self.elements is not None and self.batteries is not None
        ids = self._sat_ids()
        if sat_id not in ids:
            raise KeyError(f"unknown sat {sat_id}")
        i = ids.index(sat_id)
        base = self._baseline_elements
        if base is not None and i < len(base):
            self.elements.a_m[i] = base.a_m[i]
            self.elements.e[i] = base.e[i]
            self.elements.i_rad[i] = base.i_rad[i]
            self.elements.raan_rad[i] = base.raan_rad[i]
        if self._baseline_soc is not None and i < len(self._baseline_soc):
            self.batteries.soc[i] = float(self._baseline_soc[i])
        if self._baseline_temp is not None and self.thermal is not None and i < len(self._baseline_temp):
            self.thermal.temp_k[i] = float(self._baseline_temp[i])
        if self.fleet is not None:
            if self._baseline_flops is not None and i < len(self._baseline_flops):
                self.fleet.flops[i] = float(self._baseline_flops[i])
            self.fleet.power_draw_w[i] = np.nan
        self.state_lock.pop(sat_id, None)
        self.sat_overrides.pop(sat_id, None)
        self._persist_overrides()
        return self.control_state(sat_id=sat_id)

    def reload(self) -> dict[str, Any]:
        if self.config_path is None:
            raise RuntimeError("no config loaded — POST /config/load first")
        return self.load(self.config_path, max_sats=self.max_sats)

    def export_kpi(self, path: str | Path | None = None) -> dict[str, Any]:
        self._require()
        assert self.cfg is not None
        kpi = self.kpi()
        out = Path(path) if path else Path(self.cfg.demo.kpi_json)
        md = Path(self.cfg.demo.kpi_md)
        write_kpi(out, md, kpi)
        return {"wrote": str(out), "kpi": kpi}

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
