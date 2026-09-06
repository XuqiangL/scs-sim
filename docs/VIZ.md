# Visualization (Phase 6)

All artifacts are generated **without a Cesium Ion token or any API key**.
At least one viewer path works **offline** (SVG ground tracks; PNG if
matplotlib is installed).

## Artifacts

| File | What |
|------|------|
| `out/constellation.czml` | CZML 1.0: clock, sat `cartographicDegrees`, GS points, a few last-snapshot ISL/GSL polylines |
| `out/ground_tracks.svg` | Equirectangular lon/lat, no extra deps |
| `out/ground_tracks.png` | Same plot via matplotlib (`pip install -e ".[viz]"`) |
| `out/viz_globe.html` | Embedded SVG + optional CesiumJS from jsDelivr (Natural Earth II, no token) |
| `out/kpi_dashboard.json` | Coverage proxy, ISL degree, stretch histogram, job rate, fleet SoC |
| `out/kpi_report.md` | Short human-readable KPI summary |

## Generate (Windows)

```bat
scripts\run_phase6.bat
```

```powershell
.\scripts\run_phase6.ps1
```

```bat
py -3 -m scs_sim.demo_viz --config configs\phase6_viz.yaml
py -3 -m scs_sim.demo --viz
```

Open `out\viz_globe.html` in a browser. Offline, the 2D tracks still render.

That HTML is a **static replay**. To change dt, ISL range, SoC, or a single
sat's elements while the sim is running, use the control panel:

```bat
scripts\run_ui.bat
```

`http://127.0.0.1:18765/ui` — see [CONTROL.md](CONTROL.md).
Online, CesiumJS loads from the CDN and plays the embedded CZML. No Ion key.

## Drop CZML into Cesium

**Cesium ion (optional hosting)**

1. Generate `out/constellation.czml` locally (no key).
2. Sign in at [ion.cesium.com](https://ion.cesium.com) → My Assets → Add data → CZML.
3. Drop the file. Ion is only used if **you** want to host/stream the asset.

**Local CesiumJS / Sandcastle**

```html
const viewer = new Cesium.Viewer("cesiumContainer", {
  baseLayerPicker: false,
  geocoder: false,
});
const ds = await Cesium.CzmlDataSource.load("constellation.czml");
viewer.dataSources.add(ds);
viewer.flyTo(ds);
```

Serve the folder so the browser can fetch the CZML:

```bat
py -3 -m http.server 8765 --directory out
```

Then open `http://127.0.0.1:8765/viz_globe.html`. `viz_globe.html` already
embeds the CZML, so a local server is not required for the bundled viewer.

Do **not** set `Cesium.Ion.defaultAccessToken` unless you are loading Ion
imagery/terrain on purpose. The bundled viewer uses Cesium’s shipped
Natural Earth II tiles.

## KPI fields

- **coverage** — fraction of YAML ground stations with ≥1 GSL (last snapshot).
- **isl** — mean / max / min degree and edge count (last snapshot).
- **stretch** — GS↔GS Dijkstra path / haversine geodesic; histogram bins match
  the validation doc (LEOCraft-style).
- **compute** — job completion rate over the demo window.
- **fleet_soc** — mean / min / max battery state of charge.

These are demo-window proxies, not a published benchmark suite.
