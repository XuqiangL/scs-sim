"""Windows-friendly launcher: ``scs-sim demo|viz|ops|api|twin``."""

from __future__ import annotations

import runpy
import sys

_USAGE = """SCS-Sim commands (Windows: scs-sim.cmd <cmd>):

  demo    Phase 1–4 Walker / compute   python -m scs_sim.demo
  viz     Phase 6 CZML / KPI           python -m scs_sim.demo_viz
  ops     Phase 5 insertion            python -m scs_sim.demo_ops
  api     Phase 7 local REST           python -m scs_sim.api
  twin    Phase 7 CSV compare          python -m scs_sim.twin
  catalog TLE align (opt-in fetch)     python -m scs_sim.catalog
  bench   10k timing hooks             python -m scs_sim.bench
"""

_MODULES = {
    "demo": "scs_sim.demo",
    "viz": "scs_sim.demo_viz",
    "ops": "scs_sim.demo_ops",
    "api": "scs_sim.api",
    "twin": "scs_sim.twin",
    "catalog": "scs_sim.catalog",
    "bench": "scs_sim.bench",
}


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"-h", "--help", "help"}:
        print(_USAGE)
        return 0
    cmd = args[0].lower()
    if cmd not in _MODULES:
        print(f"unknown command {cmd!r}\n{_USAGE}", file=sys.stderr)
        return 2
    sys.argv = [f"scs-sim {cmd}", *args[1:]]
    runpy.run_module(_MODULES[cmd], run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
