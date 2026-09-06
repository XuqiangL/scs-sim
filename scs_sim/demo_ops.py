"""Phase 5 ops demo: launch waves, lifecycle, replenish/retire, timeline.

Phase: 5 (ops)
Completion: 90%

Usage::

    python -m scs_sim.demo_ops
    python -m scs_sim.demo --ops
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from scs_sim.clock import SimClock
from scs_sim.config import load_config
from scs_sim.demo import default_config_path
from scs_sim.network.isl import PlusGridISL
from scs_sim.ops.actions import conjunction_warnings
from scs_sim.ops.deployment import OpsFleet
from scs_sim.ops.lifecycle import OpsEvent
from scs_sim.ops.timeline import write_ops_csv, write_ops_html, write_ops_json
from scs_sim.ops.tle import parse_tle_file, tle_to_elements
from scs_sim.orbit.kepler import orbital_period_s
from scs_sim.orbit.propagator import make_propagator


def run_ops_demo(
    config_path: Path,
    *,
    steps: int | None = None,
) -> Path:
    cfg = load_config(config_path)
    if not cfg.deployment.waves:
        raise SystemExit(
            "Phase 5 demo needs deployment.waves[] — use configs/phase5_ops.yaml"
        )
    fleet = OpsFleet.from_waves(cfg.deployment.waves, cfg.epoch, cfg.deployment)
    events: list[OpsEvent] = []

    tle_path = cfg.deployment.tle_path
    if tle_path:
        p = Path(tle_path)
        if not p.is_file():
            p = Path(config_path).resolve().parent.parent / tle_path
        if p.is_file():
            recs = parse_tle_file(p)
            batch = tle_to_elements(recs, cfg.epoch)
            events.extend(fleet.attach_catalog(batch, now=cfg.epoch))
            print(f"  TLE ingest   : {len(recs)} records from {p}")
        else:
            print(f"  TLE ingest   : path {tle_path!r} not found — Walker only")

    n_steps = int(cfg.demo.steps if steps is None else steps)
    clock = SimClock(epoch=cfg.epoch, dt_seconds=cfg.demo.dt_seconds)
    prop = make_propagator(cfg.propagator)
    isl = PlusGridISL(cfg.isl)
    replenish_at = {a.step: a for a in cfg.deployment.replenish}
    retire_at = {a.step: a for a in cfg.deployment.retire}
    last_isl = 0
    last_conj = 0

    for step in range(n_steps):
        events.extend(fleet.tick(clock.now, step))
        if step in replenish_at:
            events.extend(fleet.replenish(replenish_at[step], clock.now, step))
            events.extend(fleet.tick(clock.now, step))
        if step in retire_at:
            act = retire_at[step]
            events.extend(fleet.request_retire(act.n_sats, clock.now, step, act.wave_id))
        fleet.apply_station_keeping()

        topo = fleet.topology_elements()
        if topo is not None and len(topo) >= 2:
            r = prop.positions_eci_m(topo, clock.elapsed_seconds)
            edges = isl.links_at(topo, r)
            last_isl = len(edges)
            if cfg.deployment.conjunction:
                warns = conjunction_warnings(
                    topo,
                    r,
                    threshold_km=cfg.deployment.conjunction_threshold_km,
                    sample=cfg.deployment.conjunction_sample,
                    now_iso=clock.now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    step=step,
                )
                last_conj += len(warns)
                events.extend(warns)
        else:
            last_isl = 0

        if step + 1 < n_steps:
            clock.advance()

    counts = fleet.counts()
    json_path = Path(cfg.demo.ops_timeline)
    csv_path = Path(cfg.demo.ops_events)
    html_path = Path(cfg.demo.ops_html)
    meta = {
        "config": str(config_path),
        "n_sats": len(fleet.records),
        "states": counts,
        "waves": [w.wave_id for w in cfg.deployment.waves],
        "tle": cfg.deployment.tle_path,
    }
    write_ops_json(json_path, events, meta)
    write_ops_csv(csv_path, events)
    write_ops_html(
        html_path,
        events,
        title=f"SCS-Sim ops timeline — {cfg.name}",
        summary=(
            f"{len(fleet.records)} sats, {len(cfg.deployment.waves)} waves, "
            f"{counts.get('operational', 0)} operational, "
            f"{counts.get('retired', 0)} retired, {last_conj} conjunction warnings"
        ),
    )

    primary_alt = cfg.deployment.waves[0].operational_altitude_km
    period_min = float(orbital_period_s(primary_alt * 1000.0 + 6_378_137.0)) / 60.0
    print("SCS-Sim Phase 5 ops demo  (~62% of full product)")
    print(f"  config       : {config_path}")
    print(f"  name         : {cfg.name}")
    print(f"  waves        : {len(cfg.deployment.waves)} → {len(fleet.records)} sats")
    print(f"  steps        : {n_steps} x {cfg.demo.dt_seconds:.0f} s")
    print(f"  states       : {counts}")
    print(f"  ISL (ops)    : {last_isl} edges on operational sats only")
    print(f"  conjunctions : {last_conj} warnings")
    print(f"  period est.  : {period_min:.2f} min at {primary_alt:.0f} km")
    print(f"  wrote        : {json_path.resolve()}")
    print(f"  wrote        : {csv_path.resolve()}")
    print(f"  wrote        : {html_path.resolve()}")
    print("  TLE hook     : set deployment.tle_path to a CelesTrak TLE file")
    print("  Phase 6      : Cesium / MSI / Orekit — not built")
    return json_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SCS-Sim Phase 5 deployment / ops demo")
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="YAML (default: configs/phase5_ops.yaml)",
    )
    parser.add_argument("--steps", type=int, default=None)
    args = parser.parse_args(argv)
    cfg_path = args.config
    if cfg_path is None:
        here = Path("configs") / "phase5_ops.yaml"
        cfg_path = here if here.is_file() else default_config_path()
    run_ops_demo(cfg_path, steps=args.steps)
    return 0


if __name__ == "__main__":
    sys.exit(main())
