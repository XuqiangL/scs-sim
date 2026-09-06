"""Propagator factory (port → adapter).

Phase: 1 (core) + Phase 3 drag hook + Phase 7 Orekit stub + vNext GPU
Completion: 96%
"""

from __future__ import annotations

from scs_sim.orbit.gpu_kepler import GpuKeplerJ2Propagator
from scs_sim.orbit.kepler import KeplerJ2Propagator
from scs_sim.orbit.orekit_prop import OrekitPropagator
from scs_sim.orbit.ports import PropagatorPort
from scs_sim.orbit.sgp4_prop import Sgp4Propagator


def make_propagator(
    name: str,
    *,
    atmosphere: object | None = None,
    apply_drag: bool = False,
) -> PropagatorPort:
    key = name.strip().lower()
    if key in {"kepler_j2_gpu", "gpu", "cuda", "kepler_gpu"}:
        return GpuKeplerJ2Propagator(atmosphere=atmosphere, apply_drag=apply_drag)
    if key in {"kepler_j2", "kepler", "j2"}:
        return KeplerJ2Propagator(atmosphere=atmosphere, apply_drag=apply_drag)
    if key in {"sgp4", "python-sgp4"}:
        return Sgp4Propagator()
    if key in {"orekit", "orekit_stub"}:
        return OrekitPropagator()
    raise ValueError(
        f"unknown propagator {name!r}; expected kepler_j2, kepler_j2_gpu, sgp4, or orekit"
    )
