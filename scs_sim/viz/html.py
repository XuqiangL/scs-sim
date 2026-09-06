"""Static HTML viewer: Cesium CDN if available, else offline 2D tracks.

Generation never needs a Cesium Ion token. Opening the HTML offline still
shows the embedded SVG ground tracks.
"""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

CESIUM_JS = "https://cdn.jsdelivr.net/npm/cesium@1.124.0/Build/Cesium/Cesium.js"
CESIUM_CSS = "https://cdn.jsdelivr.net/npm/cesium@1.124.0/Build/Cesium/Widgets/widgets.css"


def write_viz_html(
    path: Path,
    *,
    title: str,
    czml_packets: list[dict[str, Any]],
    svg_markup: str,
    png_name: str | None,
    czml_name: str,
    kpi: dict[str, Any],
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    cov = kpi.get("coverage", {})
    isl = kpi.get("isl", {})
    cmp_ = kpi.get("compute", {})
    soc = kpi.get("fleet_soc", {})
    rate = cmp_.get("completion_rate")
    try:
        rate_s = f"{100.0 * float(rate):.0f}%" if rate is not None and rate == rate else "n/a"
    except (TypeError, ValueError):
        rate_s = "n/a"

    czml_json = json.dumps(czml_packets, separators=(",", ":"))
    # Guard against </script> in payload (should never appear in our CZML).
    czml_json = czml_json.replace("<", "\\u003c")

    png_block = ""
    if png_name:
        png_block = (
            f'<p class="muted">PNG export (matplotlib): '
            f'<a href="{html.escape(png_name)}">{html.escape(png_name)}</a></p>'
            f'<img class="png" src="{html.escape(png_name)}" alt="Ground tracks PNG"/>'
        )

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{html.escape(title)}</title>
<style>
 body {{ margin: 0; font-family: Segoe UI, sans-serif; background: #0f1419; color: #e7ecf1; }}
 header {{ padding: 20px 24px 8px; }}
 h1 {{ font-size: 1.25rem; margin: 0 0 8px; }}
 .muted {{ color: #9aa7b2; font-size: 0.92rem; line-height: 1.45; }}
 .kpis {{ display: flex; flex-wrap: wrap; gap: 10px; padding: 0 24px 16px; }}
 .card {{ background: #171e27; border: 1px solid #243040; border-radius: 8px;
         padding: 10px 14px; min-width: 140px; }}
 .card b {{ display: block; font-size: 1.15rem; color: #7cb7ff; }}
 .card span {{ color: #9aa7b2; font-size: 0.8rem; }}
 section {{ padding: 8px 24px 24px; }}
 h2 {{ font-size: 1.05rem; color: #c5d4e0; }}
 #cesiumContainer {{ width: 100%; height: 420px; background: #0b1014;
                    border: 1px solid #243040; border-radius: 8px; }}
 #cesiumStatus {{ margin-top: 8px; }}
 .ok {{ color: #7dffa0; }}
 .warn {{ color: #ffb07d; }}
 svg {{ width: 100%; height: auto; max-width: 960px; border: 1px solid #243040;
        border-radius: 8px; background: #0f1419; }}
 img.png {{ max-width: 100%; border: 1px solid #243040; border-radius: 8px; }}
 code {{ color: #9ad4ff; }}
 ol {{ color: #c5d4e0; }}
 a {{ color: #7cb7ff; }}
</style>
</head>
<body>
<header>
  <h1>{html.escape(title)}</h1>
  <p class="muted">
    CZML is generated without a Cesium Ion key.
    Offline: the 2D ground tracks below always render.
    Online: CesiumJS loads from jsDelivr (Natural Earth II, no Ion token).
  </p>
</header>
<div class="kpis">
  <div class="card"><b>{kpi.get('n_sats', '—')}</b><span>satellites</span></div>
  <div class="card"><b>{cov.get('gs_with_link', '—')}/{cov.get('n_gs', '—')}</b><span>GS with ≥1 link</span></div>
  <div class="card"><b>{_safe_fmt(isl.get('mean_degree'))}</b><span>mean ISL degree</span></div>
  <div class="card"><b>{rate_s}</b><span>job completion</span></div>
  <div class="card"><b>{_safe_fmt(soc.get('last_mean'))}</b><span>fleet SoC (last)</span></div>
</div>
<section>
  <h2>3D globe (optional CesiumJS)</h2>
  <div id="cesiumContainer"></div>
  <p id="cesiumStatus" class="muted">Trying Cesium CDN…</p>
</section>
<section>
  <h2>2D ground tracks (offline fallback)</h2>
  <p class="muted">Equirectangular lon/lat from the same propagator samples. No network required.</p>
  {svg_markup}
  {png_block}
</section>
<section>
  <h2>Use the CZML file</h2>
  <p class="muted">Standalone file: <code>{html.escape(czml_name)}</code></p>
  <ol>
    <li><b>Cesium ion</b> — sign in at ion.cesium.com → My Assets → Add data → CZML → drop the file. Ion is only needed to <em>host</em> the asset, not to generate it.</li>
    <li><b>Sandcastle / local CesiumJS</b> — <code>Cesium.CzmlDataSource.load('constellation.czml')</code> then <code>viewer.dataSources.add(ds)</code>. Serve the <code>out/</code> folder with <code>python -m http.server 8765</code> if the browser blocks <code>file://</code> fetches. This HTML already embeds the CZML, so the CDN globe works without a local server.</li>
    <li><b>No key / offline</b> — ignore the globe; use the SVG (and PNG if matplotlib was installed).</li>
  </ol>
</section>
<link rel="stylesheet" href="{CESIUM_CSS}"/>
<script>window.SCS_CZML = {czml_json};</script>
<script>
(function () {{
  var status = document.getElementById("cesiumStatus");
  function fail(msg) {{
    status.className = "warn";
    status.textContent = msg;
  }}
  function boot() {{
    if (typeof Cesium === "undefined") {{
      fail("Cesium CDN unavailable — 2D tracks below still work offline.");
      return;
    }}
    try {{
      if (Cesium.Ion) {{ Cesium.Ion.defaultAccessToken = ""; }}
      var opts = {{
        baseLayerPicker: false,
        geocoder: false,
        homeButton: true,
        sceneModePicker: true,
        navigationHelpButton: false,
        animation: true,
        timeline: true,
        fullscreenButton: true,
        infoBox: true
      }};
      var ne = Cesium.buildModuleUrl("Assets/Textures/NaturalEarthII");
      if (Cesium.TileMapServiceImageryProvider && Cesium.TileMapServiceImageryProvider.fromUrl) {{
        opts.baseLayer = Cesium.ImageryLayer.fromProviderAsync(
          Cesium.TileMapServiceImageryProvider.fromUrl(ne)
        );
      }} else if (Cesium.TileMapServiceImageryProvider) {{
        opts.imageryProvider = new Cesium.TileMapServiceImageryProvider({{ url: ne }});
      }}
      var viewer = new Cesium.Viewer("cesiumContainer", opts);
      if (viewer.scene && viewer.scene.globe) {{
        viewer.scene.globe.enableLighting = false;
      }}
      var ds = Cesium.CzmlDataSource.load(window.SCS_CZML);
      viewer.dataSources.add(ds);
      ds.then(function (loaded) {{
        viewer.flyTo(loaded, {{ duration: 1.2 }});
      }});
      status.className = "ok";
      status.textContent = "CesiumJS loaded (no Ion token). Clock follows the demo window.";
    }} catch (err) {{
      fail("Cesium failed (" + err + "). Use the 2D tracks or drop constellation.czml into Sandcastle.");
    }}
  }}
  var s = document.createElement("script");
  s.src = "{CESIUM_JS}";
  s.async = true;
  s.onload = boot;
  s.onerror = function () {{
    fail("Cesium CDN blocked or offline — SVG/PNG ground tracks are the supported path.");
  }};
  document.head.appendChild(s);
}})();
</script>
</body>
</html>
"""
    path.write_text(page, encoding="utf-8")
    return path


def _safe_fmt(value: Any, digits: int = 2) -> str:
    try:
        x = float(value)
    except (TypeError, ValueError):
        return "—"
    if x != x:
        return "—"
    return f"{x:.{digits}f}"
