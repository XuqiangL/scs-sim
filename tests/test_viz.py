"""Phase 6 CZML / KPI / SVG smoke tests. No Cesium key, no network."""

from __future__ import annotations

import json
from pathlib import Path

from scs_sim.config import GroundStationConfig
from scs_sim.network.isl import ISLEdge
from scs_sim.viz.czml import build_czml, write_czml
from scs_sim.viz.kpi import build_kpi, write_kpi
from scs_sim.viz.samples import GeodeticSeries, VizBundle
from scs_sim.viz.tracks import write_ground_tracks_svg

import numpy as np
import pytest


def _bundle() -> VizBundle:
    ser_a = GeodeticSeries(
        sat_id="sat-a",
        elapsed_s=[0.0, 60.0],
        lon_deg=[-10.0, 0.0],
        lat_deg=[50.0, 51.0],
        alt_m=[550_000.0, 550_100.0],
    )
    ser_b = GeodeticSeries(
        sat_id="sat-b",
        elapsed_s=[0.0, 60.0],
        lon_deg=[20.0, 25.0],
        lat_deg=[10.0, 11.0],
        alt_m=[550_000.0, 549_900.0],
    )
    gs = (GroundStationConfig(id="london", lat_deg=51.5, lon_deg=-0.1, alt_km=0.05),)
    return VizBundle(
        epoch_iso="2026-09-06T00:00:00Z",
        end_iso="2026-09-06T00:01:00Z",
        dt_seconds=60.0,
        sat_ids=["sat-a", "sat-b"],
        series={"sat-a": ser_a, "sat-b": ser_b},
        stations=gs,
        snapshots=[],
        last_isl=[ISLEdge(a="sat-a", b="sat-b", range_km=2100.0, kind="plus_grid")],
        soc_mean_by_step=[0.8, 0.79],
        soc_min_by_step=[0.7, 0.69],
        soc_max_by_step=[0.9, 0.88],
        last_soc=np.array([0.79, 0.81]),
        n_jobs_submitted=4,
        n_jobs_completed=3,
        config_name="unit",
        config_path="configs/phase6_viz.yaml",
        n_sats=2,
        n_steps=2,
    )


def test_czml_has_document_sats_and_isl(tmp_path: Path) -> None:
    packets = build_czml(_bundle(), max_isl=4)
    assert packets[0]["id"] == "document"
    assert packets[0]["version"] == "1.0"
    assert "clock" in packets[0]
    ids = [p["id"] for p in packets]
    assert "sat/sat-a" in ids
    assert "sat/sat-b" in ids
    assert "gs/london" in ids
    assert any(i.startswith("isl/") for i in ids)
    sat = next(p for p in packets if p["id"] == "sat/sat-a")
    carto = sat["position"]["cartographicDegrees"]
    # epoch seconds, lon, lat, height, ...
    assert carto[0] == 0.0
    assert carto[1] == -10.0
    assert carto[3] == 550_000.0
    out = write_czml(tmp_path / "constellation.czml", packets)
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert isinstance(loaded, list)
    assert loaded[0]["id"] == "document"


def test_svg_and_kpi_offline(tmp_path: Path) -> None:
    b = _bundle()
    svg = write_ground_tracks_svg(tmp_path / "tracks.svg", b.series, b.stations, b.sat_ids)
    text = svg.read_text(encoding="utf-8")
    assert text.startswith("<svg")
    assert "london" in text
    kpi = build_kpi(b)
    assert kpi["compute"]["completion_rate"] == pytest.approx(0.75)
    assert "coverage" in kpi and "isl" in kpi and "stretch" in kpi and "fleet_soc" in kpi
    j, md = write_kpi(tmp_path / "kpi.json", tmp_path / "kpi.md", kpi)
    assert json.loads(j.read_text(encoding="utf-8"))["n_sats"] == 2
    assert "KPI report" in md.read_text(encoding="utf-8")
