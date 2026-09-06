"""Phase 2 ISL / GSL / routing tests.

Phase: 2 (tests)
Completion: 100%
"""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np

from scs_sim.config import GSLConfig, GroundStationConfig, ISLConfig, ShellConfig
from scs_sim.constellation.walker import generate_walker_shell
from scs_sim.network.gsl import ElevationGSL, visible_sats_for_gs
from scs_sim.network.isl import PlusGridISL, plus_grid_candidate_pairs
from scs_sim.network.routing import build_weighted_graph, dijkstra, floyd_warshall, reconstruct
from scs_sim.orbit.frames import ecef_to_geodetic
from scs_sim.orbit.kepler import KeplerJ2Propagator


def _small_walker():
    epoch = datetime(2026, 9, 6, tzinfo=timezone.utc)
    shell = ShellConfig(
        id="w6x8",
        altitude_km=550.0,
        inclination_deg=53.0,
        n_planes=6,
        n_sats_per_plane=8,
        phasing_f=1,
    )
    return generate_walker_shell(shell, epoch), epoch


def test_plus_grid_candidate_count() -> None:
    el, _ = _small_walker()
    pairs = plus_grid_candidate_pairs(el)
    # 48 sats × 4 neighbors / 2
    assert len(pairs) == 48 * 4 // 2 == 96


def test_isl_count_after_los_and_range() -> None:
    el, epoch = _small_walker()
    r = KeplerJ2Propagator().positions_eci_m(el, 0.0)
    isl = PlusGridISL(
        ISLConfig(
            pattern="plus_grid",
            max_range_km=6000.0,
            earth_occlusion=True,
            fill_geometric=False,
            max_degree=4,
        )
    )
    edges = isl.links_at(el, r)
    # Intra-plane rings alone are 6 × 8 = 48 undirected edges (~5300 km).
    assert len(edges) >= 48
    assert all(e.range_km <= 6000.0 + 1e-6 for e in edges)
    ids = {e.a for e in edges} | {e.b for e in edges}
    assert len(ids) == 48
    _ = epoch


def test_gsl_visibility_under_nadir() -> None:
    epoch = datetime(2026, 9, 6, tzinfo=timezone.utc)
    shell = ShellConfig(
        id="one",
        altitude_km=550.0,
        inclination_deg=53.0,
        n_planes=1,
        n_sats_per_plane=1,
        phasing_f=0,
    )
    el = generate_walker_shell(shell, epoch)
    r_ecef = KeplerJ2Propagator().positions_ecef_m(el, epoch, 0.0)
    lat, lon, _alt = ecef_to_geodetic(r_ecef[0])
    gs = GroundStationConfig(id="nadir", lat_deg=lat, lon_deg=lon, alt_km=0.05)
    hits = visible_sats_for_gs(gs, el.sat_id, r_ecef, GSLConfig(min_elevation_deg=25.0, max_attach=1))
    assert len(hits) == 1
    assert hits[0].sat == str(el.sat_id[0])
    assert hits[0].elev_deg > 80.0


def test_routing_finds_path_when_connected() -> None:
    # Line: GS-A — sat1 — sat2 — GS-B
    adj = build_weighted_graph(
        [("sat1", "sat2", 1000.0)],
        [("gsA", "sat1", 800.0), ("gsB", "sat2", 800.0)],
    )
    dist, prev = dijkstra(adj, "gsA")
    path = reconstruct(prev, "gsA", "gsB")
    assert path == ("gsA", "sat1", "sat2", "gsB")
    assert dist["gsB"] == 2600.0

    nodes = ["gsA", "sat1", "sat2", "gsB"]
    fw = floyd_warshall(nodes, adj)
    assert fw[0, 3] == 2600.0


def test_gsl_builder_attaches() -> None:
    epoch = datetime(2026, 9, 6, tzinfo=timezone.utc)
    shell = ShellConfig(
        id="one",
        altitude_km=550.0,
        inclination_deg=0.0,
        n_planes=1,
        n_sats_per_plane=1,
        phasing_f=0,
    )
    el = generate_walker_shell(shell, epoch)
    r_ecef = KeplerJ2Propagator().positions_ecef_m(el, epoch, 0.0)
    lat, lon, _ = ecef_to_geodetic(r_ecef[0])
    gsl = ElevationGSL(
        [GroundStationConfig(id="pad", lat_deg=lat, lon_deg=lon, alt_km=0.0)],
        GSLConfig(min_elevation_deg=10.0, max_attach=2),
    )
    edges = gsl.links_at(el.sat_id, r_ecef)
    assert len(edges) == 1
    assert gsl.visible_gateways(str(el.sat_id[0]), epoch) == ("pad",)
