"""Ops timeline JSON / CSV / cheap static HTML.

Phase: 5 (ops)
Completion: 90%
"""

from __future__ import annotations

import csv
import html
import json
from pathlib import Path
from typing import Any, Iterable

from scs_sim.ops.lifecycle import OpsEvent


def write_ops_json(path: Path, events: list[OpsEvent], meta: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "meta": meta,
        "events": [
            {
                "t_utc": e.t_utc,
                "step": e.step,
                "kind": e.kind,
                "sat_id": e.sat_id,
                "wave_id": e.wave_id,
                "detail": e.detail,
                **e.extra,
            }
            for e in events
        ],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_ops_csv(path: Path, events: Iterable[OpsEvent]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["t_utc", "step", "kind", "sat_id", "wave_id", "detail"])
        for e in events:
            w.writerow([e.t_utc, e.step, e.kind, e.sat_id, e.wave_id, e.detail])


def write_ops_html(path: Path, events: list[OpsEvent], title: str, summary: str) -> None:
    """Minimal static timeline — not Cesium."""
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for e in events:
        rows.append(
            "<tr>"
            f"<td>{html.escape(e.t_utc)}</td>"
            f"<td>{e.step}</td>"
            f"<td>{html.escape(e.kind)}</td>"
            f"<td>{html.escape(e.sat_id)}</td>"
            f"<td>{html.escape(e.wave_id)}</td>"
            f"<td>{html.escape(e.detail)}</td>"
            "</tr>"
        )
    body = "\n".join(rows) if rows else "<tr><td colspan='6'>No events</td></tr>"
    page = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/>
<title>{html.escape(title)}</title>
<style>
 body {{ font-family: Segoe UI, sans-serif; margin: 24px; background: #0f1419; color: #e7ecf1; }}
 h1 {{ font-size: 1.3rem; }}
 p {{ color: #9aa7b2; }}
 table {{ border-collapse: collapse; width: 100%; font-size: 0.85rem; }}
 th, td {{ border-bottom: 1px solid #243040; padding: 6px 8px; text-align: left; }}
 th {{ color: #7cb7ff; }}
 .wave_launch {{ color: #7dffa0; }}
 .retire {{ color: #ffb07d; }}
 .conjunction_warn {{ color: #ff6b6b; }}
</style></head><body>
<h1>{html.escape(title)}</h1>
<p>{html.escape(summary)}</p>
<table>
<thead><tr><th>UTC</th><th>Step</th><th>Kind</th><th>Sat</th><th>Wave</th><th>Detail</th></tr></thead>
<tbody>
{body}
</tbody></table>
</body></html>
"""
    path.write_text(page, encoding="utf-8")
