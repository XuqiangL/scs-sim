"""Convenience entry: same demo, network required.

Phase: 2 (network)
Completion: 100%
"""

from __future__ import annotations

import sys

from scs_sim.demo import main as demo_main


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    return demo_main(args)


if __name__ == "__main__":
    raise SystemExit(main())
