"""Local ops REST API (FastAPI TestClient). No network bind."""

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


def test_health_and_cors_preflight(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["completion_pct"] >= 78
    r = client.get("/health", headers={"Origin": "http://localhost:5500"})
    assert r.headers.get("access-control-allow-origin") == "*"
    docs = client.get("/docs")
    assert docs.status_code == 200


def test_load_step_kpi_sats_job(client: TestClient) -> None:
    cfg = REPO / "configs" / "phase6_viz.yaml"
    r = client.post("/config/load", json={"path": str(cfg), "max_sats": 6})
    assert r.status_code == 200, r.text
    st = r.json()
    assert st["loaded"] is True
    assert st["n_sats"] == 6

    r = client.post("/sim/step", json={"n": 2})
    assert r.status_code == 200, r.text
    assert r.json()["step"] == 2

    r = client.get("/sats")
    assert r.status_code == 200
    sats = r.json()["sats"]
    assert len(sats) == 6
    assert {"sat_id", "lat_deg", "lon_deg", "alt_km", "soc", "state"} <= set(sats[0])
    assert 200 < sats[0]["alt_km"] < 2000

    r = client.get(f"/sats/{sats[0]['sat_id']}")
    assert r.status_code == 200
    assert r.json()["sat_id"] == sats[0]["sat_id"]

    r = client.post("/jobs", json={"job_id": "api-job-1", "flops": 1.0e14})
    assert r.status_code == 200
    assert r.json()["status"] == "queued"

    r = client.get("/jobs")
    ids = {j["job_id"] for j in r.json()["jobs"]}
    assert "api-job-1" in ids

    r = client.get("/kpi")
    assert r.status_code == 200
    kpi = r.json()
    assert kpi["n_sats"] == 6
    assert "coverage" in kpi and "fleet_soc" in kpi and "compute" in kpi

    r = client.get("/waves")
    assert r.status_code == 200
    assert r.json()["waves"] == []


def test_step_without_config_is_409(client: TestClient) -> None:
    r = client.post("/sim/step", json={"n": 1})
    assert r.status_code == 409
