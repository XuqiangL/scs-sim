"""Walker T = P×S and invalid phasing."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from scs_sim.config import ShellConfig
from scs_sim.constellation.walker import generate_walker_shell


def test_walker_t_equals_p_times_s() -> None:
    epoch = datetime(2026, 9, 6, tzinfo=timezone.utc)
    for p, s, f in ((3, 5, 1), (12, 10, 0), (72, 22, 17)):
        shell = ShellConfig(
            id=f"t{p}x{s}",
            altitude_km=550.0,
            inclination_deg=53.0,
            n_planes=p,
            n_sats_per_plane=s,
            phasing_f=f,
        )
        batch = generate_walker_shell(shell, epoch)
        assert len(batch) == p * s
        assert shell.n_sats == p * s


def test_invalid_phasing_f_raises() -> None:
    with pytest.raises(ValueError, match="phasing_f"):
        ShellConfig(
            id="bad",
            altitude_km=550.0,
            inclination_deg=53.0,
            n_planes=6,
            n_sats_per_plane=8,
            phasing_f=6,
        ).validate()
