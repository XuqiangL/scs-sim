"""EXE entry: local API + embedded WebView2 window (no external browser).

Phase: vNext desktop
Completion: 95%
"""

from __future__ import annotations

import argparse
import socket
import sys
import threading
import time
from pathlib import Path


def _bundled_root() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[2]


def _wait_port(host: str, port: int, timeout_s: float = 20.0) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.4):
                return True
        except OSError:
            time.sleep(0.15)
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SCS-Sim Windows desktop launcher")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18765)
    parser.add_argument("--config", default=None)
    parser.add_argument(
        "--browser",
        action="store_true",
        help="Open system browser instead of embedded WebView2 (debug only)",
    )
    parser.add_argument("--no-window", action="store_true", help="API only, no UI window")
    args = parser.parse_args(argv)

    root = _bundled_root()
    cfg = Path(args.config) if args.config else (root / "configs" / "phase6_viz.yaml")
    if not cfg.is_file():
        alt = Path.cwd() / "configs" / "phase6_viz.yaml"
        if alt.is_file():
            cfg = alt

    try:
        import uvicorn
    except ImportError:
        print("uvicorn missing", file=sys.stderr)
        return 1

    from scs_sim.api.app import create_app
    from scs_sim.api.session import SimSession

    session = SimSession()
    if cfg.is_file():
        session.load(cfg)
        print(f"[scs-sim] preloaded {cfg}")
    app = create_app(session)
    url = f"http://{args.host}:{args.port}/ui"

    def _run() -> None:
        uvicorn.run(app, host=args.host, port=int(args.port), log_level="info")

    threading.Thread(target=_run, daemon=True).start()
    if not _wait_port(args.host, int(args.port)):
        print("[scs-sim] API failed to bind", file=sys.stderr)
        return 2
    print(f"[scs-sim] API ready {url}")

    if args.no_window:
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            return 0

    if args.browser:
        import webbrowser

        webbrowser.open(url)
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            return 0

    try:
        import webview
    except ImportError:
        print(
            "[scs-sim] pywebview missing — install with: py -3 -m pip install pywebview\n"
            "Falling back is disabled; refuse to open external browser by default.",
            file=sys.stderr,
        )
        return 3

    webview.create_window(
        "SCS-Sim · 星座控制台",
        url,
        width=1680,
        height=960,
        min_size=(1100, 700),
        background_color="#0b0e12",
    )
    # Edge WebView2 — GPU-accelerated Chromium embed, no system browser tab
    webview.start(gui="edgechromium")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
