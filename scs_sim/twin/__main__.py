"""CLI: compare telemetry CSV to a sim-state CSV.

Usage::

    python -m scs_sim.twin --telemetry tests/fixtures/telemetry_sample.csv \\
        --sim tests/fixtures/sim_state_sample.csv --output out/twin_compare.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from scs_sim.twin.compare import compare_tables, write_twin_compare
from scs_sim.twin.io import load_telemetry_csv


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="SCS-Sim digital-twin CSV compare")
    p.add_argument("--telemetry", type=Path, required=True)
    p.add_argument("--sim", type=Path, required=True, help="Sim-state CSV, same schema")
    p.add_argument("--output", type=Path, default=Path("out/twin_compare.json"))
    args = p.parse_args(argv)
    tel = load_telemetry_csv(args.telemetry)
    sim = load_telemetry_csv(args.sim)
    report = compare_tables(sim, tel)
    report["mode"] = "tables"
    report["telemetry"] = str(args.telemetry)
    report["sim"] = str(args.sim)
    out = write_twin_compare(args.output, report)
    print(f"matched {report['n_matched']}  RMSE pos {report['rmse_position_km']:.4f} km  SoC {report['rmse_soc']:.4f}")
    print(f"wrote {out.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
