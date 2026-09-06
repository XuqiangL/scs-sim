"""KPI dashboard JSON + short Markdown report."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from scs_sim.network.routing import PathResult
from scs_sim.viz.samples import VizBundle

# Stretch histogram edges (path / geodesic). LEOCraft-style bins.
STRETCH_BINS = [1.0, 1.25, 1.5, 2.0, 3.0, 5.0, 10.0, 50.0]


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return float("nan")
    return float(np.percentile(np.asarray(values, dtype=float), q))


def _histogram(values: list[float], bins: list[float]) -> dict[str, Any]:
    if not values:
        return {"bins": bins, "counts": [0] * (len(bins) - 1), "n": 0}
    counts, edges = np.histogram(np.asarray(values, dtype=float), bins=np.asarray(bins, dtype=float))
    return {
        "bins": [float(x) for x in edges],
        "counts": [int(c) for c in counts],
        "n": int(len(values)),
    }


def _coverage(bundle: VizBundle) -> dict[str, Any]:
    n_gs = len(bundle.stations)
    gs_ids = [g.id for g in bundle.stations]
    last_links = {g: 0 for g in gs_ids}
    frac_acc: list[float] = []
    for snap in bundle.snapshots:
        have = {e.gs for e in snap.gsl_edges}
        if n_gs:
            frac_acc.append(len(have) / n_gs)
        if snap is bundle.snapshots[-1]:
            for e in snap.gsl_edges:
                last_links[e.gs] = last_links.get(e.gs, 0) + 1
    gs_with = sum(1 for v in last_links.values() if v >= 1)
    return {
        "n_gs": n_gs,
        "gs_with_link": gs_with,
        "fraction": (gs_with / n_gs) if n_gs else float("nan"),
        "mean_fraction_over_snapshots": float(np.mean(frac_acc)) if frac_acc else float("nan"),
        "links_by_gs": last_links,
        "definition": "GS with ≥1 GSL in the last topology snapshot (coverage proxy)",
    }


def _isl_degree(bundle: VizBundle) -> dict[str, Any]:
    last = bundle.snapshots[-1] if bundle.snapshots else None
    deg: Counter[str] = Counter()
    n_edges = 0
    if last is not None:
        n_edges = len(last.isl_edges)
        for e in last.isl_edges:
            deg[e.a] += 1
            deg[e.b] += 1
    values = [int(deg[s]) for s in bundle.sat_ids] if bundle.sat_ids else []
    return {
        "n_edges_last": n_edges,
        "mean_degree": float(np.mean(values)) if values else float("nan"),
        "max_degree": int(max(values)) if values else 0,
        "min_degree": int(min(values)) if values else 0,
        "n_sats": len(bundle.sat_ids),
    }


def _stretch_values(bundle: VizBundle) -> list[float]:
    out: list[float] = []
    for snap in bundle.snapshots:
        if snap.routing is None:
            continue
        for p in snap.routing.paths:
            if math_isfinite(p.stretch):
                out.append(float(p.stretch))
    return out


def math_isfinite(x: float) -> bool:
    return bool(np.isfinite(x))


def _stretch_summary(bundle: VizBundle) -> dict[str, Any]:
    values = _stretch_values(bundle)
    last_paths: list[PathResult] = []
    last_pairs = last_connected = 0
    if bundle.snapshots and bundle.snapshots[-1].routing is not None:
        r = bundle.snapshots[-1].routing
        last_pairs = r.pairs
        last_connected = r.connected
        last_paths = list(r.paths)
    last_vals = [float(p.stretch) for p in last_paths if math_isfinite(p.stretch)]
    return {
        "n_pair_samples": len(values),
        "last_pairs": last_pairs,
        "last_connected": last_connected,
        "mean": float(np.mean(values)) if values else float("nan"),
        "median": float(np.median(values)) if values else float("nan"),
        "p95": _percentile(values, 95),
        "max": float(np.max(values)) if values else float("nan"),
        "last_mean": float(np.mean(last_vals)) if last_vals else float("nan"),
        "histogram": _histogram(values, STRETCH_BINS),
        "definition": "GS↔GS path length / great-circle geodesic (all routed snapshots)",
        "future_baseline": "LEOCraft stretch — optional tests/baselines/leocraft_stretch.json",
    }


def _compute(bundle: VizBundle) -> dict[str, Any]:
    submitted = int(bundle.n_jobs_submitted)
    completed = int(bundle.n_jobs_completed)
    rate = (completed / submitted) if submitted else float("nan")
    return {
        "submitted": submitted,
        "completed": completed,
        "running": int(bundle.n_jobs_running),
        "delayed": int(bundle.n_jobs_delayed),
        "queued": int(bundle.n_jobs_queued),
        "completion_rate": rate,
        "energy_j": float(bundle.compute_energy_j),
    }


def _soc(bundle: VizBundle) -> dict[str, Any]:
    last = bundle.last_soc
    return {
        "mean_over_window": float(np.mean(bundle.soc_mean_by_step)) if bundle.soc_mean_by_step else float("nan"),
        "min_over_window": float(np.min(bundle.soc_min_by_step)) if bundle.soc_min_by_step else float("nan"),
        "max_over_window": float(np.max(bundle.soc_max_by_step)) if bundle.soc_max_by_step else float("nan"),
        "last_mean": float(np.mean(last)) if last.size else float("nan"),
        "last_min": float(np.min(last)) if last.size else float("nan"),
        "last_max": float(np.max(last)) if last.size else float("nan"),
        "n_sats": int(last.size),
    }


def build_kpi(bundle: VizBundle) -> dict[str, Any]:
    return {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "config": bundle.config_name,
        "config_path": bundle.config_path,
        "epoch": bundle.epoch_iso,
        "end": bundle.end_iso,
        "n_sats": bundle.n_sats or len(bundle.sat_ids),
        "n_steps": bundle.n_steps,
        "dt_seconds": bundle.dt_seconds,
        "propagator": bundle.propagator,
        "coverage": _coverage(bundle),
        "isl": _isl_degree(bundle),
        "stretch": _stretch_summary(bundle),
        "compute": _compute(bundle),
        "fleet_soc": _soc(bundle),
        "notes": [
            "Coverage is a GS-with-link proxy, not area population coverage.",
            "Stretch uses Dijkstra over ISL+GSL; geodesic is haversine.",
            "Hypatia RTT / LEOCraft stretch baselines are optional (see docs/VALIDATION.md).",
        ],
    }


def _fmt(x: float, digits: int = 3) -> str:
    if x is None or not np.isfinite(x):
        return "n/a"
    return f"{x:.{digits}f}"


def kpi_markdown(kpi: dict[str, Any]) -> str:
    cov = kpi["coverage"]
    isl = kpi["isl"]
    st = kpi["stretch"]
    cmp_ = kpi["compute"]
    soc = kpi["fleet_soc"]
    hist = st["histogram"]
    hist_lines = []
    bins = hist["bins"]
    counts = hist["counts"]
    for i, c in enumerate(counts):
        hist_lines.append(f"| {bins[i]:.2f}–{bins[i+1]:.2f} | {c} |")
    hist_table = "\n".join(hist_lines) if hist_lines else "| (empty) | 0 |"
    rate = cmp_["completion_rate"]
    rate_s = "n/a" if not np.isfinite(rate) else f"{100.0 * rate:.1f}%"
    return f"""# SCS-Sim KPI report

Generated **{kpi['generated_utc']}** from `{kpi['config_path']}` (`{kpi['config']}`).

Window `{kpi['epoch']}` → `{kpi['end']}` · **{kpi['n_sats']}** sats · **{kpi['n_steps']}** × {kpi['dt_seconds']:.0f} s · propagator `{kpi['propagator']}`.

## Coverage proxy

| | |
|---|---|
| Ground stations | {cov['n_gs']} |
| GS with ≥1 link (last snap) | {cov['gs_with_link']} |
| Fraction | {_fmt(cov['fraction'])} |
| Mean fraction over snapshots | {_fmt(cov['mean_fraction_over_snapshots'])} |

Links by GS (last snapshot): `{cov['links_by_gs']}`.

## ISL degree (last snapshot)

| | |
|---|---|
| Edges | {isl['n_edges_last']} |
| Mean degree | {_fmt(isl['mean_degree'])} |
| Max degree | {isl['max_degree']} |
| Min degree | {isl['min_degree']} |

## GS↔GS stretch

Path / geodesic over routed snapshots. Future comparison: LEOCraft stretch (optional baseline file).

| | |
|---|---|
| Pair samples | {st['n_pair_samples']} |
| Last connected / pairs | {st['last_connected']} / {st['last_pairs']} |
| Mean | {_fmt(st['mean'])} |
| Median | {_fmt(st['median'])} |
| P95 | {_fmt(st['p95'])} |
| Max | {_fmt(st['max'])} |

| Stretch bin | Count |
|---|---:|
{hist_table}

## Compute jobs

| | |
|---|---|
| Submitted | {cmp_['submitted']} |
| Completed | {cmp_['completed']} |
| Completion rate | {rate_s} |
| Running / queued / delayed | {cmp_['running']} / {cmp_['queued']} / {cmp_['delayed']} |
| Energy | {_fmt(cmp_['energy_j'] / 1e6, 3)} MJ |

## Fleet SoC

| | |
|---|---|
| Mean over window | {_fmt(soc['mean_over_window'])} |
| Min / max over window | {_fmt(soc['min_over_window'])} / {_fmt(soc['max_over_window'])} |
| Last-step mean | {_fmt(soc['last_mean'])} |
| Last-step min / max | {_fmt(soc['last_min'])} / {_fmt(soc['last_max'])} |

## Notes

- No Cesium or Ion key is required to produce this report.
- Hypatia RTT is a planned comparison (`2 · path_km / c`); see `docs/VALIDATION.md`.
"""


def write_kpi(json_path: Path, md_path: Path, kpi: dict[str, Any]) -> tuple[Path, Path]:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(kpi, indent=2), encoding="utf-8")
    md_path.write_text(kpi_markdown(kpi), encoding="utf-8")
    return json_path, md_path
