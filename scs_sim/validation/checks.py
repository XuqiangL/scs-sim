"""Deterministic validation helpers used by tests/test_validation.py.

Hard checks (always run):

- Orbital period vs Kepler ``T = 2π √(a³/μ)``
- Walker T count vs YAML ``n_planes * n_sats_per_plane``
- Geocentric radius ≈ semi-major axis for near-circular sats

Optional literature comparisons (Hypatia RTT, LEOCraft stretch) load JSON
from ``tests/baselines/`` when present and **must not fail** if the files
are absent — those are future alignments, not CI gates.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from scs_sim.config import SimConfig
from scs_sim.constants import MU_EARTH_M3_S2
from scs_sim.constellation.walker import generate_constellation
from scs_sim.orbit.elements import KeplerianBatch
from scs_sim.orbit.kepler import orbital_period_s

# Documented default tolerances (also restated in docs/VALIDATION.md).
PERIOD_REL_TOL = 1e-12
RADIUS_REL_TOL = 1e-4  # near-circular e ≈ 0 after Kepler conversion
WALKER_T_ABS_TOL = 0  # exact integer match


def kepler_period_formula_s(a_m: float) -> float:
    """Textbook two-body period ``T = 2π √(a³/μ)``."""
    a = float(a_m)
    return float(2.0 * np.pi * np.sqrt(a**3 / MU_EARTH_M3_S2))


def kepler_period_relative_error(a_m: float) -> float:
    """|impl − formula| / formula for :func:`orbital_period_s`."""
    impl = float(orbital_period_s(a_m))
    ref = kepler_period_formula_s(a_m)
    return abs(impl - ref) / ref


def walker_t_counts(cfg: SimConfig) -> tuple[int, int, int]:
    """Return (configured T, generated T, sum of shell P×S).

    Generated T uses the full configured constellation (no demo subsample).
    """
    configured = int(cfg.n_sats_configured)
    shell_sum = int(sum(s.n_planes * s.n_sats_per_plane for s in cfg.shells))
    batch = generate_constellation(cfg, max_sats=configured, subsample="stride")
    return configured, int(len(batch)), shell_sum


def max_radius_sma_rel_error(elements: KeplerianBatch, r_eci_m: np.ndarray) -> float:
    """max |‖r‖ − a| / a. For e ≈ 0 this should be ~0 (machine + conversion)."""
    r = np.linalg.norm(np.asarray(r_eci_m, dtype=float).reshape(-1, 3), axis=1)
    a = np.asarray(elements.a_m, dtype=float)
    return float(np.max(np.abs(r - a) / np.maximum(a, 1.0)))


def optional_baseline_path(repo_root: Path, name: str) -> Path | None:
    """Return a baseline JSON path if it exists, else None (do not fail)."""
    path = Path(repo_root) / "tests" / "baselines" / name
    return path if path.is_file() else None


def rtt_ms_from_path_km(path_km: float, c_km_s: float = 299_792.458) -> float:
    """One-way optical delay × 2 (Hypatia-style RTT proxy, vacuum)."""
    return 2.0 * 1000.0 * float(path_km) / c_km_s
