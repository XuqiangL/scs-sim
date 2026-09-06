"""Cesium-ready CZML (JSON) export. No Ion / API key required to generate.

CZML 1.0 document + per-sat cartographicDegrees sampled from the propagator,
plus optional last-snapshot ISL polylines and ground-station points.

Drop ``out/constellation.czml`` into Cesium ion (Add data → CZML) or a local
CesiumJS Sandcastle. See docs/VIZ.md.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scs_sim.config import GroundStationConfig
from scs_sim.network.isl import ISLEdge
from scs_sim.viz.samples import GeodeticSeries, VizBundle

# Distinct, color-blind-friendlier palette (sRGB 0–255).
_SAT_RGBA = (90, 180, 255, 255)
_PATH_RGBA = (70, 150, 230, 90)
_GS_RGBA = (255, 176, 64, 255)
_ISL_RGBA = (120, 230, 170, 110)
_GSL_RGBA = (255, 200, 90, 90)


def _iso_interval(start: str, end: str) -> str:
    return f"{start}/{end}"


def document_packet(
    name: str,
    start_iso: str,
    end_iso: str,
    *,
    multiplier: float = 60.0,
) -> dict[str, Any]:
    return {
        "id": "document",
        "name": name,
        "version": "1.0",
        "clock": {
            "interval": _iso_interval(start_iso, end_iso),
            "currentTime": start_iso,
            "multiplier": float(multiplier),
            "range": "LOOP_STOP",
            "step": "SYSTEM_CLOCK_MULTIPLIER",
        },
    }


def sat_packet(
    series: GeodeticSeries,
    start_iso: str,
    end_iso: str,
    *,
    epoch_iso: str,
) -> dict[str, Any]:
    carto: list[float] = []
    for t, lon, lat, alt in zip(
        series.elapsed_s, series.lon_deg, series.lat_deg, series.alt_m, strict=True
    ):
        carto.extend([float(t), float(lon), float(lat), float(alt)])
    return {
        "id": f"sat/{series.sat_id}",
        "name": series.sat_id,
        "availability": _iso_interval(start_iso, end_iso),
        "position": {
            "interpolationAlgorithm": "LINEAR",
            "interpolationDegree": 1,
            "epoch": epoch_iso,
            "cartographicDegrees": carto,
        },
        "point": {
            "pixelSize": 6,
            "color": {"rgba": list(_SAT_RGBA)},
            "outlineColor": {"rgba": [12, 20, 28, 200]},
            "outlineWidth": 1,
        },
        "path": {
            "material": {"solidColor": {"color": {"rgba": list(_PATH_RGBA)}}},
            "width": 1.2,
            "leadTime": 0,
            "trailTime": 5400,
            "resolution": 120,
        },
    }


def gs_packet(station: GroundStationConfig) -> dict[str, Any]:
    alt_m = float(station.alt_km) * 1000.0
    return {
        "id": f"gs/{station.id}",
        "name": station.id,
        "position": {
            "cartographicDegrees": [float(station.lon_deg), float(station.lat_deg), alt_m],
        },
        "point": {
            "pixelSize": 11,
            "color": {"rgba": list(_GS_RGBA)},
            "outlineColor": {"rgba": [40, 24, 8, 220]},
            "outlineWidth": 1,
        },
        "label": {
            "text": station.id,
            "font": "11px sans-serif",
            "fillColor": {"rgba": [255, 230, 200, 230]},
            "pixelOffset": {"cartesian2": [0, -16]},
            "showBackground": True,
            "backgroundColor": {"rgba": [20, 24, 30, 160]},
        },
    }


def _last_llh(series: GeodeticSeries) -> tuple[float, float, float] | None:
    if not series.lon_deg:
        return None
    return series.lon_deg[-1], series.lat_deg[-1], series.alt_m[-1]


def isl_polyline_packet(
    edge: ISLEdge,
    series: dict[str, GeodeticSeries],
    *,
    kind: str = "isl",
) -> dict[str, Any] | None:
    a = series.get(edge.a)
    b = series.get(edge.b)
    if a is None or b is None:
        return None
    pa, pb = _last_llh(a), _last_llh(b)
    if pa is None or pb is None:
        return None
    color = list(_ISL_RGBA if kind == "isl" else _GSL_RGBA)
    return {
        "id": f"{kind}/{edge.a}-{edge.b}",
        "name": f"{kind} {edge.a}–{edge.b} ({edge.range_km:.0f} km)",
        "polyline": {
            "positions": {
                "cartographicDegrees": [
                    pa[0],
                    pa[1],
                    pa[2],
                    pb[0],
                    pb[1],
                    pb[2],
                ],
            },
            "material": {"solidColor": {"color": {"rgba": color}}},
            "width": 1.4,
            "clampToGround": False,
        },
    }


def gsl_polyline_packet(
    gs_id: str,
    sat_id: str,
    range_km: float,
    stations: tuple[GroundStationConfig, ...],
    series: dict[str, GeodeticSeries],
) -> dict[str, Any] | None:
    sat = series.get(sat_id)
    if sat is None:
        return None
    ps = _last_llh(sat)
    if ps is None:
        return None
    st = next((g for g in stations if g.id == gs_id), None)
    if st is None:
        return None
    return {
        "id": f"gsl/{gs_id}-{sat_id}",
        "name": f"gsl {gs_id}–{sat_id} ({range_km:.0f} km)",
        "polyline": {
            "positions": {
                "cartographicDegrees": [
                    float(st.lon_deg),
                    float(st.lat_deg),
                    float(st.alt_km) * 1000.0,
                    ps[0],
                    ps[1],
                    ps[2],
                ],
            },
            "material": {"solidColor": {"color": {"rgba": list(_GSL_RGBA)}}},
            "width": 1.2,
            "clampToGround": False,
        },
    }


def build_czml(
    bundle: VizBundle,
    *,
    max_isl: int = 16,
    max_gsl: int = 8,
    name: str | None = None,
) -> list[dict[str, Any]]:
    """Build a CZML 1.0 packet list from a :class:`VizBundle`."""
    title = name or f"SCS-Sim {bundle.config_name or 'constellation'}"
    packets: list[dict[str, Any]] = [
        document_packet(title, bundle.epoch_iso, bundle.end_iso, multiplier=max(bundle.dt_seconds, 1.0))
    ]
    for sid in bundle.sat_ids:
        ser = bundle.series.get(sid)
        if ser is None or not ser.elapsed_s:
            continue
        packets.append(sat_packet(ser, bundle.epoch_iso, bundle.end_iso, epoch_iso=bundle.epoch_iso))
    for gs in bundle.stations:
        packets.append(gs_packet(gs))
    for edge in bundle.last_isl[: max(0, int(max_isl))]:
        pkt = isl_polyline_packet(edge, bundle.series)
        if pkt is not None:
            packets.append(pkt)
    if bundle.snapshots:
        last = bundle.snapshots[-1]
        for ge in last.gsl_edges[: max(0, int(max_gsl))]:
            pkt = gsl_polyline_packet(ge.gs, ge.sat, ge.range_km, bundle.stations, bundle.series)
            if pkt is not None:
                packets.append(pkt)
    return packets


def write_czml(path: Path, packets: list[dict[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(packets, indent=2), encoding="utf-8")
    return path
