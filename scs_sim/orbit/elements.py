"""Vectorized Keplerian element batch (scalable toward 10k sats).

Phase: 1 (core)
Completion: 90%
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import numpy as np


@dataclass
class KeplerianBatch:
    """Classical elements stored as parallel numpy arrays.

    Units: metres, radians. ``m_rad`` is mean anomaly at ``epoch``.
    """

    sat_id: np.ndarray
    shell_id: np.ndarray
    plane: np.ndarray
    slot: np.ndarray
    a_m: np.ndarray
    e: np.ndarray
    i_rad: np.ndarray
    raan_rad: np.ndarray
    argp_rad: np.ndarray
    m_rad: np.ndarray
    epoch: datetime

    def __len__(self) -> int:
        return int(self.a_m.shape[0])

    def take(self, index: np.ndarray) -> KeplerianBatch:
        return KeplerianBatch(
            sat_id=self.sat_id[index],
            shell_id=self.shell_id[index],
            plane=self.plane[index],
            slot=self.slot[index],
            a_m=self.a_m[index],
            e=self.e[index],
            i_rad=self.i_rad[index],
            raan_rad=self.raan_rad[index],
            argp_rad=self.argp_rad[index],
            m_rad=self.m_rad[index],
            epoch=self.epoch,
        )

    def copy(self) -> KeplerianBatch:
        return KeplerianBatch(
            sat_id=self.sat_id.copy(),
            shell_id=self.shell_id.copy(),
            plane=self.plane.copy(),
            slot=self.slot.copy(),
            a_m=self.a_m.copy(),
            e=self.e.copy(),
            i_rad=self.i_rad.copy(),
            raan_rad=self.raan_rad.copy(),
            argp_rad=self.argp_rad.copy(),
            m_rad=self.m_rad.copy(),
            epoch=self.epoch,
        )
