"""Runtime fleet / per-sat override API and control UI."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from scs_sim.api.app import create_app
from scs_sim.api.session import SimSession

REPO = Path(__file__).resolve().parents[1]
CFG = REPO / "configs" / "phase6_viz.yaml"


@pytest.fixture()
def client(tmp_path, monkeypatch) -> TestClient:
    sess = SimSession()
    sess.overrides_path = tmp_path / "overrides.json"
    with TestClient(create_app(sess)) as c:
        yield c


def _load(client: TestClient, n: int = 8) -> dict:
    r = client.post("/config/load", json={"path": str(CFG), "max_sats": n})
    assert r.status_code == 200, r.text
    return r.json()


def test_ui_and_control_pages(client: TestClient) -> None:
    for path in ("/ui", "/control"):
        r = client.get(path)
        assert r.status_code == 200, path
        assert "text/html" in r.headers.get("content-type", "")
        assert "星座控制台" in r.text
        assert "Fleet" in r.text
        assert "sat_id" in r.text
    root = client.get("/").json()
    assert root["ui"] == "/ui"
    assert root["control"] == "/control"


def test_fleet_override_changes_running_session(client: TestClient) -> None:
    _load(client, 6)
    r = client.post(
        "/control/fleet",
        json={
            "dt_seconds": 45.0,
            "isl_max_range_km": 3200.0,
            "gsl_min_elevation_deg": 12.0,
            "solar_w": 2200.0,
            "battery_capacity_wh": 90.0,
            "apply_drag": True,
            "atmosphere_scale": 2.5,
            "eclipse": False,
            "compute_flops": 5.0e13,
            "idle_w": 70.0,
            "busy_w": 300.0,
        },
    )
    assert r.status_code == 200, r.text
    fleet = r.json()["fleet"]
    assert fleet["dt_seconds"] == 45.0
    assert fleet["isl_max_range_km"] == 3200.0
    assert fleet["gsl_min_elevation_deg"] == 12.0
    assert fleet["battery_capacity_wh"] == 90.0
    assert fleet["apply_drag"] is True
    assert fleet["atmosphere_scale"] == 2.5
    assert fleet["eclipse"] is False
    assert fleet["compute_flops"] == 5.0e13
    assert fleet["idle_w"] == 70.0
    assert fleet["busy_w"] == 300.0
    assert abs(fleet["solar_w"] - 2200.0) < 1e-6

    st = client.get("/sim/status").json()
    assert st["dt_seconds"] == 45.0

    r = client.post("/sim/step", json={"n": 1})
    assert r.status_code == 200
    live = client.get("/control/state").json()
    assert live["fleet"]["isl_max_range_km"] == 3200.0
    assert live["step"] == 1
    # Null eclipse → nobody in shadow
    assert live["fleet_live"]["eclipse_pct"] == 0.0


def test_sat_override_and_reset(client: TestClient, tmp_path: Path) -> None:
    _load(client, 6)
    sid = client.get("/sats").json()["sats"][0]["sat_id"]
    before = client.get(f"/sats/{sid}").json()
    r = client.post(
        f"/control/sat/{sid}",
        json={
            "a_km": 7200.0,
            "e": 0.012,
            "i_deg": 61.0,
            "raan_deg": 44.0,
            "soc": 0.33,
            "power_draw_w": 180.0,
            "flops": 9.0e13,
            "state": "commissioning",
        },
    )
    assert r.status_code == 200, r.text
    sel = r.json()["selected"]
    assert sel["sat_id"] == sid
    assert abs(sel["a_km"] - 7200.0) < 1e-6
    assert abs(sel["e"] - 0.012) < 1e-9
    assert abs(sel["i_deg"] - 61.0) < 1e-6
    assert abs(sel["raan_deg"] - 44.0) < 1e-6
    assert abs(sel["soc"] - 0.33) < 1e-9
    assert sel["power_draw_w"] == 180.0
    assert sel["flops"] == 9.0e13
    assert sel["state"] == "commissioning"
    assert sel["overridden"] is True
    assert before["a_km"] != sel["a_km"]

    ov = client.app.state.session.overrides_path
    assert ov.is_file()
    text = ov.read_text(encoding="utf-8")
    assert sid in text
    assert "7200" in text

    r = client.post(f"/control/sat/{sid}/reset")
    assert r.status_code == 200
    reset = r.json()["selected"]
    assert abs(reset["a_km"] - before["a_km"]) < 1e-6
    assert reset["overridden"] is False
    assert reset["state"] == "operational"


def test_override_requires_session(client: TestClient) -> None:
    r = client.post("/control/fleet", json={"dt_seconds": 30})
    assert r.status_code == 409
    r = client.post("/control/sat/nope", json={"soc": 0.5})
    assert r.status_code == 409
    _load(client, 4)
    r = client.post("/control/sat/missing-sat", json={"soc": 0.5})
    assert r.status_code == 404


def test_reload_and_kpi_export(client: TestClient, tmp_path: Path) -> None:
    _load(client, 6)
    client.post("/control/fleet", json={"dt_seconds": 33})
    assert client.get("/sim/status").json()["dt_seconds"] == 33
    r = client.post("/config/reload")
    assert r.status_code == 200
    assert client.get("/control/state").json()["fleet"]["dt_seconds"] == 90.0

    out = tmp_path / "kpi.json"
    r = client.post("/kpi/export", json={"path": str(out)})
    assert r.status_code == 200
    assert Path(r.json()["wrote"]) == out
    assert out.is_file()
    assert "fleet_soc" in r.json()["kpi"]
