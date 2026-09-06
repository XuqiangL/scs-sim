"""Time-varying topology snapshots and JSON/CSV export.

Phase: 2 (network)
Completion: 90%
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from scs_sim.config import GroundStationConfig, GSLConfig, ISLConfig
from scs_sim.network.gsl import ElevationGSL, GSLEdge
from scs_sim.network.isl import ISLEdge, PlusGridISL
from scs_sim.network.routing import RoutingSummary, build_weighted_graph, gs_pair_metrics
from scs_sim.orbit.elements import KeplerianBatch


@dataclass
class TopologySnapshot:
    t_utc: str
    step: int
    n_sats: int
    isl_edges: list[ISLEdge]
    gsl_edges: list[GSLEdge]
    routing: RoutingSummary | None

    def to_json_obj(self) -> dict[str, Any]:
        return {
            "t_utc": self.t_utc,
            "step": self.step,
            "n_sats": self.n_sats,
            "n_isl": len(self.isl_edges),
            "n_gsl": len(self.gsl_edges),
            "isl_edges": [asdict(e) for e in self.isl_edges],
            "gsl_edges": [asdict(e) for e in self.gsl_edges],
            "routing": None
            if self.routing is None
            else {
                "pairs": self.routing.pairs,
                "connected": self.routing.connected,
                "mean_hops": self.routing.mean_hops,
                "mean_stretch": self.routing.mean_stretch,
                "mean_path_km": self.routing.mean_path_km,
                "sample_paths": [
                    {
                        "src": p.src,
                        "dst": p.dst,
                        "hops": p.hops,
                        "path_km": p.path_km,
                        "geodesic_km": p.geodesic_km,
                        "stretch": p.stretch,
                        "path": list(p.path),
                    }
                    for p in self.routing.paths[:12]
                ],
            },
        }


class TopologyBuilder:
    def __init__(
        self,
        isl_cfg: ISLConfig,
        gsl_cfg: GSLConfig,
        stations: tuple[GroundStationConfig, ...],
    ) -> None:
        self.isl = PlusGridISL(isl_cfg)
        self.gsl = ElevationGSL(stations, gsl_cfg)
        self.stations = stations

    def snapshot(
        self,
        elements: KeplerianBatch,
        r_eci_m: Any,
        r_ecef_m: Any,
        *,
        when: datetime,
        step: int,
        route: bool = True,
    ) -> TopologySnapshot:
        isl_edges = self.isl.links_at(elements, r_eci_m)
        gsl_edges = self.gsl.links_at(elements.sat_id, r_ecef_m)
        routing = None
        if route and self.stations:
            adj = build_weighted_graph(
                ((e.a, e.b, e.range_km) for e in isl_edges),
                ((e.gs, e.sat, e.range_km) for e in gsl_edges),
            )
            routing = gs_pair_metrics(self.stations, adj)
        return TopologySnapshot(
            t_utc=when.strftime("%Y-%m-%dT%H:%M:%SZ"),
            step=step,
            n_sats=len(elements),
            isl_edges=isl_edges,
            gsl_edges=gsl_edges,
            routing=routing,
        )


def write_topology_json(path: Path, snapshots: list[TopologySnapshot], meta: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "meta": meta,
        "snapshots": [s.to_json_obj() for s in snapshots],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_topology_edges_csv(path: Path, snapshots: list[TopologySnapshot]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["t_utc", "step", "kind", "src", "dst", "range_km", "elev_deg"])
        for snap in snapshots:
            for e in snap.isl_edges:
                w.writerow([snap.t_utc, snap.step, f"isl_{e.kind}", e.a, e.b, f"{e.range_km:.6f}", ""])
            for e in snap.gsl_edges:
                w.writerow(
                    [snap.t_utc, snap.step, "gsl", e.gs, e.sat, f"{e.range_km:.6f}", f"{e.elev_deg:.3f}"]
                )
