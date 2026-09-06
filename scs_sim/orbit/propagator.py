"""Propagator factory (port → adapter).

Phase: 1 (core)
Completion: 90%
"""

from __future__ import annotations

from scs_sim.orbit.kepler import KeplerJ2Propagator
from scs_sim.orbit.ports import PropagatorPort
from scs_sim.orbit.sgp4_prop import Sgp4Propagator


def make_propagator(name: str) -> PropagatorPort:
    key = name.strip().lower()
    if key in {"kepler_j2", "kepler", "j2"}:
        return KeplerJ2Propagator()
    if key in {"sgp4", "python-sgp4"}:
        return Sgp4Propagator()
    raise ValueError(f"unknown propagator {name!r}; expected kepler_j2 or sgp4")
