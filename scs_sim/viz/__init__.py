"""Phase 6 visualization: CZML, ground tracks, KPI dashboard.

No Cesium API key is required to generate artifacts. The 2D SVG/PNG
path works offline; CesiumJS is optional at view time only.
"""

from scs_sim.viz.czml import build_czml, write_czml
from scs_sim.viz.kpi import build_kpi, write_kpi
from scs_sim.viz.tracks import write_ground_tracks_svg, try_write_ground_tracks_png

__all__ = [
    "build_czml",
    "write_czml",
    "build_kpi",
    "write_kpi",
    "write_ground_tracks_svg",
    "try_write_ground_tracks_png",
]
