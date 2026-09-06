"""Run the local ops API.

Usage::

    python -m scs_sim.api --config configs/phase6_viz.yaml --port 18765
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SCS-Sim local ops REST API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18765)
    parser.add_argument("--config", type=Path, default=None, help="Preload YAML")
    parser.add_argument("--max-sats", type=int, default=None)
    args = parser.parse_args(argv)

    try:
        import uvicorn
    except ImportError:
        print('uvicorn missing — pip install -e ".[api]"', file=sys.stderr)
        return 1

    from scs_sim.api.app import create_app
    from scs_sim.api.session import SimSession

    session = SimSession()
    if args.config is not None:
        session.load(args.config, max_sats=args.max_sats)
        print(f"[scs-sim] preloaded {args.config}  n={session.status().get('n_sats')}")

    app = create_app(session)
    print(f"[scs-sim] ops API  http://{args.host}:{args.port}/docs  (CORS open, no auth)")
    uvicorn.run(app, host=args.host, port=int(args.port), log_level="info")
    return 0


if __name__ == "__main__":
    sys.exit(main())
