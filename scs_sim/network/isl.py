"""+Grid / Walker-adjacent inter-satellite links.

Phase: 2 (network)
Completion: 90%

Intra-plane ±1 and inter-plane ±1 (+Grid), then LOS + max-range filter.
Optional geometric fill to ``max_degree`` when a subsample dropped neighbors.
Inspired by LEOCraft / Hypatia +Grid — clean-room implementation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, Sequence

import numpy as np

from scs_sim.config import ISLConfig
from scs_sim.network.geometry import earth_occludes_segment, pairwise_range_m
from scs_sim.orbit.elements import KeplerianBatch


class ISLTopologyPort(Protocol):
    name: str

    def neighbors(self, sat_id: str, when: datetime) -> Sequence[str]:
        """Local ISL peers at ``when`` (requires a prior ``links_at`` call)."""

    def adjacency(self, when: datetime) -> np.ndarray:
        """Boolean adjacency matrix (N, N)."""


@dataclass(frozen=True)
class ISLEdge:
    a: str
    b: str
    range_km: float
    kind: str  # plus_grid | geometric


class NullISL:
    """Empty ISL fabric (kept for tests / Phase-1-only runs)."""

    name = "null_isl"

    def neighbors(self, sat_id: str, when: datetime) -> Sequence[str]:
        _ = (sat_id, when)
        return ()

    def adjacency(self, when: datetime) -> np.ndarray:
        _ = when
        return np.zeros((0, 0), dtype=bool)


def plus_grid_candidate_pairs(elements: KeplerianBatch) -> list[tuple[int, int]]:
    """Undirected (i, j) index pairs for intra ±1 and inter ±1, same shell."""
    key_to_i: dict[tuple[str, int, int], int] = {}
    for i in range(len(elements)):
        key_to_i[
            (str(elements.shell_id[i]), int(elements.plane[i]), int(elements.slot[i]))
        ] = i
    pairs: set[tuple[int, int]] = set()
    n_planes = elements.n_planes
    n_slots = elements.n_slots
    assert n_planes is not None and n_slots is not None
    for i in range(len(elements)):
        sh = str(elements.shell_id[i])
        p = int(elements.plane[i])
        s = int(elements.slot[i])
        p_mod = int(n_planes[i])
        s_mod = int(n_slots[i])
        cands = (
            (sh, p, (s + 1) % s_mod),
            (sh, p, (s - 1) % s_mod),
            (sh, (p + 1) % p_mod, s),
            (sh, (p - 1) % p_mod, s),
        )
        for key in cands:
            j = key_to_i.get(key)
            if j is None or j == i:
                continue
            a, b = (i, j) if i < j else (j, i)
            pairs.add((a, b))
    return sorted(pairs)


def _filter_feasible(
    r_eci_m: np.ndarray,
    pairs: list[tuple[int, int]],
    cfg: ISLConfig,
) -> list[tuple[int, int, float]]:
    if not pairs:
        return []
    i = np.array([a for a, _ in pairs], dtype=int)
    j = np.array([b for _, b in pairs], dtype=int)
    rng = pairwise_range_m(r_eci_m, i, j)
    keep = rng <= (cfg.max_range_km * 1000.0)
    if cfg.earth_occlusion:
        occ = earth_occludes_segment(r_eci_m[i], r_eci_m[j])
        keep = keep & ~occ
    out: list[tuple[int, int, float]] = []
    for k, (a, b) in enumerate(pairs):
        if keep[k]:
            out.append((a, b, float(rng[k])))
    return out


def _geometric_fill(
    r_eci_m: np.ndarray,
    elements: KeplerianBatch,
    existing: list[tuple[int, int, float]],
    cfg: ISLConfig,
) -> list[tuple[int, int, float]]:
    """Add nearest LOS+range neighbors until each sat reaches ``max_degree``."""
    n = len(elements)
    adj: list[set[int]] = [set() for _ in range(n)]
    edges = list(existing)
    for a, b, _rng in existing:
        adj[a].add(b)
        adj[b].add(a)
    max_m = cfg.max_range_km * 1000.0
    r = np.asarray(r_eci_m, dtype=float).reshape(-1, 3)
    # Pairwise ranges — N is demo-scale (≤ a few hundred)
    diff = r[:, None, :] - r[None, :, :]
    dist = np.linalg.norm(diff, axis=2)
    np.fill_diagonal(dist, np.inf)
    for i in range(n):
        if len(adj[i]) >= cfg.max_degree:
            continue
        order = np.argsort(dist[i])
        for j in order:
            if len(adj[i]) >= cfg.max_degree:
                break
            j = int(j)
            if j in adj[i] or dist[i, j] > max_m:
                continue
            if cfg.earth_occlusion and bool(earth_occludes_segment(r[i], r[j])[0]):
                continue
            a, b = (i, j) if i < j else (j, i)
            if b not in adj[a]:
                adj[a].add(b)
                adj[b].add(a)
                edges.append((a, b, float(dist[i, j])))
    return edges


class PlusGridISL:
    """Working +Grid ISL builder (snapshot-based)."""

    name = "plus_grid"

    def __init__(self, cfg: ISLConfig | None = None) -> None:
        self.cfg = cfg or ISLConfig()
        self._last_neighbors: dict[str, tuple[str, ...]] = {}
        self._last_adj = np.zeros((0, 0), dtype=bool)

    def links_at(
        self,
        elements: KeplerianBatch,
        r_eci_m: np.ndarray,
    ) -> list[ISLEdge]:
        if self.cfg.pattern == "geometric":
            pairs: list[tuple[int, int]] = []
            feasible = _geometric_fill(r_eci_m, elements, [], self.cfg)
        else:
            pairs = plus_grid_candidate_pairs(elements)
            feasible = _filter_feasible(r_eci_m, pairs, self.cfg)
            if self.cfg.fill_geometric:
                feasible = _geometric_fill(r_eci_m, elements, feasible, self.cfg)

        n = len(elements)
        adj = np.zeros((n, n), dtype=bool)
        neighbors: dict[str, list[str]] = {str(s): [] for s in elements.sat_id}
        edges: list[ISLEdge] = []
        seen: set[tuple[str, str]] = set()
        grid = set(pairs)
        for a, b, rng in feasible:
            sa, sb = str(elements.sat_id[a]), str(elements.sat_id[b])
            key = (sa, sb) if sa < sb else (sb, sa)
            if key in seen:
                continue
            seen.add(key)
            adj[a, b] = adj[b, a] = True
            neighbors[sa].append(sb)
            neighbors[sb].append(sa)
            kind = "plus_grid" if (min(a, b), max(a, b)) in grid else "geometric"
            edges.append(ISLEdge(a=sa, b=sb, range_km=rng / 1000.0, kind=kind))
        self._last_neighbors = {k: tuple(v) for k, v in neighbors.items()}
        self._last_adj = adj
        return edges

    def neighbors(self, sat_id: str, when: datetime) -> Sequence[str]:
        _ = when
        return self._last_neighbors.get(sat_id, ())

    def adjacency(self, when: datetime) -> np.ndarray:
        _ = when
        return self._last_adj
