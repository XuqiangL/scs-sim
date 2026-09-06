"""Walker-delta generator, vectorized toward 10k satellites.

Phase: 1 (core) + Phase 2 subsample modes
Completion: 95%

Clean-room Walker i:T/P/F placement (RAAN = 2π k/P,
M = 2π F k/T + 2π j/S). Inspired by published Walker geometry, not
copied from Hypatia / LEOCraft / StarPerf.
"""

from __future__ import annotations

from datetime import datetime

import numpy as np

from scs_sim.config import ShellConfig, SimConfig
from scs_sim.constants import R_EARTH_M
from scs_sim.orbit.elements import KeplerianBatch


def generate_walker_shell(
    shell: ShellConfig,
    epoch: datetime,
    *,
    sat_id_offset: int = 0,
) -> KeplerianBatch:
    """Build one circular Walker-delta shell as a :class:`KeplerianBatch`."""
    shell.validate()
    p = int(shell.n_planes)
    s = int(shell.n_sats_per_plane)
    t = p * s
    f = int(shell.phasing_f)

    plane = np.repeat(np.arange(p, dtype=np.int32), s)
    slot = np.tile(np.arange(s, dtype=np.int32), p)
    raan = np.deg2rad(shell.raan_offset_deg) + 2.0 * np.pi * plane / p
    mean_anom = 2.0 * np.pi * f * plane / t + 2.0 * np.pi * slot / s

    a_m = np.full(t, R_EARTH_M + shell.altitude_km * 1000.0, dtype=float)
    e = np.full(t, float(shell.eccentricity), dtype=float)
    i_rad = np.full(t, np.deg2rad(shell.inclination_deg), dtype=float)
    argp = np.full(t, np.deg2rad(shell.arg_perigee_deg), dtype=float)

    sat_id = np.array(
        [f"{shell.id}-{sat_id_offset + k:05d}" for k in range(t)],
        dtype=object,
    )
    shell_id = np.full(t, shell.id, dtype=object)

    return KeplerianBatch(
        sat_id=sat_id,
        shell_id=shell_id,
        plane=plane,
        slot=slot,
        a_m=a_m,
        e=e,
        i_rad=i_rad,
        raan_rad=np.mod(raan, 2.0 * np.pi),
        argp_rad=np.mod(argp, 2.0 * np.pi),
        m_rad=np.mod(mean_anom, 2.0 * np.pi),
        epoch=epoch,
        n_planes=np.full(t, p, dtype=np.int32),
        n_slots=np.full(t, s, dtype=np.int32),
    )


def _concat(batches: list[KeplerianBatch], epoch: datetime) -> KeplerianBatch:
    return KeplerianBatch(
        sat_id=np.concatenate([b.sat_id for b in batches]),
        shell_id=np.concatenate([b.shell_id for b in batches]),
        plane=np.concatenate([b.plane for b in batches]),
        slot=np.concatenate([b.slot for b in batches]),
        a_m=np.concatenate([b.a_m for b in batches]),
        e=np.concatenate([b.e for b in batches]),
        i_rad=np.concatenate([b.i_rad for b in batches]),
        raan_rad=np.concatenate([b.raan_rad for b in batches]),
        argp_rad=np.concatenate([b.argp_rad for b in batches]),
        m_rad=np.concatenate([b.m_rad for b in batches]),
        epoch=epoch,
        n_planes=np.concatenate([b.n_planes for b in batches]),
        n_slots=np.concatenate([b.n_slots for b in batches]),
    )


def subsample_even(elements: KeplerianBatch, max_sats: int) -> KeplerianBatch:
    """Keep up to ``max_sats`` satellites, evenly strided across the stack."""
    n = len(elements)
    if max_sats <= 0:
        raise ValueError("max_sats must be positive")
    if n <= max_sats:
        return elements
    idx = np.linspace(0, n - 1, max_sats, dtype=int)
    return elements.take(idx)


def subsample_first_shell(elements: KeplerianBatch, max_sats: int) -> KeplerianBatch:
    """Keep the first ``max_sats`` of the first shell (preserves +Grid rings)."""
    n = len(elements)
    if max_sats <= 0:
        raise ValueError("max_sats must be positive")
    if n <= max_sats:
        return elements
    first = str(elements.shell_id[0])
    in_first = np.where(elements.shell_id == first)[0]
    if in_first.size >= max_sats:
        return elements.take(in_first[:max_sats])
    rest = np.where(elements.shell_id != first)[0]
    idx = np.concatenate([in_first, rest[: max_sats - in_first.size]])
    return elements.take(idx)


def subsample_spread_planes(elements: KeplerianBatch, max_sats: int) -> KeplerianBatch:
    """Take whole planes spaced around the first shell (coverage + intra-plane rings)."""
    n = len(elements)
    if max_sats <= 0:
        raise ValueError("max_sats must be positive")
    if n <= max_sats:
        return elements
    first = str(elements.shell_id[0])
    idx_first = np.where(elements.shell_id == first)[0]
    planes = elements.plane[idx_first]
    unique = np.unique(planes)
    n_slots = int(elements.n_slots[idx_first[0]]) if elements.n_slots is not None else 1
    n_take = max(1, min(len(unique), max_sats // max(n_slots, 1)))
    pick = np.linspace(0, len(unique) - 1, n_take, dtype=int)
    chosen = set(int(p) for p in unique[pick])
    keep: list[int] = []
    for i in idx_first:
        if int(elements.plane[i]) in chosen:
            keep.append(int(i))
    keep_arr = np.array(keep, dtype=int)[:max_sats]
    if keep_arr.size < max_sats:
        rest = np.setdiff1d(np.arange(n), keep_arr, assume_unique=False)
        keep_arr = np.concatenate([keep_arr, rest[: max_sats - keep_arr.size]])
    return elements.take(keep_arr)


def generate_constellation(
    cfg: SimConfig,
    *,
    max_sats: int | None = None,
    subsample: str | None = None,
) -> KeplerianBatch:
    """Generate all configured shells, optionally subsampled for a demo."""
    batches: list[KeplerianBatch] = []
    offset = 0
    for shell in cfg.shells:
        batches.append(generate_walker_shell(shell, cfg.epoch, sat_id_offset=offset))
        offset += shell.n_sats
    elements = _concat(batches, cfg.epoch)
    limit = cfg.demo.max_sats if max_sats is None else max_sats
    mode = cfg.demo.subsample if subsample is None else subsample
    if limit is not None:
        if mode == "first_shell":
            elements = subsample_first_shell(elements, limit)
        elif mode == "spread_planes":
            elements = subsample_spread_planes(elements, limit)
        else:
            elements = subsample_even(elements, limit)
    return elements
