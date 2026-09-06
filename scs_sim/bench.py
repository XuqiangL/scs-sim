"""10k-scale timing hooks (Walker generate + Kepler-J2 + optional ISL subsample).

Usage::

    python -m scs_sim.bench
    python -m scs_sim.bench --n-sats 64 --steps 2 --isl-max-sats 32
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from scs_sim.config import ISLConfig, load_config
from scs_sim.constellation.walker import generate_constellation
from scs_sim.network.isl import PlusGridISL
from scs_sim.orbit.kepler import KeplerJ2Propagator


def peak_rss_mb() -> float | None:
    """Best-effort resident set. ``resource`` on Unix; optional ``psutil``."""
    try:
        import resource

        rss = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        # Linux: KiB; macOS: bytes
        if rss > 10_000_000:
            return rss / (1024.0 * 1024.0)
        return rss / 1024.0
    except (ImportError, OSError):
        pass
    try:
        import psutil  # type: ignore[import-untyped]

        return float(psutil.Process().memory_info().rss) / (1024.0 * 1024.0)
    except Exception:
        return None


def run_bench(
    *,
    config_path: Path,
    n_sats: int | None,
    steps: int,
    dt_seconds: float,
    isl_max_sats: int | None,
    output: Path,
) -> dict[str, Any]:
    cfg = load_config(config_path)
    t0 = time.perf_counter()
    elements = generate_constellation(cfg, max_sats=n_sats, subsample="stride")
    t_gen = time.perf_counter() - t0
    n = len(elements)

    prop = KeplerJ2Propagator()
    t1 = time.perf_counter()
    for k in range(int(steps)):
        prop.positions_eci_m(elements, float(k) * float(dt_seconds))
    t_prop = time.perf_counter() - t1
    prop_sats_s = (n * steps / t_prop) if t_prop > 0 else float("inf")

    isl_n = 0
    isl_edges = 0
    t_isl = 0.0
    if isl_max_sats is not None and isl_max_sats > 0:
        isl_n = min(int(isl_max_sats), n)
        idx = __import__("numpy").linspace(0, n - 1, isl_n, dtype=int)
        sub = elements.take(idx)
        r = prop.positions_eci_m(sub, 0.0)
        t2 = time.perf_counter()
        edges = PlusGridISL(cfg.isl if hasattr(cfg, "isl") else ISLConfig()).links_at(sub, r)
        t_isl = time.perf_counter() - t2
        isl_edges = len(edges)

    report: dict[str, Any] = {
        "config": str(config_path),
        "n_sats": n,
        "n_sats_configured": cfg.n_sats_configured,
        "steps": int(steps),
        "dt_seconds": float(dt_seconds),
        "generate_s": t_gen,
        "propagate_s": t_prop,
        "propagate_sats_per_s": prop_sats_s,
        "isl_n_sats": isl_n,
        "isl_edges": isl_edges,
        "isl_s": t_isl,
        "peak_rss_mb": peak_rss_mb(),
        "notes": [
            "Full +Grid fill at N=10008 is O(N²) and not the default ISL path.",
            "Use --isl-max-sats to time a subsample; omit it to skip ISL.",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    here = Path("configs") / "walker_10k.yaml"
    parser = argparse.ArgumentParser(description="SCS-Sim 10k timing bench")
    parser.add_argument("--config", type=Path, default=here if here.is_file() else None)
    parser.add_argument("--n-sats", type=int, default=None, help="Override demo subsample (None = YAML)")
    parser.add_argument("--full", action="store_true", help="Force N = configured T (10008 on walker_10k)")
    parser.add_argument("--steps", type=int, default=4)
    parser.add_argument("--dt", type=float, default=60.0)
    parser.add_argument(
        "--isl-max-sats",
        type=int,
        default=64,
        help="ISL subsample size (0 skips ISL). Full N is expensive.",
    )
    parser.add_argument("--output", type=Path, default=Path("out/bench.json"))
    args = parser.parse_args(argv)
    if args.config is None:
        raise SystemExit("pass --config configs/walker_10k.yaml")
    n = args.n_sats
    if args.full:
        n = load_config(args.config).n_sats_configured
    isl = None if args.isl_max_sats <= 0 else args.isl_max_sats
    report = run_bench(
        config_path=args.config,
        n_sats=n,
        steps=args.steps,
        dt_seconds=args.dt,
        isl_max_sats=isl,
        output=args.output,
    )
    print("SCS-Sim bench")
    print(f"  N            : {report['n_sats']}  (configured {report['n_sats_configured']})")
    print(f"  generate     : {report['generate_s']*1000:.1f} ms")
    print(f"  propagate    : {report['propagate_s']*1000:.1f} ms  ({report['propagate_sats_per_s']:.0f} sat-steps/s)")
    if report["isl_n_sats"]:
        print(f"  ISL          : {report['isl_n_sats']} sats  {report['isl_edges']} edges  {report['isl_s']*1000:.1f} ms")
    else:
        print("  ISL          : skipped")
    rss = report["peak_rss_mb"]
    print(f"  peak RSS     : {rss:.0f} MB" if rss is not None else "  peak RSS     : n/a")
    print(f"  wrote        : {Path(args.output).resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
