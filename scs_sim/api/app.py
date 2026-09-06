"""Local ops REST API (FastAPI). CORS open for a LAN dashboard. No auth."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from scs_sim import __completion_pct__, __phase__, __version__
from scs_sim.api.session import SimSession
from scs_sim.twin.compare import compare_to_propagator, compare_tables, write_twin_compare
from scs_sim.twin.io import load_telemetry_csv


def _require_fastapi():
    try:
        from fastapi import FastAPI, HTTPException
        from fastapi.middleware.cors import CORSMiddleware
        from pydantic import BaseModel, Field
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            'FastAPI extra missing. Install with: pip install -e ".[api]"'
        ) from exc
    return FastAPI, HTTPException, CORSMiddleware, BaseModel, Field


FastAPI, HTTPException, CORSMiddleware, BaseModel, Field = _require_fastapi()


class LoadBody(BaseModel):
    path: str = Field(..., description="YAML config path")
    max_sats: int | None = Field(None, description="Optional Walker subsample")


class StepBody(BaseModel):
    n: int = Field(1, ge=1, le=500, description="Number of discrete steps")


class JobBody(BaseModel):
    job_id: str
    flops: float = Field(..., gt=0)
    dest_gs: str | None = None


class TwinBody(BaseModel):
    telemetry_path: str
    sim_path: str | None = Field(None, description="Optional sim-state CSV (same schema)")
    output: str = "out/twin_compare.json"


def create_app(session: SimSession | None = None) -> Any:
    sess = session or SimSession()
    app = FastAPI(
        title="SCS-Sim Ops API",
        version=__version__,
        description=(
            "Local constellation ops console. CORS is open for a same-machine dashboard. "
            "Not a production service — no auth, no TLS."
        ),
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def _http(err: Exception, code: int = 400):
        raise HTTPException(status_code=code, detail=str(err)) from err

    @app.get("/", include_in_schema=False)
    def root() -> dict[str, Any]:
        return {
            "name": "SCS-Sim Ops API",
            "docs": "/docs",
            "health": "/health",
            "version": __version__,
            "completion_pct": __completion_pct__,
        }

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {
            "ok": True,
            "version": __version__,
            "phase": __phase__,
            "completion_pct": __completion_pct__,
        }

    @app.get("/version")
    def version() -> dict[str, Any]:
        return health()

    @app.post("/config/load")
    def load_cfg(body: LoadBody) -> dict[str, Any]:
        try:
            return sess.load(body.path, max_sats=body.max_sats)
        except FileNotFoundError as exc:
            _http(exc, 404)
        except Exception as exc:
            _http(exc, 400)
        return {}

    @app.get("/config")
    def get_cfg() -> dict[str, Any]:
        try:
            return sess.status()
        except RuntimeError as exc:
            _http(exc, 409)
        return {}

    @app.post("/sim/step")
    def sim_step(body: StepBody) -> dict[str, Any]:
        try:
            return sess.step(body.n)
        except RuntimeError as exc:
            _http(exc, 409)
        except Exception as exc:
            _http(exc, 400)
        return {}

    @app.get("/sim/status")
    def sim_status() -> dict[str, Any]:
        return sess.status()

    @app.get("/waves")
    def waves() -> dict[str, Any]:
        try:
            sess._require()
        except RuntimeError as exc:
            _http(exc, 409)
        return sess.waves()

    @app.get("/sats")
    def sats(limit: int | None = None) -> dict[str, Any]:
        try:
            rows = sess.sat_states(limit=limit)
        except RuntimeError as exc:
            _http(exc, 409)
        return {"n": len(rows), "sats": rows}

    @app.get("/sats/{sat_id}")
    def sat_one(sat_id: str) -> dict[str, Any]:
        try:
            rows = sess.sat_states()
        except RuntimeError as exc:
            _http(exc, 409)
        for row in rows:
            if row["sat_id"] == sat_id:
                return row
        _http(KeyError(f"unknown sat {sat_id}"), 404)
        return {}

    @app.get("/kpi")
    def kpi() -> dict[str, Any]:
        disk = Path("out/kpi_dashboard.json")
        try:
            return sess.kpi()
        except RuntimeError:
            if disk.is_file():
                import json

                return json.loads(disk.read_text(encoding="utf-8"))
            _http(RuntimeError("no session and no out/kpi_dashboard.json"), 409)
        return {}

    @app.get("/jobs")
    def jobs() -> dict[str, Any]:
        try:
            sess._require()
        except RuntimeError as exc:
            _http(exc, 409)
        return {"jobs": sess.list_jobs()}

    @app.post("/jobs")
    def submit_job(body: JobBody) -> dict[str, Any]:
        try:
            return sess.submit_job(body.job_id, body.flops, body.dest_gs)
        except RuntimeError as exc:
            _http(exc, 409)
        except ValueError as exc:
            _http(exc, 400)
        return {}

    @app.post("/twin/compare")
    def twin_compare(body: TwinBody) -> dict[str, Any]:
        tel_p = Path(body.telemetry_path)
        if not tel_p.is_file():
            _http(FileNotFoundError(f"telemetry not found: {tel_p}"), 404)
        tel = load_telemetry_csv(tel_p)
        if body.sim_path:
            sim_p = Path(body.sim_path)
            if not sim_p.is_file():
                _http(FileNotFoundError(f"sim CSV not found: {sim_p}"), 404)
            report = compare_tables(load_telemetry_csv(sim_p), tel)
            report["mode"] = "tables"
        else:
            try:
                sess._require()
            except RuntimeError as exc:
                _http(exc, 409)
            assert sess.elements is not None and sess.prop is not None and sess.cfg is not None
            states = sess._states()
            soc = {}
            if sess.batteries is not None:
                soc = {sid: float(sess.batteries.soc[i]) for i, sid in enumerate(sess._sat_ids())}
            report = compare_to_propagator(
                tel,
                sess.elements,
                sess.prop,
                sess.cfg.epoch,
                soc_by_sat=soc,
                state_by_sat=states,
            )
        report["telemetry"] = str(tel_p)
        write_twin_compare(body.output, report)
        report["wrote"] = body.output
        return report

    app.state.session = sess
    return app


app = None


def get_app() -> Any:
    global app
    if app is None:
        app = create_app()
    return app
