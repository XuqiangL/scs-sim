"""Interactive FastAPI E2E: OpenAPI, load, step, sats, job, KPI, twin."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from scs_sim.api.app import create_app
from scs_sim.api.session import SimSession

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture()
def client() -> TestClient:
    with TestClient(create_app(SimSession())) as c:
        yield c


def test_openapi_schema_lists_ops_paths(client: TestClient) -> None:
    r = client.get("/openapi.json")
    assert r.status_code == 200
    spec = r.json()
    paths = spec.get("paths") or {}
    for p in ("/docs", "/health", "/config/load", "/sim/step", "/sats", "/jobs", "/kpi", "/twin/compare"):
        if p == "/docs":
            docs = client.get("/docs")
            assert docs.status_code == 200
            continue
        assert p in paths, p


def test_api_session_flow_and_twin(client: TestClient) -> None:
    cfg = REPO / "configs" / "phase6_viz.yaml"
    r = client.post("/config/load", json={"path": str(cfg), "max_sats": 8})
    assert r.status_code == 200
    assert r.json()["loaded"] is True
    r = client.post("/sim/step", json={"n": 2})
    assert r.status_code == 200
    r = client.get("/sats")
    assert r.status_code == 200
    body = r.json()
    assert body["n"] == 8
    assert {"sat_id", "lat_deg", "lon_deg", "alt_km", "soc", "state"} <= set(body["sats"][0])
    r = client.post("/jobs", json={"job_id": "e2e-job", "flops": 2.0e14, "dest_gs": None})
    assert r.status_code == 200
    r = client.get("/kpi")
    assert r.status_code == 200
    kpi = r.json()
    for key in ("coverage", "isl", "stretch", "compute", "fleet_soc", "n_sats"):
        assert key in kpi
    tel = REPO / "tests" / "fixtures" / "telemetry_sample.csv"
    sim = REPO / "tests" / "fixtures" / "sim_state_sample.csv"
    r = client.post(
        "/twin/compare",
        json={
            "telemetry_path": str(tel),
            "sim_path": str(sim),
            "output": str(REPO / "out" / "twin_compare.json"),
        },
    )
    assert r.status_code == 200
    report = r.json()
    assert report["n_matched"] >= 1
    assert report["rmse_position_km"] == report["rmse_position_km"]  # finite
    assert (REPO / "out" / "twin_compare.json").is_file()
