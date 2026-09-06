"""Phase 1–4 demo: orbits, topology, environment, compute schedule.

Phase: 4 (compute) + 3 (power/thermal/radiation)
Completion: 90%

Usage::

    python -m scs_sim.demo
    python -m scs_sim.demo --config configs/phase4_compute.yaml
    python -m scs_sim.demo --no-network --no-compute
"""

from __future__ import annotations

import argparse
import csv
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
from scs_sim.network.topology import TopologyBuilder, write_topology_edges_csv, write_topology_json
from scs_sim.orbit.kepler import orbital_period_s
from scs_sim.orbit.propagator import make_propagator


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_config_path() -> Path:
    here = Path("configs") / "walker_10k.yaml"
    if here.is_file():
        return here
    bundled = _repo_root() / "configs" / "walker_10k.yaml"
    if bundled.is_file():
        return bundled
    raise FileNotFoundError(
        "could not find configs/walker_10k.yaml; pass --config PATH"
    )


def _write_csv(path: Path, header: list[str], rows: list[list[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        writer.writerows(rows)


def _topology_step_indices(n_steps: int, n_topo: int | None) -> set[int]:
    if n_topo is None or n_topo >= n_steps:
        return set(range(n_steps))
    if n_topo <= 0:
        return set()
    idx = np.linspace(0, n_steps - 1, n_topo, dtype=int)
    return set(int(i) for i in idx)


def run_demo(
    config_path: Path,
    *,
    max_sats: int | None = None,
    steps: int | None = None,
    output: Path | None = None,
    network: bool | None = None,
    compute: bool | None = None,
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
    do_net = cfg.demo.network if network is None else network
    do_cmp = cfg.compute.enabled if compute is None else compute
    eclipse = CylindricalEclipse() if cfg.environment.eclipse else NullEclipse()
    rad = make_radiation(cfg.radiation.model, peak_flux_cm2_s=cfg.radiation.peak_flux_cm2_s)
    batteries = BatteryBank(n_sats, cfg.power)
    thermal = ThermalState(n_sats, cfg.thermal)
    dose = DoseAccumulator(n_sats)
    want_env_cols = bool(cfg.demo.eclipse_columns)

    out_path = Path(output) if output is not None else Path(cfg.demo.output)
    header = [
        "t_utc",
        "step",
        "sat_id",
        "shell_id",
        "plane",
        "slot",
        "x_eci_km",
        "y_eci_km",
        "z_eci_km",
        "x_ecef_km",
        "y_ecef_km",
        "z_ecef_km",
        "r_km",
    ]
    if want_env_cols:
        header.extend(["eclipse", "sunlight", "density_kg_m3"])

    rows: list[list[object]] = []
    env_rows: list[list[object]] = []
    snapshots = []
    topo_idx = _topology_step_indices(n_steps, cfg.demo.topology_steps) if do_net else set()
    builder = TopologyBuilder(cfg.isl, cfg.gsl, cfg.ground_stations) if do_net else None

    fleet = None
    jobs: list[Job] = []
    summary = ComputeSummary()
    scheduler = GreedyEclipseScheduler(min_soc=cfg.compute.min_soc)
    if do_cmp and cfg.compute.jobs:
        template = ComputeNode(
            sat_id="_",
            flops=cfg.compute.flops,
            memory_bytes=int(cfg.compute.memory_gib * 1024**3),
            idle_w=cfg.compute.idle_w,
            busy_w=cfg.compute.busy_w,
        )
        fleet = ComputeFleet([str(s) for s in elements.sat_id], template)
        jobs = [
            Job(job_id=j.id, flops=j.flops, dest_gs=j.dest_gs, origin_gs=j.origin_gs)
            for j in cfg.compute.jobs
        ]

    eclipse_flags_acc: list[float] = []
    soc_acc: list[float] = []
    temp_acc: list[float] = []

    gs_ids = [g.id for g in cfg.ground_stations]
    last_reach: dict[str, frozenset[str]] = {str(s): frozenset() for s in elements.sat_id}

    for step in range(n_steps):
        elapsed = clock.elapsed_seconds
        r_eci = prop.positions_eci_m(elements, elapsed)
        r_ecef = prop.positions_ecef_m(elements, cfg.epoch, elapsed)
        r_km = np.linalg.norm(r_eci, axis=1) / 1000.0
        t_iso = clock.now.strftime("%Y-%m-%dT%H:%M:%SZ")
        labels = eclipse.label(r_eci, clock.now)
        sun_frac = eclipse.sunlight_fraction(r_eci, clock.now)
        dens = atm.density_kg_m3(r_ecef, clock.now)
        flux = rad.proton_flux_cm2_s(r_ecef, clock.now)
        dose.step(flux, cfg.demo.dt_seconds)

        snap = None
        if builder is not None and (step in topo_idx or do_cmp):
            snap = builder.snapshot(
                elements,
                r_eci,
                r_ecef,
                when=clock.now,
                step=step,
                route=step in topo_idx,
            )
            if step in topo_idx:
                snapshots.append(snap)
            adj = build_weighted_graph(
                ((e.a, e.b, e.range_km) for e in snap.isl_edges),
                ((e.gs, e.sat, e.range_km) for e in snap.gsl_edges),
            )
            last_reach = reachable_gateways([str(s) for s in elements.sat_id], gs_ids, adj)

        if fleet is not None:
            r_next = prop.positions_eci_m(elements, elapsed + cfg.demo.dt_seconds)
            sun_next = eclipse.sunlight_fraction(
                r_next, clock.now + timedelta(seconds=cfg.demo.dt_seconds)
            )
            assigns = scheduler.place(
                jobs,
                [str(s) for s in elements.sat_id],
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

        in_ecl = np.array([lb != "sun" for lb in labels], dtype=float)
        eclipse_flags_acc.append(float(in_ecl.mean()))
        soc_acc.append(float(batteries.soc.mean()))
        temp_acc.append(float(thermal.temp_k.mean()))

        for i in range(n_sats):
            row: list[object] = [
                t_iso,
                step,
                elements.sat_id[i],
                elements.shell_id[i],
                int(elements.plane[i]),
                int(elements.slot[i]),
                f"{r_eci[i, 0] / 1000.0:.6f}",
                f"{r_eci[i, 1] / 1000.0:.6f}",
                f"{r_eci[i, 2] / 1000.0:.6f}",
                f"{r_ecef[i, 0] / 1000.0:.6f}",
                f"{r_ecef[i, 1] / 1000.0:.6f}",
                f"{r_ecef[i, 2] / 1000.0:.6f}",
                f"{r_km[i]:.6f}",
            ]
            if want_env_cols:
                row.extend([labels[i], f"{float(sun_frac[i]):.3f}", f"{float(dens[i]):.6e}"])
            rows.append(row)
            env_rows.append(
                [
                    t_iso,
                    step,
                    elements.sat_id[i],
                    labels[i],
                    f"{float(sun_frac[i]):.3f}",
                    f"{float(batteries.soc[i]):.4f}",
                    f"{float(thermal.temp_k[i]):.2f}",
                    f"{float(load_w[i]):.1f}",
                    f"{float(batteries.last_gen_w[i]):.1f}",
                    f"{float(flux[i]):.3f}",
                    f"{float(dose.dose_cm2[i]):.3f}",
                ]
            )

        if step + 1 < n_steps:
            clock.advance()

    _write_csv(out_path, header, rows)
    env_path = Path(cfg.demo.environment_output)
    _write_csv(
        env_path,
        [
            "t_utc",
            "step",
            "sat_id",
            "eclipse",
            "sunlight",
            "soc",
            "temp_k",
            "load_w",
            "gen_w",
            "flux_cm2_s",
            "dose_cm2",
        ],
        env_rows,
    )

    topo_path = Path(cfg.demo.topology_output)
    edge_csv = topo_path.with_name("topology_edges.csv")
    if snapshots:
        write_topology_json(
            topo_path,
            snapshots,
            meta={
                "config": str(config_path),
                "n_sats": n_sats,
                "isl": {"pattern": cfg.isl.pattern, "max_range_km": cfg.isl.max_range_km},
                "gsl": {
                    "min_elevation_deg": cfg.gsl.min_elevation_deg,
                    "n_stations": len(cfg.ground_stations),
                },
            },
        )
        write_topology_edges_csv(edge_csv, snapshots)

    cmp_path = Path(cfg.demo.compute_output)
    if jobs:
        finalize_summary(jobs, summary)
        _write_csv(
            cmp_path,
            [
                "t_utc",
                "step",
                "job_id",
                "sat_id",
                "status",
                "remaining_flops",
                "soc",
                "sunlight",
                "energy_j",
                "notes",
            ],
            [
                [
                    e.t_utc,
                    e.step,
                    e.job_id,
                    e.sat_id,
                    e.status,
                    f"{e.remaining_flops:.4e}",
                    f"{e.soc:.4f}",
                    f"{e.sunlight:.3f}",
                    f"{e.energy_j:.1f}",
                    e.notes,
                ]
                for e in summary.events
            ],
        )

    primary = cfg.shells[0]
    a_primary = primary.altitude_km * 1000.0 + 6_378_137.0
    period_min = float(orbital_period_s(a_primary)) / 60.0
    mean_alt = float(np.mean(elements.a_m) / 1000.0 - 6378.137)
    last = snapshots[-1] if snapshots else None
    mean_soc = float(np.mean(soc_acc)) if soc_acc else float("nan")
    pct_ecl = 100.0 * float(np.mean(eclipse_flags_acc)) if eclipse_flags_acc else 0.0
    mean_t = float(np.mean(temp_acc)) if temp_acc else float("nan")

    print("SCS-Sim Phase 1–4 demo  (~50% of full product)")
    print(f"  config       : {config_path}")
    print(f"  name         : {cfg.name}")
    print(f"  shells       : {len(cfg.shells)}")
    print(f"  configured N : {cfg.n_sats_configured}")
    print(f"  demo N       : {n_sats}  (subsample={cfg.demo.subsample})")
    print(f"  altitude     : {mean_alt:.1f} km mean  (primary shell {primary.altitude_km:.0f} km)")
    print(f"  inclination  : {primary.inclination_deg:.1f} deg (primary)")
    print(f"  period est.  : {period_min:.2f} min  (Keplerian, primary a)")
    print(f"  propagator   : {getattr(prop, 'name', cfg.propagator)}")
    print(f"  epoch        : {cfg.epoch.strftime('%Y-%m-%dT%H:%M:%SZ')}")
    print(f"  steps        : {n_steps} x {cfg.demo.dt_seconds:.0f} s")
    print(f"  wrote        : {out_path.resolve()}  ({len(rows)} rows)")
    print(
        f"  environment  : mean SoC {mean_soc:.3f}, eclipse {pct_ecl:.1f}%, "
        f"mean T {mean_t:.1f} K"
    )
    print(f"  wrote        : {env_path.resolve()}")
    if last is not None:
        print(f"  ISL pattern  : {cfg.isl.pattern}  max_range={cfg.isl.max_range_km:.0f} km")
        print(f"  ISL edges    : {len(last.isl_edges)} at last snapshot (step {last.step})")
        print(
            f"  GSL edges    : {len(last.gsl_edges)}  "
            f"({len(cfg.ground_stations)} GS, min elev {cfg.gsl.min_elevation_deg:.0f}°)"
        )
        if last.routing is not None:
            r = last.routing
            print(
                f"  GS routing   : {r.connected}/{r.pairs} pairs connected, "
                f"mean hops {r.mean_hops:.2f}, mean stretch {r.mean_stretch:.2f}"
            )
        print(f"  wrote        : {topo_path.resolve()}")
        print(f"  wrote        : {edge_csv.resolve()}")
    else:
        print("  network      : skipped")
    if jobs:
        print(
            f"  compute      : {summary.completed}/{summary.submitted} completed, "
            f"{summary.running} running, {summary.queued} queued, "
            f"{summary.delayed} delayed/unplaced, energy {summary.energy_j/1e6:.3f} MJ"
        )
        print(f"  wrote        : {cmp_path.resolve()}")
    else:
        print("  compute      : skipped")
    print("  Phase 5–6    : Cesium / ops packaging — not built")
    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SCS-Sim Phase 1–4 Walker + compute demo")
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="YAML constellation config (default: configs/walker_10k.yaml)",
    )
    parser.add_argument("--max-sats", type=int, default=None, help="Override demo subsample")
    parser.add_argument("--steps", type=int, default=None, help="Override demo steps")
    parser.add_argument("--output", type=Path, default=None, help="CSV output path")
    parser.add_argument("--no-network", action="store_true", help="Skip ISL/GSL topology")
    parser.add_argument("--no-compute", action="store_true", help="Skip job scheduler")
    args = parser.parse_args(argv)

    cfg_path = args.config if args.config is not None else default_config_path()
    run_demo(
        cfg_path,
        max_sats=args.max_sats,
        steps=args.steps,
        output=args.output,
        network=False if args.no_network else None,
        compute=False if args.no_compute else None,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
