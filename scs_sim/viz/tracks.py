"""Offline 2D ground-track plots: SVG always, PNG if matplotlib is installed.

No proprietary GIS license. Equirectangular lon/lat, antimeridian-safe.
"""

from __future__ import annotations

import math
from pathlib import Path

from scs_sim.config import GroundStationConfig
from scs_sim.viz.samples import GeodeticSeries

# Canvas
_W = 960
_H = 480
_PAD = 28


def _lonlat_to_xy(lon: float, lat: float) -> tuple[float, float]:
    x = _PAD + (lon + 180.0) / 360.0 * (_W - 2 * _PAD)
    y = _PAD + (90.0 - lat) / 180.0 * (_H - 2 * _PAD)
    return x, y


def _hue_hex(i: int, n: int) -> str:
    hue = (i * 360 / max(n, 1)) % 360
    # HSL → sRGB hex, sat 55%, light 62%
    h = hue / 360.0
    s, l = 0.55, 0.62

    def f(p: float, q: float, t: float) -> float:
        t = t % 1.0
        if t < 1 / 6:
            return p + (q - p) * 6 * t
        if t < 1 / 2:
            return q
        if t < 2 / 3:
            return p + (q - p) * (2 / 3 - t) * 6
        return p

    q = l * (1 + s) if l < 0.5 else l + s - l * s
    p = 2 * l - q
    r = int(round(f(p, q, h + 1 / 3) * 255))
    g = int(round(f(p, q, h) * 255))
    b = int(round(f(p, q, h - 1 / 3) * 255))
    return f"#{r:02x}{g:02x}{b:02x}"


def _split_antimeridian(lons: list[float], lats: list[float]) -> list[list[tuple[float, float]]]:
    """Break polylines when longitude jumps more than 180°."""
    if not lons:
        return []
    segs: list[list[tuple[float, float]]] = [[(lons[0], lats[0])]]
    for lo, la in zip(lons[1:], lats[1:], strict=True):
        prev = segs[-1][-1][0]
        if abs(lo - prev) > 180.0:
            segs.append([(lo, la)])
        else:
            segs[-1].append((lo, la))
    return segs


def _pick_track_ids(sat_ids: list[str], series: dict[str, GeodeticSeries], limit: int) -> list[str]:
    if len(sat_ids) <= limit:
        return list(sat_ids)
    if not sat_ids:
        return []
    step = max(1, math.ceil(len(sat_ids) / limit))
    picked = sat_ids[::step][:limit]
    # Always keep first and last so the ring is represented.
    if sat_ids[0] not in picked:
        picked[0] = sat_ids[0]
    if sat_ids[-1] not in picked:
        picked[-1] = sat_ids[-1]
    return picked


def write_ground_tracks_svg(
    path: Path,
    series: dict[str, GeodeticSeries],
    stations: tuple[GroundStationConfig, ...],
    sat_ids: list[str],
    *,
    max_tracks: int = 12,
    title: str = "SCS-Sim ground tracks",
) -> Path:
    """Write a self-contained SVG map. Works without matplotlib or network."""
    path.parent.mkdir(parents=True, exist_ok=True)
    picked = _pick_track_ids(sat_ids, series, max_tracks)
    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{_W}" height="{_H}" '
        f'viewBox="0 0 {_W} {_H}" role="img" aria-label="{title}">',
        '<rect width="100%" height="100%" fill="#0f1419"/>',
    ]
    # Graticule
    for lat in (-60, -30, 0, 30, 60):
        x1, y = _lonlat_to_xy(-180, lat)
        x2, _ = _lonlat_to_xy(180, lat)
        col = "#2a3a48" if lat else "#3d5a70"
        parts.append(
            f'<line x1="{x1:.1f}" y1="{y:.1f}" x2="{x2:.1f}" y2="{y:.1f}" '
            f'stroke="{col}" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{x1 + 4:.1f}" y="{y - 4:.1f}" fill="#6b8194" '
            f'font-size="10" font-family="Segoe UI, sans-serif">{lat}°</text>'
        )
    for lon in (-120, -60, 0, 60, 120):
        x, y1 = _lonlat_to_xy(lon, 90)
        _, y2 = _lonlat_to_xy(lon, -90)
        parts.append(
            f'<line x1="{x:.1f}" y1="{y1:.1f}" x2="{x:.1f}" y2="{y2:.1f}" '
            f'stroke="#2a3a48" stroke-width="1"/>'
        )
    parts.append(
        f'<text x="{_W / 2:.1f}" y="18" fill="#e7ecf1" text-anchor="middle" '
        f'font-size="14" font-family="Segoe UI, sans-serif">{title}</text>'
    )

    n = max(len(picked), 1)
    for i, sid in enumerate(picked):
        ser = series.get(sid)
        if ser is None or len(ser.lon_deg) < 2:
            continue
        color = _hue_hex(i, n)
        for seg in _split_antimeridian(ser.lon_deg, ser.lat_deg):
            if len(seg) < 2:
                continue
            d = "M " + " L ".join(f"{_lonlat_to_xy(lo, la)[0]:.1f},{_lonlat_to_xy(lo, la)[1]:.1f}" for lo, la in seg)
            parts.append(
                f'<path d="{d}" fill="none" stroke="{color}" stroke-width="1.6" '
                f'stroke-opacity="0.9"/>'
            )
        x, y = _lonlat_to_xy(ser.lon_deg[-1], ser.lat_deg[-1])
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.2" fill="{color}"/>')

    for gs in stations:
        x, y = _lonlat_to_xy(float(gs.lon_deg), float(gs.lat_deg))
        parts.append(
            f'<rect x="{x - 4:.1f}" y="{y - 4:.1f}" width="8" height="8" '
            f'fill="#ffb040" stroke="#3a2a10" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{x + 7:.1f}" y="{y - 6:.1f}" fill="#ffd8a0" font-size="11" '
            f'font-family="Segoe UI, sans-serif">{gs.id}</text>'
        )

    parts.append(
        f'<text x="{_PAD}" y="{_H - 8}" fill="#6b8194" font-size="10" '
        f'font-family="Segoe UI, sans-serif">'
        f"Equirectangular · {len(picked)}/{len(sat_ids)} sats · "
        f"offline SVG (no Cesium key)</text>"
    )
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")
    return path


def try_write_ground_tracks_png(
    path: Path,
    series: dict[str, GeodeticSeries],
    stations: tuple[GroundStationConfig, ...],
    sat_ids: list[str],
    *,
    max_tracks: int = 12,
    title: str = "SCS-Sim ground tracks",
) -> Path | None:
    """Write a PNG if matplotlib is installed; otherwise return None."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return None

    path.parent.mkdir(parents=True, exist_ok=True)
    picked = _pick_track_ids(sat_ids, series, max_tracks)
    fig, ax = plt.subplots(figsize=(10.0, 5.0), dpi=120)
    fig.patch.set_facecolor("#0f1419")
    ax.set_facecolor("#0f1419")
    ax.set_xlim(-180, 180)
    ax.set_ylim(-90, 90)
    ax.set_xlabel("Longitude (deg)", color="#9aa7b2")
    ax.set_ylabel("Latitude (deg)", color="#9aa7b2")
    ax.set_title(title, color="#e7ecf1")
    ax.tick_params(colors="#9aa7b2")
    for spine in ax.spines.values():
        spine.set_color("#243040")
    ax.grid(True, color="#2a3a48", linewidth=0.6)
    ax.set_xticks([-180, -120, -60, 0, 60, 120, 180])
    ax.set_yticks([-60, -30, 0, 30, 60])

    cmap = plt.get_cmap("viridis")
    n = max(len(picked), 1)
    for i, sid in enumerate(picked):
        ser = series.get(sid)
        if ser is None or len(ser.lon_deg) < 2:
            continue
        color = cmap(i / max(n - 1, 1))
        for seg in _split_antimeridian(ser.lon_deg, ser.lat_deg):
            if len(seg) < 2:
                continue
            xs = [p[0] for p in seg]
            ys = [p[1] for p in seg]
            ax.plot(xs, ys, color=color, linewidth=1.2, alpha=0.9)
        ax.scatter([ser.lon_deg[-1]], [ser.lat_deg[-1]], color=color, s=16, zorder=3)

    if stations:
        ax.scatter(
            [g.lon_deg for g in stations],
            [g.lat_deg for g in stations],
            marker="s",
            c="#ffb040",
            s=28,
            zorder=4,
        )
        for g in stations:
            ax.annotate(
                g.id,
                (g.lon_deg, g.lat_deg),
                textcoords="offset points",
                xytext=(5, 5),
                color="#ffd8a0",
                fontsize=8,
            )

    fig.tight_layout()
    fig.savefig(path, facecolor=fig.get_facecolor())
    plt.close(fig)
    return path
