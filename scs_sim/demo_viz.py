"""Phase 6 visualization + KPI demo.

Usage::

    python -m scs_sim.demo_viz
    python -m scs_sim.demo --viz
    python -m scs_sim.demo_viz --config configs/phase6_viz.yaml
"""

from __future__ import annotations

import argparse
import sys
from datetime import timedelta
from pathlib import Path

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
from scs_sim.environment.radiation import DoseAccumulator, make_radiation
from scs_sim.environment.thermal import ThermalState
from scs_sim.network.reachability import reachable_gateways
from scs_sim.network.routing import build_weighted_graph
from scs_sim.network.topology import TopologyBuilder
from scs_sim.orbit.frames import ecef_to_geodetic_n
from scs_sim.orbit.propagator import make_propagator
from scs_sim.viz.czml import build_czml, write_czml
from scs_sim.viz.html import write_viz_html
from scs_sim.viz.kpi import build_kpi, write_kpi
from scs_sim.viz.samples import GeodeticSeries, VizBundle
from scs_sim.viz.tracks import try_write_ground_tracks_png, write_ground_tracks_svg


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_viz_config() -> Path:
    here = Path("configs") / "phase6_viz.yaml"
    if here.is_file():
        return here
    bundled = _repo_root() / "configs" / "phase6_viz.yaml"
    if bundled.is_file():
        return bundled
    raise FileNotFoundError("could not find configs/phase6_viz.yaml; pass --config PATH")


def run_viz_demo(
    config_path: Path,
    *,
    max_sats: int | None = None,
    steps: int | None = None,
) -> Path:
    cfg: SimConfig = load_config(config_path)
    elements = generate_constellation(cfg, max_sats=max_sats)
    n_sats = len(elements)
    atm = make_atmosphere(cfg.environment.atmosphere)
    prop = make_propagator(
        cfg.propagator,
        atmosphere=atm,
        apply_drag=cfg.environment.apply_drag,
    )
    n_steps = int(cfg.demo.steps if steps is None else steps)
    clock = SimClock(epoch=cfg.epoch, dt_seconds=cfg.demo.dt_seconds)
    eclipse = CylindricalEclipse() if cfg.environment.eclipse else NullEclipse()
    rad = make_radiation(cfg.radiation.model, peak_flux_cm2_s=cfg.radiation.peak_flux_cm2_s)
    batteries = BatteryBank(n_sats, cfg.power)
    thermal = ThermalState(n_sats, cfg.thermal)
    dose = DoseAccumulator(n_sats)

    sat_ids = [str(s) for s in elements.sat_id]
    series = {sid: GeodeticSeries(sat_id=sid) for sid in sat_ids}
    builder = TopologyBuilder(cfg.isl, cfg.gsl, cfg.ground_stations)
    snapshots = []
    gs_ids = [g.id for g in cfg.ground_stations]
    last_reach = {sid: frozenset() for sid in sat_ids}

    fleet = None
    jobs: list[Job] = []
    summary = ComputeSummary()
    scheduler = GreedyEclipseScheduler(min_soc=cfg.compute.min_soc)
    if cfg.compute.enabled and cfg.compute.jobs:
        template = ComputeNode(
            sat_id="_",
            flops=cfg.compute.flops,
            memory_bytes=int(cfg.compute.memory_gib * 1024**3),
            idle_w=cfg.compute.idle_w,
            busy_w=cfg.compute.busy_w,
        )
        fleet = ComputeFleet(sat_ids, template)
        jobs = [
            Job(job_id=j.id, flops=j.flops, dest_gs=j.dest_gs, origin_gs=j.origin_gs)
            for j in cfg.compute.jobs
        ]

    soc_mean: list[float] = []
    soc_min: list[float] = []
    soc_max: list[float] = []
    epoch_iso = cfg.epoch.strftime("%Y-%m-%dT%H:%M:%SZ")

    for step in range(n_steps):
        elapsed = clock.elapsed_seconds
        r_eci = prop.positions_eci_m(elements, elapsed)
        r_ecef = prop.positions_ecef_m(elements, cfg.epoch, elapsed)
        lat, lon, alt = ecef_to_geodetic_n(r_ecef)
        t_iso = clock.now.strftime("%Y-%m-%dT%H:%M:%SZ")
        sun_frac = eclipse.sunlight_fraction(r_eci, clock.now)
        flux = rad.proton_flux_cm2_s(r_ecef, clock.now)
        dose.step(flux, cfg.demo.dt_seconds)

        for i, sid in enumerate(sat_ids):
            ser = series[sid]
            ser.elapsed_s.append(float(elapsed))
            ser.lon_deg.append(float(lon[i]))
            ser.lat_deg.append(float(lat[i]))
            ser.alt_m.append(float(alt[i]))

        snap = builder.snapshot(
            elements,
            r_eci,
            r_ecef,
            when=clock.now,
            step=step,
            route=True,
        )
        snapshots.append(snap)
        adj = build_weighted_graph(
            ((e.a, e.b, e.range_km) for e in snap.isl_edges),
            ((e.gs, e.sat, e.range_km) for e in snap.gsl_edges),
        )
        last_reach = reachable_gateways(sat_ids, gs_ids, adj)

        if fleet is not None:
            r_next = prop.positions_eci_m(elements, elapsed + cfg.demo.dt_seconds)
            sun_next = eclipse.sunlight_fraction(
                r_next, clock.now + timedelta(seconds=cfg.demo.dt_seconds)
            )
            assigns = scheduler.place(
                jobs,
                sat_ids,
                soc=batteries.soc,
                sunlight=sun_frac,
                sunlight_next=sun_next,
                reachable=last_reach,
                busy=fleet.busy,
                min_soc=cfg.compute.min_soc,
            )
            apply_assignments(jobs, fleet, assigns, step)
            tick_compute(
                jobs,
                fleet,
                soc=batteries.soc,
                dt_s=cfg.demo.dt_seconds,
                step=step,
                t_utc=t_iso,
                sunlight=sun_frac,
                summary=summary,
            )
            payload_w = fleet.load_w()
        else:
            payload_w = np.zeros(n_sats)

        load_w = cfg.power.platform_idle_w + payload_w
        batteries.step(sun_frac, load_w, cfg.demo.dt_seconds)
        thermal.step(sun_frac, load_w, cfg.demo.dt_seconds)
        soc_mean.append(float(batteries.soc.mean()))
        soc_min.append(float(batteries.soc.min()))
        soc_max.append(float(batteries.soc.max()))

        if step + 1 < n_steps:
            clock.advance()

    if jobs:
        finalize_summary(jobs, summary)

    end_iso = clock.now.strftime("%Y-%m-%dT%H:%M:%SZ")
    last_isl = list(snapshots[-1].isl_edges) if snapshots else []
    bundle = VizBundle(
        epoch_iso=epoch_iso,
        end_iso=end_iso,
        dt_seconds=float(cfg.demo.dt_seconds),
        sat_ids=sat_ids,
        series=series,
        stations=cfg.ground_stations,
        snapshots=snapshots,
        last_isl=last_isl,
        soc_mean_by_step=soc_mean,
        soc_min_by_step=soc_min,
        soc_max_by_step=soc_max,
        last_soc=batteries.soc.copy(),
        n_jobs_submitted=summary.submitted if jobs else 0,
        n_jobs_completed=summary.completed if jobs else 0,
        n_jobs_running=summary.running if jobs else 0,
        n_jobs_delayed=summary.delayed if jobs else 0,
        n_jobs_queued=summary.queued if jobs else 0,
        compute_energy_j=summary.energy_j if jobs else 0.0,
        config_name=cfg.name,
        config_path=str(config_path),
        n_sats=n_sats,
        n_steps=n_steps,
        propagator=getattr(prop, "name", cfg.propagator),
    )

    packets = build_czml(bundle, max_isl=cfg.demo.max_isl_czml)
    czml_path = write_czml(Path(cfg.demo.czml_output), packets)
    svg_path = write_ground_tracks_svg(
        Path(cfg.demo.tracks_svg),
        series,
        cfg.ground_stations,
        sat_ids,
        title=f"{cfg.name} ground tracks",
    )
    png_path = try_write_ground_tracks_png(
        Path(cfg.demo.tracks_png),
        series,
        cfg.ground_stations,
        sat_ids,
        title=f"{cfg.name} ground tracks",
    )
    kpi = build_kpi(bundle)
    kpi_json, kpi_md = write_kpi(Path(cfg.demo.kpi_json), Path(cfg.demo.kpi_md), kpi)
    svg_markup = svg_path.read_text(encoding="utf-8")
    html_path = write_viz_html(
        Path(cfg.demo.viz_html),
        title=f"SCS-Sim · {cfg.name}",
        czml_packets=packets,
        svg_markup=svg_markup,
        png_name=Path(cfg.demo.tracks_png).name if png_path is not None else None,
        czml_name=Path(cfg.demo.czml_output).name,
        kpi=kpi,
    )

    cov = kpi["coverage"]
    isl = kpi["isl"]
    st = kpi["stretch"]
    print("SCS-Sim Phase 6 visualization  (~78% of full product)")
    print(f"  config       : {config_path}")
    print(f"  name         : {cfg.name}")
    print(f"  demo N       : {n_sats}  steps={n_steps} x {cfg.demo.dt_seconds:.0f} s")
    print(f"  epoch        : {epoch_iso} → {end_iso}")
    print(
        f"  coverage     : {cov['gs_with_link']}/{cov['n_gs']} GS with ≥1 link "
        f"(mean {cov['mean_fraction_over_snapshots']:.2f})"
    )
    print(
        f"  ISL degree   : mean {isl['mean_degree']:.2f}  max {isl['max_degree']}  "
        f"edges {isl['n_edges_last']}"
    )
    print(
        f"  stretch      : mean {st['mean']:.2f}  p95 {st['p95']:.2f}  "
        f"connected {st['last_connected']}/{st['last_pairs']}"
    )
    if jobs:
        print(
            f"  compute      : {summary.completed}/{summary.submitted} completed "
            f"({100.0 * kpi['compute']['completion_rate']:.0f}%)"
        )
    print(f"  fleet SoC    : last mean {kpi['fleet_soc']['last_mean']:.3f}")
    print(f"  wrote        : {czml_path.resolve()}")
    print(f"  wrote        : {svg_path.resolve()}")
    if png_path is not None:
        print(f"  wrote        : {png_path.resolve()}  (matplotlib)")
    else:
        print("  PNG tracks   : skipped (pip install -e \".[viz]\" for matplotlib)")
    print(f"  wrote        : {html_path.resolve()}")
    print(f"  wrote        : {kpi_json.resolve()}")
    print(f"  wrote        : {kpi_md.resolve()}")
    print("  Cesium       : no API key used. Drop constellation.czml into Ion / Sandcastle.")
    print("  Phase 7      : Windows MSI / ops REST / Orekit — not built")
    return html_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SCS-Sim Phase 6 CZML + KPI demo")
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="YAML config (default: configs/phase6_viz.yaml)",
    )
    parser.add_argument("--max-sats", type=int, default=None, help="Override demo subsample")
    parser.add_argument("--steps", type=int, default=None, help="Override demo steps")
    args = parser.parse_args(argv)
    cfg_path = args.config if args.config is not None else default_viz_config()
    run_viz_demo(cfg_path, max_sats=args.max_sats, steps=args.steps)
    return 0


if __name__ == "__main__":
    sys.exit(main())
