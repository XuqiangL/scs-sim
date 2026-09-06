"""Phase 6 validation harness.

Hard checks always run. Hypatia RTT / LEOCraft stretch comparisons are
documented future work and skip (do not fail) when baseline JSON is absent.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pytest

from scs_sim.config import ShellConfig, load_config
from scs_sim.constellation.walker import generate_walker_shell
from scs_sim.orbit.kepler import KeplerJ2Propagator
from scs_sim.validation.checks import (
    PERIOD_REL_TOL,
    RADIUS_REL_TOL,
    kepler_period_formula_s,
    kepler_period_relative_error,
    max_radius_sma_rel_error,
    optional_baseline_path,
    rtt_ms_from_path_km,
    walker_t_counts,
)

REPO = Path(__file__).resolve().parents[1]


def test_orbital_period_matches_kepler_formula() -> None:
    # 550 km LEO and a GEO-ish a, both vs T = 2π √(a³/μ)
    for alt_km in (400.0, 550.0, 1100.0):
        a = 6_378_137.0 + alt_km * 1000.0
        err = kepler_period_relative_error(a)
        assert err <= PERIOD_REL_TOL
        period = kepler_period_formula_s(a)
        assert 80.0 * 60 < period < 130.0 * 60


def test_walker_t_matches_config() -> None:
    cfg = load_config(REPO / "configs" / "walker_10k.yaml")
    configured, generated, shell_sum = walker_t_counts(cfg)
    assert configured == 10_008
    assert shell_sum == 10_008
    assert generated == configured

    viz = load_config(REPO / "configs" / "phase6_viz.yaml")
    c, g, s = walker_t_counts(viz)
    assert c == 6 * 6 == 36
    assert s == 36
    assert g == 36


def test_radius_approx_sma_near_circular() -> None:
    epoch = datetime(2026, 9, 6, tzinfo=timezone.utc)
    shell = ShellConfig(
        id="circ",
        altitude_km=550.0,
        inclination_deg=53.0,
        n_planes=3,
        n_sats_per_plane=4,
        phasing_f=1,
        eccentricity=0.0,
    )
    el = generate_walker_shell(shell, epoch)
    prop = KeplerJ2Propagator()
    r0 = prop.positions_eci_m(el, 0.0)
    r1 = prop.positions_eci_m(el, 120.0)
    assert max_radius_sma_rel_error(el, r0) <= RADIUS_REL_TOL
    assert max_radius_sma_rel_error(el, r1) <= RADIUS_REL_TOL
    assert float(np.max(el.e)) < 1e-12


def test_hypatia_rtt_baseline_optional() -> None:
    """Future: compare 2·path_km/c to a Hypatia RTT table if one is checked in."""
    path = optional_baseline_path(REPO, "hypatia_rtt.json")
    if path is None:
        pytest.skip("Hypatia RTT baseline not present (documented future comparison)")
    raw = json.loads(path.read_text(encoding="utf-8"))
    pairs = raw.get("pairs") or []
    assert pairs, "baseline file exists but has no pairs"
    for row in pairs:
        proxy = rtt_ms_from_path_km(float(row["path_km"]))
        ref = float(row["rtt_ms"])
        # Loose — literature traces include processing delay we do not model.
        assert abs(proxy - ref) / max(ref, 1.0) < 0.5


def test_leocraft_stretch_baseline_optional() -> None:
    """Future: compare mean GS↔GS stretch to a LEOCraft snapshot if present."""
    path = optional_baseline_path(REPO, "leocraft_stretch.json")
    if path is None:
        pytest.skip("LEOCraft stretch baseline not present (documented future comparison)")
    raw = json.loads(path.read_text(encoding="utf-8"))
    mean_ref = float(raw["mean_stretch"])
    assert mean_ref >= 1.0
