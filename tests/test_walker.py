"""Walker generation count.

Phase: 1 (tests)
Completion: 100%
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from scs_sim.config import ShellConfig, load_config
from scs_sim.constellation.walker import generate_constellation, generate_walker_shell

REPO = Path(__file__).resolve().parents[1]


def test_walker_shell_count_starlink_like() -> None:
    shell = ShellConfig(
        id="sl_550",
        altitude_km=550.0,
        inclination_deg=53.0,
        n_planes=72,
        n_sats_per_plane=22,
        phasing_f=17,
    )
    batch = generate_walker_shell(shell, datetime(2026, 9, 6, tzinfo=timezone.utc))
    assert len(batch) == 72 * 22 == 1584
    assert len(set(batch.sat_id.tolist())) == 1584
    assert int(batch.plane.max()) == 71
    assert int(batch.slot.max()) == 21


def test_walker_10k_config_count() -> None:
    cfg = load_config(REPO / "configs" / "walker_10k.yaml")
    assert cfg.n_sats_configured == 10_008
    full = generate_constellation(cfg, max_sats=10_008)
    assert len(full) == 10_008
    demo = generate_constellation(cfg)  # uses demo.max_sats = 100
    assert len(demo) == 100
    assert len(set(int(p) for p in demo.plane)) >= 4
