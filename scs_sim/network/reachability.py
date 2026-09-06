"""Sat → gateway reachability on a snapshot graph.

Phase: 4 (compute) / 2 (network reuse)
Completion: 90%
"""

from __future__ import annotations

from typing import Iterable, Mapping, Sequence

from scs_sim.network.routing import dijkstra


def reachable_gateways(
    sat_ids: Sequence[str],
    gs_ids: Sequence[str],
    adj: Mapping[str, list[tuple[str, float]]],
) -> dict[str, frozenset[str]]:
    """For each sat, which ground stations are reachable (GSL or ISL multi-hop)."""
    gs = set(gs_ids)
    out: dict[str, frozenset[str]] = {}
    for sat in sat_ids:
        if sat not in adj:
            out[sat] = frozenset()
            continue
        dist, _prev = dijkstra(adj, sat)
        out[sat] = frozenset(g for g in gs if g in dist)
    return out


def any_gateway_reachable(sat_id: str, reach: Mapping[str, Iterable[str]]) -> bool:
    return bool(list(reach.get(sat_id, ())))
