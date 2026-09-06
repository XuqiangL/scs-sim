"""Phase 1 demo: generate a Walker shell, propagate, write CSV.

Phase: 1 (core)
Completion: 95%

Usage::

    python -m scs_sim.demo
    python -m scs_sim.demo --config configs/walker_10k.yaml --max-sats 100
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

from scs_sim.clock import SimClock
from scs_sim.config import load_config
from scs_sim.constellation.walker import generate_constellation
from scs_sim.orbit.kepler import orbital_period_s
from scs_sim.orbit.propagator import make_propagator

# Placeholder ports are imported so the hexagonal surface is exercised, not run.
from scs_sim.compute.scheduler import NullScheduler  # noqa: F401
from scs_sim.environment.atmosphere import NullAtmosphere  # noqa: F401
from scs_sim.network.isl import NullISL  # noqa: F401


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


def _write_ephemeris(
    path: Path,
    rows: list[list[object]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        writer.writerows(rows)


def run_demo(
    config_path: Path,
    *,
    max_sats: int | None = None,
    steps: int | None = None,
    output: Path | None = None,
) -> Path:
    cfg = load_config(config_path)
    elements = generate_constellation(cfg, max_sats=max_sats)
    prop = make_propagator(cfg.propagator)
    n_steps = int(cfg.demo.steps if steps is None else steps)
    clock = SimClock(epoch=cfg.epoch, dt_seconds=cfg.demo.dt_seconds)

    out_path = Path(output) if output is not None else Path(cfg.demo.output)
    rows: list[list[object]] = []

    for step in range(n_steps):
        elapsed = clock.elapsed_seconds
        r_eci = prop.positions_eci_m(elements, elapsed)
        r_ecef = prop.positions_ecef_m(elements, cfg.epoch, elapsed)
        r_km = np.linalg.norm(r_eci, axis=1) / 1000.0
        t_iso = clock.now.strftime("%Y-%m-%dT%H:%M:%SZ")
        for i in range(len(elements)):
            rows.append(
                [
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
            )
        if step + 1 < n_steps:
            clock.advance()

    _write_ephemeris(out_path, rows)

    primary = cfg.shells[0]
    a_primary = primary.altitude_km * 1000.0 + 6_378_137.0
    period_min = float(orbital_period_s(a_primary)) / 60.0
    mean_alt = float(np.mean(elements.a_m) / 1000.0 - 6378.137)

    print("SCS-Sim Phase 1 demo  (~10% of full product)")
    print(f"  config       : {config_path}")
    print(f"  name         : {cfg.name}")
    print(f"  shells       : {len(cfg.shells)}")
    print(f"  configured N : {cfg.n_sats_configured}")
    print(f"  demo N       : {len(elements)}  (demo_max_sats / subsample)")
    print(f"  altitude     : {mean_alt:.1f} km mean  (primary shell {primary.altitude_km:.0f} km)")
    print(f"  inclination  : {primary.inclination_deg:.1f} deg (primary)")
    print(f"  period est.  : {period_min:.2f} min  (Keplerian, primary a)")
    print(f"  propagator   : {prop.name}")
    print(f"  epoch        : {cfg.epoch.strftime('%Y-%m-%dT%H:%M:%SZ')}")
    print(f"  steps        : {n_steps} x {cfg.demo.dt_seconds:.0f} s")
    print(f"  wrote        : {out_path.resolve()}  ({len(rows)} rows)")
    print("  Phase 2+     : ISL/GSL, drag/eclipse, compute scheduler — interfaces only")
    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SCS-Sim Phase 1 Walker demo")
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="YAML constellation config (default: configs/walker_10k.yaml)",
    )
    parser.add_argument("--max-sats", type=int, default=None, help="Override demo subsample")
    parser.add_argument("--steps", type=int, default=None, help="Override demo steps")
    parser.add_argument("--output", type=Path, default=None, help="CSV output path")
    args = parser.parse_args(argv)

    cfg_path = args.config if args.config is not None else default_config_path()
    run_demo(cfg_path, max_sats=args.max_sats, steps=args.steps, output=args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
