"""Micro-bench (N<=64) writes out/bench.json. No 10k in CI."""

from __future__ import annotations

import json
from pathlib import Path

from scs_sim.bench import run_bench

REPO = Path(__file__).resolve().parents[1]


def test_micro_bench_writes_json(tmp_path: Path) -> None:
    out = tmp_path / "bench.json"
    report = run_bench(
        config_path=REPO / "configs" / "walker_10k.yaml",
        n_sats=64,
        steps=2,
        dt_seconds=60.0,
        isl_max_sats=32,
        output=out,
    )
    assert out.is_file()
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["n_sats"] == 64
    assert loaded["steps"] == 2
    assert loaded["generate_s"] >= 0.0
    assert loaded["propagate_s"] >= 0.0
    assert loaded["isl_n_sats"] == 32
    assert loaded["isl_edges"] >= 0
    assert report["propagate_sats_per_s"] > 0
