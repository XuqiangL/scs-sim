"""Orekit stub: factory returns a port, propagate raises, no Java import."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from scs_sim.config import ShellConfig
from scs_sim.constellation.walker import generate_walker_shell
from scs_sim.orbit.orekit_prop import OrekitPropagator
from scs_sim.orbit.propagator import make_propagator


def test_orekit_factory_and_not_implemented() -> None:
    prop = make_propagator("orekit")
    assert prop.name == "orekit"
    assert isinstance(prop, OrekitPropagator)
    epoch = datetime(2026, 9, 6, tzinfo=timezone.utc)
    el = generate_walker_shell(
        ShellConfig(
            id="ok",
            altitude_km=550.0,
            inclination_deg=53.0,
            n_planes=1,
            n_sats_per_plane=1,
            phasing_f=0,
        ),
        epoch,
    )
    with pytest.raises(NotImplementedError, match="Orekit"):
        prop.positions_eci_m(el, 0.0)
    with pytest.raises(NotImplementedError, match="install"):
        prop.positions_ecef_m(el, epoch, 0.0)
