"""Orekit propagator stub (Phase 7).

Implements :class:`PropagatorPort` so a future Java/Orekit adapter can drop
in behind ``make_propagator("orekit")``. This module is **pure Python** and
does not import JCC, Orekit, or a JDK. Calling any propagate method raises
``NotImplementedError`` with install hints. CI stays Java-free.
"""

from __future__ import annotations

from datetime import datetime

import numpy as np

from scs_sim.orbit.elements import KeplerianBatch

_HINT = (
    "Orekit adapter is a Phase 7 stub (no Java in this tree). "
    "To wire a real backend later: install a JDK 17+, the Orekit JAR "
    "(https://www.orekit.org/, Apache-2.0), and a Python bridge such as "
    "orekit / Hipparchus via conda-forge; then implement "
    "scs_sim.orbit.orekit_prop.OrekitPropagator behind PropagatorPort. "
    "Default demos stay on kepler_j2 / sgp4."
)


class OrekitPropagator:
    """Port-compatible stub. ``name`` is ``orekit``; methods do not propagate."""

    name = "orekit"

    def __init__(self) -> None:
        # Do not import Java here. Construction stays cheap for factory tests.
        return

    def _unsupported(self, op: str) -> None:
        raise NotImplementedError(f"OrekitPropagator.{op}: {_HINT}")

    def elements_at(self, elements: KeplerianBatch, elapsed_s: float) -> KeplerianBatch:
        self._unsupported("elements_at")
        return elements

    def positions_eci_m(self, elements: KeplerianBatch, elapsed_s: float) -> np.ndarray:
        self._unsupported("positions_eci_m")
        return np.zeros((len(elements), 3), dtype=float)

    def positions_ecef_m(
        self,
        elements: KeplerianBatch,
        epoch: datetime,
        elapsed_s: float,
    ) -> np.ndarray:
        self._unsupported("positions_ecef_m")
        return np.zeros((len(elements), 3), dtype=float)
