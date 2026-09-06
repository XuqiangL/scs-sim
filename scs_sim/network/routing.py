"""Snapshot routing: Dijkstra + Floyd–Warshall, GS↔GS stretch / hops.

Phase: 2 (network)
Completion: 90%

Clean-room graphs. Metrics inspired by Hypatia / LEOPath / StarPerf papers,
not their source.
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass
from typing import Iterable

import numpy as np

from scs_sim.config import GroundStationConfig
from scs_sim.orbit.frames import haversine_m


@dataclass(frozen=True)
class PathResult:
    src: str
    dst: str
    hops: int
    path_km: float
    geodesic_km: float
    stretch: float
    path: tuple[str, ...]


@dataclass(frozen=True)
class RoutingSummary:
    pairs: int
    connected: int
    mean_hops: float
    mean_stretch: float
    mean_path_km: float
    paths: tuple[PathResult, ...]


def build_weighted_graph(
    isl_edges: Iterable[tuple[str, str, float]],
    gsl_edges: Iterable[tuple[str, str, float]],
) -> dict[str, list[tuple[str, float]]]:
    """Undirected adjacency: node → [(neighbor, range_km), ...]."""
    adj: dict[str, list[tuple[str, float]]] = {}

    def add(u: str, v: str, w: float) -> None:
        adj.setdefault(u, []).append((v, w))
        adj.setdefault(v, []).append((u, w))

    for a, b, w in isl_edges:
        add(a, b, float(w))
    for gs, sat, w in gsl_edges:
        add(gs, sat, float(w))
    return adj


def dijkstra(
    adj: dict[str, list[tuple[str, float]]],
    source: str,
) -> tuple[dict[str, float], dict[str, str]]:
    dist: dict[str, float] = {source: 0.0}
    prev: dict[str, str] = {}
    heap: list[tuple[float, str]] = [(0.0, source)]
    while heap:
        d, u = heapq.heappop(heap)
        if d != dist.get(u, float("inf")):
            continue
        for v, w in adj.get(u, ()):
            nd = d + w
            if nd < dist.get(v, float("inf")):
                dist[v] = nd
                prev[v] = u
                heapq.heappush(heap, (nd, v))
    return dist, prev


def reconstruct(prev: dict[str, str], src: str, dst: str) -> tuple[str, ...] | None:
    if dst != src and dst not in prev:
        return None
    node = dst
    path = [node]
    while node != src:
        node = prev[node]
        path.append(node)
    path.reverse()
    return tuple(path)


def floyd_warshall(nodes: list[str], adj: dict[str, list[tuple[str, float]]]) -> np.ndarray:
    """All-pairs shortest path (km). ``inf`` = disconnected."""
    idx = {n: i for i, n in enumerate(nodes)}
    n = len(nodes)
    dist = np.full((n, n), np.inf, dtype=float)
    np.fill_diagonal(dist, 0.0)
    for u, nbrs in adj.items():
        if u not in idx:
            continue
        i = idx[u]
        for v, w in nbrs:
            if v in idx:
                dist[i, idx[v]] = min(dist[i, idx[v]], float(w))
    for k in range(n):
        dist = np.minimum(dist, dist[:, k : k + 1] + dist[k : k + 1, :])
    return dist


def gs_pair_metrics(
    stations: Iterable[GroundStationConfig],
    adj: dict[str, list[tuple[str, float]]],
) -> RoutingSummary:
    gs = list(stations)
    paths: list[PathResult] = []
    hops_acc: list[int] = []
    stretch_acc: list[float] = []
    path_km_acc: list[float] = []
    pairs = 0
    connected = 0
    for i, a in enumerate(gs):
        dist, prev = dijkstra(adj, a.id)
        for b in gs[i + 1 :]:
            pairs += 1
            geo = haversine_m(a.lat_deg, a.lon_deg, b.lat_deg, b.lon_deg) / 1000.0
            path = reconstruct(prev, a.id, b.id)
            if path is None:
                continue
            connected += 1
            hops = max(0, len(path) - 1)
            pkm = float(dist[b.id])
            stretch = pkm / max(geo, 1.0)
            hops_acc.append(hops)
            stretch_acc.append(stretch)
            path_km_acc.append(pkm)
            paths.append(
                PathResult(
                    src=a.id,
                    dst=b.id,
                    hops=hops,
                    path_km=pkm,
                    geodesic_km=geo,
                    stretch=stretch,
                    path=path,
                )
            )
    return RoutingSummary(
        pairs=pairs,
        connected=connected,
        mean_hops=float(np.mean(hops_acc)) if hops_acc else float("nan"),
        mean_stretch=float(np.mean(stretch_acc)) if stretch_acc else float("nan"),
        mean_path_km=float(np.mean(path_km_acc)) if path_km_acc else float("nan"),
        paths=tuple(paths),
    )
