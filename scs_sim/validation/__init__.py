"""Validation checks and optional literature-baseline hooks (Phase 6)."""

from scs_sim.validation.checks import (
    kepler_period_relative_error,
    max_radius_sma_rel_error,
    optional_baseline_path,
    walker_t_counts,
)

__all__ = [
    "kepler_period_relative_error",
    "max_radius_sma_rel_error",
    "optional_baseline_path",
    "walker_t_counts",
]
