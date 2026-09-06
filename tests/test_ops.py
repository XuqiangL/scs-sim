"""Phase 5 deployment / lifecycle / TLE tests.

Phase: 5 (tests)
Completion: 100%
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from scs_sim.config import DeploymentConfig, WaveConfig
from scs_sim.network.isl import PlusGridISL
from scs_sim.config import ISLConfig
from scs_sim.ops.deployment import OpsFleet
from scs_sim.ops.tle import parse_tle_file, tle_to_elements
from scs_sim.orbit.kepler import KeplerJ2Propagator

REPO = Path(__file__).resolve().parents[1]
FIXTURE = REPO / "tests" / "fixtures" / "starlink_sample.tle"


def _wave() -> WaveConfig:
    return WaveConfig(
        wave_id="w1",
        launch_epoch=datetime(2026, 9, 6, tzinfo=timezone.utc),
        n_sats=8,
        n_planes=2,
        n_sats_per_plane=4,
        parking_altitude_km=350.0,
        operational_altitude_km=550.0,
        inclination_deg=53.0,
        ramp_hours=2.0,
        commission_hours=1.0,
        shell_id="ops",
    )


def test_wave_advances_lifecycle_states() -> None:
    wave = _wave()
    cfg = DeploymentConfig(waves=(wave,), station_keeping=False, conjunction=False)
    fleet = OpsFleet.from_waves((wave,), wave.launch_epoch, cfg)
    t0 = wave.launch_epoch
    fleet.tick(t0 - timedelta(hours=1), step=0)
    assert all(r.state == "planned" for r in fleet.records)
    fleet.tick(t0, step=1)
    assert all(r.state == "ascending" for r in fleet.records)
    fleet.tick(t0 + timedelta(hours=2), step=2)
    assert all(r.state == "commissioning" for r in fleet.records)
    fleet.tick(t0 + timedelta(hours=3, minutes=5), step=3)
    assert all(r.state == "operational" for r in fleet.records)


def test_retired_sats_excluded_from_isl() -> None:
    wave = _wave()
    cfg = DeploymentConfig(
        waves=(wave,),
        station_keeping=False,
        conjunction=False,
        decommission_hours=1.0,
    )
    fleet = OpsFleet.from_waves((wave,), wave.launch_epoch, cfg)
    now = wave.launch_epoch + timedelta(hours=4)
    fleet.tick(now, step=0)
    assert all(r.state == "operational" for r in fleet.records)
    topo = fleet.topology_elements()
    assert topo is not None and len(topo) == 8
    prop = KeplerJ2Propagator()
    r = prop.positions_eci_m(topo, 0.0)
    edges = PlusGridISL(
        ISLConfig(max_range_km=20000.0, earth_occlusion=False, fill_geometric=True)
    ).links_at(topo, r)
    assert edges

    retired_ids = {fleet.records[0].sat_id, fleet.records[1].sat_id}
    fleet.request_retire(2, now, step=1)
    fleet.tick(now + timedelta(hours=1), step=2)
    assert sum(1 for r in fleet.records if r.state == "retired") == 2
    topo2 = fleet.topology_elements()
    assert topo2 is not None
    ids = {str(s) for s in topo2.sat_id}
    assert retired_ids.isdisjoint(ids)
    r2 = prop.positions_eci_m(topo2, 0.0)
    edges2 = PlusGridISL(
        ISLConfig(max_range_km=20000.0, earth_occlusion=False, fill_geometric=True)
    ).links_at(topo2, r2)
    involved = {e.a for e in edges2} | {e.b for e in edges2}
    assert retired_ids.isdisjoint(involved)


def test_tle_parser_loads_two_line_fixture() -> None:
    recs = parse_tle_file(FIXTURE)
    assert len(recs) >= 2
    assert recs[0].line1.startswith("1 ")
    assert recs[0].line2.startswith("2 ")
    assert recs[0].satnum == 44713
    el = tle_to_elements(recs, datetime(2026, 3, 6, tzinfo=timezone.utc))
    assert len(el) == len(recs)
    assert 6800.0 < el.a_m[0] / 1000.0 < 7200.0
    assert abs(float(el.i_rad[0]) - 53.05 * 3.1415926535 / 180.0) < 0.01
