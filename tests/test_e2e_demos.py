"""Demo modules + artifact schema E2E (small configs, offline)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scs_sim.bench import run_bench
from scs_sim.catalog.align import align_tle_to_walker, write_align_report
from scs_sim.catalog.celestrak import load_tles
from scs_sim.config import load_config
from scs_sim.demo import run_demo
from scs_sim.demo_ops import run_ops_demo
from scs_sim.demo_viz import run_viz_demo
from scs_sim.twin.compare import compare_tables, write_twin_compare
from scs_sim.twin.io import load_telemetry_csv

REPO = Path(__file__).resolve().parents[1]


def test_demo_phase2_writes_topology() -> None:
    out = run_demo(
        REPO / "configs" / "phase2_network.yaml",
        max_sats=16,
        steps=3,
        output=REPO / "out" / "ephemeris_demo.csv",
        compute=False,
    )
    assert out.is_file() and out.stat().st_size > 0
    topo = REPO / "out" / "topology_demo.json"
    assert topo.is_file()
    payload = json.loads(topo.read_text(encoding="utf-8"))
    assert "snapshots" in payload and payload["snapshots"]
    snap = payload["snapshots"][0]
    assert "isl_edges" in snap and "gsl_edges" in snap


def test_demo_phase4_compute_csv() -> None:
    run_demo(REPO / "configs" / "phase4_compute.yaml", max_sats=16, steps=4)
    sched = REPO / "out" / "compute_schedule.csv"
    assert sched.is_file() and sched.stat().st_size > 0


def test_demo_phase5_ops_timeline() -> None:
    path = run_ops_demo(REPO / "configs" / "phase5_ops.yaml", steps=4)
    assert path.is_file()
    html = REPO / "out" / "ops_timeline.html"
    assert html.is_file() and "SCS-Sim" in html.read_text(encoding="utf-8")


def test_demo_phase6_czml_and_kpi_schema() -> None:
    run_viz_demo(REPO / "configs" / "phase6_viz.yaml", max_sats=12, steps=4)
    czml_path = REPO / "out" / "constellation.czml"
    packets = json.loads(czml_path.read_text(encoding="utf-8"))
    assert isinstance(packets, list) and packets[0]["id"] == "document"
    assert any(str(p.get("id", "")).startswith("sat/") for p in packets)
    kpi = json.loads((REPO / "out" / "kpi_dashboard.json").read_text(encoding="utf-8"))
    for key in ("coverage", "isl", "stretch", "compute", "fleet_soc"):
        assert key in kpi
    html = (REPO / "out" / "viz_globe.html").read_text(encoding="utf-8")
    assert "SCS_CZML" in html
    assert (REPO / "out" / "ground_tracks.svg").stat().st_size > 0


def test_catalog_and_twin_and_bench_artifacts() -> None:
    recs = load_tles(REPO / "tests" / "fixtures" / "starlink_sample.tle")
    cfg = load_config(REPO / "configs" / "walker_10k.yaml")
    report = align_tle_to_walker(recs, cfg, source="fixture", fetched=False)
    write_align_report(REPO / "out" / "tle_align_report.json", report)
    assert report["sgp4_step_ok"]
    sim = load_telemetry_csv(REPO / "tests" / "fixtures" / "sim_state_sample.csv")
    tel = load_telemetry_csv(REPO / "tests" / "fixtures" / "telemetry_sample.csv")
    twin = compare_tables(sim, tel)
    write_twin_compare(REPO / "out" / "twin_compare.json", twin)
    assert twin["n_matched"] == 4
    assert twin["rmse_position_km"] == twin["rmse_position_km"]
    bench = run_bench(
        config_path=REPO / "configs" / "walker_10k.yaml",
        n_sats=48,
        steps=2,
        dt_seconds=60.0,
        isl_max_sats=24,
        output=REPO / "out" / "bench.json",
    )
    assert bench["n_sats"] == 48


def test_run_all_demos_equivalent_exit_codes() -> None:
    """Same sequence as scripts/run_all_demos.bat, without reinstalling."""
    cmds = [
        [
            sys.executable,
            "-m",
            "scs_sim.demo",
            "--config",
            "configs/walker_10k.yaml",
            "--max-sats",
            "16",
            "--steps",
            "3",
            "--no-compute",
            "--no-network",
        ],
        [
            sys.executable,
            "-m",
            "scs_sim.demo",
            "--config",
            "configs/phase2_network.yaml",
            "--max-sats",
            "16",
            "--steps",
            "3",
            "--no-compute",
        ],
        [
            sys.executable,
            "-m",
            "scs_sim.catalog",
            "--tle",
            "tests/fixtures/starlink_sample.tle",
        ],
        [
            sys.executable,
            "-m",
            "scs_sim.bench",
            "--n-sats",
            "32",
            "--steps",
            "2",
            "--isl-max-sats",
            "16",
        ],
    ]
    codes = []
    for cmd in cmds:
        proc = subprocess.run(cmd, cwd=REPO, check=False, capture_output=True, text=True)
        codes.append({"cmd": " ".join(cmd[2:]), "returncode": proc.returncode})
        assert proc.returncode == 0, proc.stderr[-2000:]
    (REPO / "out").mkdir(parents=True, exist_ok=True)
    (REPO / "out" / "e2e_demo_codes.json").write_text(json.dumps(codes, indent=2), encoding="utf-8")
