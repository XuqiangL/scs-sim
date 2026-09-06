"""Phase 1–3 demo: Walker ephemeris + topology + eclipse columns.

Phase: 2 (network) / 3 (eclipse columns)
Completion: 90%

Usage::

    python -m scs_sim.demo
    python -m scs_sim.demo --config configs/phase2_network.yaml
    python -m scs_sim.demo --no-network
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

from scs_sim.clock import SimClock
from scs_sim.config import SimConfig, load_config
from scs_sim.constellation.walker import generate_constellation
from scs_sim.environment.atmosphere import make_atmosphere
from scs_sim.environment.eclipse import CylindricalEclipse, NullEclipse
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


def _write_ephemeris(path: Path, header: list[str], rows: list[list[object]]) -> None:
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
) -> Path:
    cfg: SimConfig = load_config(config_path)
    elements = generate_constellation(cfg, max_sats=max_sats)
    atm = make_atmosphere(cfg.environment.atmosphere)
    prop = make_propagator(
        cfg.propagator,
        atmosphere=atm,
        apply_drag=cfg.environment.apply_drag,
    )
    n_steps = int(cfg.demo.steps if steps is None else steps)
    clock = SimClock(epoch=cfg.epoch, dt_seconds=cfg.demo.dt_seconds)
    do_net = cfg.demo.network if network is None else network
    eclipse = CylindricalEclipse() if cfg.environment.eclipse else NullEclipse()
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
    snapshots = []
    topo_idx = _topology_step_indices(n_steps, cfg.demo.topology_steps) if do_net else set()
    builder = None
    if do_net:
        builder = TopologyBuilder(cfg.isl, cfg.gsl, cfg.ground_stations)

    for step in range(n_steps):
        elapsed = clock.elapsed_seconds
        r_eci = prop.positions_eci_m(elements, elapsed)
        r_ecef = prop.positions_ecef_m(elements, cfg.epoch, elapsed)
        r_km = np.linalg.norm(r_eci, axis=1) / 1000.0
        t_iso = clock.now.strftime("%Y-%m-%dT%H:%M:%SZ")
        if want_env_cols:
            labels = (
                eclipse.label(r_eci, clock.now)
                if hasattr(eclipse, "label")
                else ["sun"] * len(elements)
            )
            sun_frac = eclipse.sunlight_fraction(r_eci, clock.now)
            dens = atm.density_kg_m3(r_ecef, clock.now)
        else:
            labels = [""] * len(elements)
            sun_frac = np.ones(len(elements))
            dens = np.zeros(len(elements))

        for i in range(len(elements)):
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

        if builder is not None and step in topo_idx:
            snapshots.append(
                builder.snapshot(
                    elements,
                    r_eci,
                    r_ecef,
                    when=clock.now,
                    step=step,
                    route=True,
                )
            )
        if step + 1 < n_steps:
            clock.advance()

    _write_ephemeris(out_path, header, rows)

    topo_path = Path(cfg.demo.topology_output)
    edge_csv = topo_path.with_name(topo_path.stem.replace("topology", "topology_edges") + ".csv")
    if snapshots:
        write_topology_json(
            topo_path,
            snapshots,
            meta={
                "config": str(config_path),
                "n_sats": len(elements),
                "isl": {
                    "pattern": cfg.isl.pattern,
                    "max_range_km": cfg.isl.max_range_km,
                },
                "gsl": {
                    "min_elevation_deg": cfg.gsl.min_elevation_deg,
                    "n_stations": len(cfg.ground_stations),
                },
            },
        )
        write_topology_edges_csv(edge_csv, snapshots)

    primary = cfg.shells[0]
    a_primary = primary.altitude_km * 1000.0 + 6_378_137.0
    period_min = float(orbital_period_s(a_primary)) / 60.0
    mean_alt = float(np.mean(elements.a_m) / 1000.0 - 6378.137)
    last = snapshots[-1] if snapshots else None

    print("SCS-Sim Phase 1+2+3 demo  (~32% of full product)")
    print(f"  config       : {config_path}")
    print(f"  name         : {cfg.name}")
    print(f"  shells       : {len(cfg.shells)}")
    print(f"  configured N : {cfg.n_sats_configured}")
    print(f"  demo N       : {len(elements)}  (subsample={cfg.demo.subsample})")
    print(f"  altitude     : {mean_alt:.1f} km mean  (primary shell {primary.altitude_km:.0f} km)")
    print(f"  inclination  : {primary.inclination_deg:.1f} deg (primary)")
    print(f"  period est.  : {period_min:.2f} min  (Keplerian, primary a)")
    print(f"  propagator   : {getattr(prop, 'name', cfg.propagator)}")
    print(f"  epoch        : {cfg.epoch.strftime('%Y-%m-%dT%H:%M:%SZ')}")
    print(f"  steps        : {n_steps} x {cfg.demo.dt_seconds:.0f} s")
    print(f"  wrote        : {out_path.resolve()}  ({len(rows)} rows)")
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
    print("  Phase 4+     : compute scheduler / Cesium / ops — not built")
    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SCS-Sim Phase 1–3 Walker + network demo")
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="YAML constellation config (default: configs/walker_10k.yaml)",
    )
    parser.add_argument("--max-sats", type=int, default=None, help="Override demo subsample")
    parser.add_argument("--steps", type=int, default=None, help="Override demo steps")
    parser.add_argument("--output", type=Path, default=None, help="CSV output path")
    parser.add_argument(
        "--no-network",
        action="store_true",
        help="Skip ISL/GSL topology (Phase 1 ephemeris only)",
    )
    args = parser.parse_args(argv)

    cfg_path = args.config if args.config is not None else default_config_path()
    run_demo(
        cfg_path,
        max_sats=args.max_sats,
        steps=args.steps,
        output=args.output,
        network=False if args.no_network else None,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
