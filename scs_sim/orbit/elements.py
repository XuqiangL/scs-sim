"""Vectorized Keplerian element batch (scalable toward 10k sats).

Phase: 1 (core)
Completion: 95%
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import numpy as np


def _idx(arr: np.ndarray, index: np.ndarray) -> np.ndarray:
    return arr[index]


@dataclass
class KeplerianBatch:
    """Classical elements stored as parallel numpy arrays.

    Units: metres, radians. ``m_rad`` is mean anomaly at ``epoch``.
    ``n_planes`` / ``n_slots`` are the Walker P/S of each sat's shell (for +Grid).
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
    n_planes: np.ndarray | None = None
    n_slots: np.ndarray | None = None

    def __post_init__(self) -> None:
        n = int(self.a_m.shape[0])
        if self.n_planes is None:
            self.n_planes = np.full(n, int(self.plane.max()) + 1 if n else 0, dtype=np.int32)
        if self.n_slots is None:
            self.n_slots = np.full(n, int(self.slot.max()) + 1 if n else 0, dtype=np.int32)

    def __len__(self) -> int:
        return int(self.a_m.shape[0])

    def take(self, index: np.ndarray) -> KeplerianBatch:
        return KeplerianBatch(
            sat_id=_idx(self.sat_id, index),
            shell_id=_idx(self.shell_id, index),
            plane=_idx(self.plane, index),
            slot=_idx(self.slot, index),
            a_m=_idx(self.a_m, index),
            e=_idx(self.e, index),
            i_rad=_idx(self.i_rad, index),
            raan_rad=_idx(self.raan_rad, index),
            argp_rad=_idx(self.argp_rad, index),
            m_rad=_idx(self.m_rad, index),
            epoch=self.epoch,
            n_planes=_idx(self.n_planes, index) if self.n_planes is not None else None,
            n_slots=_idx(self.n_slots, index) if self.n_slots is not None else None,
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
            n_planes=None if self.n_planes is None else self.n_planes.copy(),
            n_slots=None if self.n_slots is None else self.n_slots.copy(),
        )
