"""10k generate + propagate. Marked slow; default suite stays short."""

from __future__ import annotations

from pathlib import Path

import pytest

from scs_sim.bench import run_bench

REPO = Path(__file__).resolve().parents[1]


@pytest.mark.slow
def test_bench_n_10008_few_steps(tmp_path: Path) -> None:
    out = tmp_path / "bench10k.json"
    report = run_bench(
        config_path=REPO / "configs" / "walker_10k.yaml",
        n_sats=10_008,
        steps=3,
        dt_seconds=60.0,
        isl_max_sats=0,
        output=out,
    )
    assert report["n_sats"] == 10_008
    assert report["generate_s"] < 30.0
    assert report["propagate_s"] < 30.0
    assert out.is_file()
