"""Ops action stubs: station-keeping already on the fleet; conjunction screen.

Phase: 5 (ops)
Completion: 85%
"""

from __future__ import annotations

import numpy as np

from scs_sim.ops.lifecycle import OpsEvent
from scs_sim.orbit.elements import KeplerianBatch


def conjunction_warnings(
    elements: KeplerianBatch,
    r_eci_m: np.ndarray,
    *,
    threshold_km: float,
    sample: int,
    now_iso: str,
    step: int,
) -> list[OpsEvent]:
    """Pairwise distance check on an evenly sampled operational subset."""
    n = len(elements)
    if n < 2:
        return []
    if n > sample:
        idx = np.linspace(0, n - 1, sample, dtype=int)
        r = np.asarray(r_eci_m, dtype=float).reshape(-1, 3)[idx]
        ids = elements.sat_id[idx]
    else:
        r = np.asarray(r_eci_m, dtype=float).reshape(-1, 3)
        ids = elements.sat_id
    m = r.shape[0]
    events: list[OpsEvent] = []
    thr = threshold_km * 1000.0
    # Upper triangle only; O(sample²) on the subsample
    for i in range(m):
        d = np.linalg.norm(r[i + 1 :] - r[i], axis=1)
        hits = np.where(d < thr)[0]
        for h in hits:
            j = i + 1 + int(h)
            events.append(
                OpsEvent(
                    t_utc=now_iso,
                    step=step,
                    kind="conjunction_warn",
                    sat_id=str(ids[i]),
                    wave_id="*",
                    detail=f"{ids[i]} vs {ids[j]} at {d[h]/1000.0:.2f} km",
                    extra={"other": str(ids[j]), "range_km": float(d[h] / 1000.0)},
                )
            )
    return events
