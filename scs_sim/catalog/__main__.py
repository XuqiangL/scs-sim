"""TLE alignment CLI.

Usage::

    python -m scs_sim.catalog --tle tests/fixtures/starlink_sample.tle
    python -m scs_sim.catalog --fetch-tle --tle out/starlink.tle
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from scs_sim.catalog.align import align_tle_to_walker, write_align_report
from scs_sim.catalog.celestrak import CELESTRAK_STARLINK_TLE, load_tles, resolve_tle_path
from scs_sim.config import load_config


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="SCS-Sim TLE / CelesTrak alignment (fetch is opt-in)")
    p.add_argument("--tle", type=Path, default=None, help="Local TLE path (fixture or cache)")
    p.add_argument("--config", type=Path, default=None, help="Walker YAML (default walker_10k)")
    p.add_argument(
        "--fetch-tle",
        action="store_true",
        help="Download CelesTrak Starlink GROUP TLE (network; not used in CI)",
    )
    p.add_argument("--url", default=CELESTRAK_STARLINK_TLE)
    p.add_argument("--output", type=Path, default=Path("out/tle_align_report.json"))
    args = p.parse_args(argv)

    cfg_path = args.config
    if cfg_path is None:
        here = Path("configs") / "walker_10k.yaml"
        cfg_path = here if here.is_file() else _repo_root() / "configs" / "walker_10k.yaml"
    cfg = load_config(cfg_path)

    default_tle = Path("tests") / "fixtures" / "starlink_sample.tle"
    tle_arg = args.tle
    if tle_arg is None and not args.fetch_tle:
        if default_tle.is_file():
            tle_arg = default_tle
        elif cfg.catalog.tle_path:
            tle_arg = Path(cfg.catalog.tle_path)
        elif cfg.deployment.tle_path:
            tle_arg = Path(cfg.deployment.tle_path)

    fetch = bool(args.fetch_tle or cfg.catalog.fetch)
    tle_path = resolve_tle_path(
        tle_arg,
        fetch=fetch,
        cache_path=cfg.catalog.cache_path,
        url=args.url or cfg.catalog.url,
    )
    recs = load_tles(tle_path)
    report = align_tle_to_walker(recs, cfg, source=str(tle_path), fetched=fetch)
    out = write_align_report(args.output, report)
    print("SCS-Sim TLE alignment")
    print(f"  source       : {tle_path}  fetched={fetch}")
    print(f"  n_tle        : {report['n_tle']}")
    print(f"  walker shell : {report['walker_shell_id']}  T={report['n_walker_shell']}")
    print(
        f"  alt          : TLE mean {report['tle_mean_alt_km']:.1f} km  "
        f"Walker {report['walker_alt_km']:.1f} km  "
        f"in-band {report['n_tle_in_walker_band']}/{report['n_tle']}"
    )
    print(
        f"  inc          : TLE {report['tle_mean_inc_deg']:.2f}°  "
        f"Walker {report['walker_inc_deg']:.2f}°"
    )
    print(f"  SGP4 step    : ok  mean r {report['sgp4_mean_radius_km']:.1f} km")
    print(f"  wrote        : {out.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
