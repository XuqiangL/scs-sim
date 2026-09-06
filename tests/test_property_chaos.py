"""Property, chaos, and import-smoke tests."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pytest

from scs_sim.clock import SimClock
from scs_sim.config import ISLConfig, ShellConfig, load_config
from scs_sim.environment.power import BatteryBank, PowerConfig
from scs_sim.network.isl import PlusGridISL
from scs_sim.ops.deployment import OpsFleet
from scs_sim.config import DeploymentConfig, WaveConfig
from scs_sim.orbit.kepler import KeplerJ2Propagator

REPO = Path(__file__).resolve().parents[1]


def test_soc_always_unit_interval_random_seeds() -> None:
    rng = np.random.default_rng(20260906)
    for seed in range(12):
        n = 8
        bank = BatteryBank(n, PowerConfig(initial_soc=float(rng.uniform(0.05, 0.95))))
        for _ in range(15):
            sun = rng.uniform(0.0, 1.0, size=n)
            load = rng.uniform(0.0, 400.0, size=n)
            bank.step(sun, load, dt_s=float(rng.uniform(10.0, 120.0)))
            assert np.all(bank.soc >= 0.0)
            assert np.all(bank.soc <= 1.0)
            assert np.all(bank.last_gen_w >= 0.0)
            assert np.all(bank.last_load_w >= 0.0)


def test_retired_sats_never_in_isl_adjacency() -> None:
    wave = WaveConfig(
        wave_id="w",
        launch_epoch=datetime(2026, 9, 1, tzinfo=timezone.utc),
        n_sats=8,
        n_planes=2,
        n_sats_per_plane=4,
        parking_altitude_km=550.0,
        operational_altitude_km=550.0,
        inclination_deg=53.0,
        ramp_hours=0.0,
        commission_hours=0.0,
        shell_id="ops",
    )
    cfg = DeploymentConfig(waves=(wave,), station_keeping=False, conjunction=False, decommission_hours=0.0)
    fleet = OpsFleet.from_waves((wave,), wave.launch_epoch, cfg)
    now = wave.launch_epoch
    fleet.tick(now, step=0)
    assert all(r.state == "operational" for r in fleet.records)
    retired = {fleet.records[0].sat_id, fleet.records[1].sat_id}
    fleet.request_retire(2, now, step=1)
    fleet.tick(now, step=2)
    topo = fleet.topology_elements()
    assert topo is not None
    ids = {str(s) for s in topo.sat_id}
    assert retired.isdisjoint(ids)
    r = KeplerJ2Propagator().positions_eci_m(topo, 0.0)
    edges = PlusGridISL(
        ISLConfig(max_range_km=20000.0, earth_occlusion=False, fill_geometric=True)
    ).links_at(topo, r)
    involved = {e.a for e in edges} | {e.b for e in edges}
    assert retired.isdisjoint(involved)


def test_bad_yaml_and_impossible_config_raise(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "name: bad\nepoch: '2026-01-01T00:00:00Z'\npropagator: not_a_prop\nshells:\n"
        "  - {id: s, altitude_km: 550, inclination_deg: 53, n_planes: 2, n_sats_per_plane: 2, phasing_f: 0}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="propagator"):
        load_config(bad)
    empty = tmp_path / "empty.yaml"
    empty.write_text("name: e\nepoch: '2026-01-01T00:00:00Z'\npropagator: kepler_j2\nshells: []\n", encoding="utf-8")
    with pytest.raises(ValueError, match="at least one shell"):
        load_config(empty)
    with pytest.raises(ValueError, match="phasing_f"):
        ShellConfig(
            id="x",
            altitude_km=550.0,
            inclination_deg=53.0,
            n_planes=4,
            n_sats_per_plane=4,
            phasing_f=4,
        ).validate()


def test_clock_dt_positive_and_advance_semantics() -> None:
    with pytest.raises(ValueError, match="dt_seconds"):
        SimClock(epoch=datetime(2026, 1, 1, tzinfo=timezone.utc), dt_seconds=0.0)
    with pytest.raises(ValueError, match="dt_seconds"):
        SimClock(epoch=datetime(2026, 1, 1, tzinfo=timezone.utc), dt_seconds=-1.0)
    clk = SimClock(epoch=datetime(2026, 1, 1, tzinfo=timezone.utc), dt_seconds=60.0)
    t0 = clk.now
    clk.advance(0)
    assert clk.step == 0
    assert clk.now == t0
    clk.advance(2)
    assert clk.step == 2
    assert clk.elapsed_seconds == 120.0
    with pytest.raises(ValueError, match="negative"):
        clk.advance(-1)
    clk.reset()
    assert clk.step == 0


def test_import_all_public_packages() -> None:
    import importlib

    mods = [
        "scs_sim",
        "scs_sim.api",
        "scs_sim.bench",
        "scs_sim.catalog",
        "scs_sim.cli",
        "scs_sim.clock",
        "scs_sim.compute",
        "scs_sim.config",
        "scs_sim.constellation",
        "scs_sim.demo",
        "scs_sim.demo_ops",
        "scs_sim.demo_viz",
        "scs_sim.environment",
        "scs_sim.network",
        "scs_sim.ops",
        "scs_sim.orbit",
        "scs_sim.twin",
        "scs_sim.validation",
        "scs_sim.viz",
    ]
    for name in mods:
        importlib.import_module(name)
