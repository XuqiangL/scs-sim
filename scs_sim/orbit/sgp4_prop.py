"""python-sgp4 adapter (TEME treated as ECI in Phase 1).

Phase: 1 (core)
Completion: 80%

Uses Brandon Rhodes' ``sgp4`` package. Does not vendor Simplified
Perturbations code; we only map Keplerian batches onto ``Satrec.sgp4init``.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
from sgp4.api import WGS84, Satrec, jday

from scs_sim.constants import MU_EARTH_M3_S2, SGP4_MIN_ECC
from scs_sim.orbit.elements import KeplerianBatch
from scs_sim.orbit.frames import eci_to_ecef


def _days_since_1949(dt: datetime) -> float:
    """SGP4 epoch: days from 1949-12-31 00:00 UT."""
    jd, fr = jday(
        dt.year,
        dt.month,
        dt.day,
        dt.hour,
        dt.minute,
        dt.second + dt.microsecond * 1e-6,
    )
    return (jd + fr) - 2433281.5


def _mean_motion_rad_per_min(a_m: np.ndarray) -> np.ndarray:
    n_rad_s = np.sqrt(MU_EARTH_M3_S2 / a_m**3)
    return n_rad_s * 60.0


class Sgp4Propagator:
    """Per-satellite ``Satrec`` batch. Slower than Kepler+J2; useful as a check."""

    name = "sgp4"

    def elements_at(self, elements: KeplerianBatch, elapsed_s: float) -> KeplerianBatch:
        # SGP4 does not expose updated classical elements cheaply; return a
        # shallow copy with the same epoch elements (positions use sgp4()).
        _ = elapsed_s
        return elements.copy()

    def _propagate_km(self, elements: KeplerianBatch, when: datetime) -> np.ndarray:
        epoch_days = _days_since_1949(elements.epoch)
        jd, fr = jday(
            when.year,
            when.month,
            when.day,
            when.hour,
            when.minute,
            when.second + when.microsecond * 1e-6,
        )
        n = len(elements)
        out = np.empty((n, 3), dtype=float)
        no_kozai = _mean_motion_rad_per_min(elements.a_m)
        ecc = np.maximum(elements.e, SGP4_MIN_ECC)
        for i in range(n):
            sat = Satrec()
            sat.sgp4init(
                WGS84,
                "i",
                i + 1,
                epoch_days,
                0.0,  # bstar — Phase 3 drag lives elsewhere
                0.0,
                0.0,
                float(ecc[i]),
                float(elements.argp_rad[i]),
                float(elements.i_rad[i]),
                float(elements.m_rad[i]),
                float(no_kozai[i]),
                float(elements.raan_rad[i]),
            )
            err, r_km, _v = sat.sgp4(jd, fr)
            if err != 0:
                raise RuntimeError(f"SGP4 error {err} for sat index {i}")
            out[i, :] = r_km
        return out

    def positions_eci_m(self, elements: KeplerianBatch, elapsed_s: float) -> np.ndarray:
        when = elements.epoch + timedelta(seconds=float(elapsed_s))
        return self._propagate_km(elements, when) * 1000.0

    def positions_ecef_m(
        self,
        elements: KeplerianBatch,
        epoch: datetime,
        elapsed_s: float,
    ) -> np.ndarray:
        r_eci = self.positions_eci_m(elements, elapsed_s)
        when = epoch + timedelta(seconds=float(elapsed_s))
        return eci_to_ecef(r_eci, when)
