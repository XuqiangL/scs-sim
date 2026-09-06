"""CelesTrak fixture parse + one SGP4 step. No network."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pytest

from scs_sim.catalog.align import align_tle_to_walker, propagate_tle_eci_m, write_align_report
from scs_sim.catalog.celestrak import load_tles, resolve_tle_path
from scs_sim.config import load_config
from scs_sim.constants import R_EARTH_M
from scs_sim.ops.tle import tle_checksum

REPO = Path(__file__).resolve().parents[1]
FIXTURE = REPO / "tests" / "fixtures" / "starlink_sample.tle"


def test_fixture_parses_and_sgp4_steps(tmp_path: Path) -> None:
    recs = load_tles(FIXTURE)
    assert 6 <= len(recs) <= 12
    assert all(r.line1.startswith("1 ") and r.line2.startswith("2 ") for r in recs)
    for r in recs:
        assert tle_checksum(r.line1[:68]) == int(r.line1[68])
        assert tle_checksum(r.line2[:68]) == int(r.line2[68])
    when = datetime(2026, 3, 6, 12, 0, tzinfo=timezone.utc)
    r0 = propagate_tle_eci_m(recs, when)
    r1 = propagate_tle_eci_m(recs, datetime(2026, 3, 6, 12, 1, tzinfo=timezone.utc))
    assert r0.shape == (len(recs), 3)
    alt = np.linalg.norm(r0, axis=1) / 1000.0 - R_EARTH_M / 1000.0
    assert np.all((alt > 400.0) & (alt < 700.0))
    assert np.linalg.norm(r1[0] - r0[0]) > 20_000.0

    cfg = load_config(REPO / "configs" / "walker_10k.yaml")
    report = align_tle_to_walker(recs, cfg, source=str(FIXTURE), fetched=False)
    assert report["n_tle"] == len(recs)
    assert report["n_walker_shell"] == 1584
    assert report["sgp4_step_ok"] is True
    assert report["fraction_in_walker_band"] == pytest.approx(1.0)
    assert abs(report["inc_delta_deg"]) < 0.2
    out = write_align_report(tmp_path / "tle_align_report.json", report)
    assert "n_tle" in out.read_text(encoding="utf-8")


def test_resolve_tle_offline_requires_file(tmp_path: Path) -> None:
    missing = tmp_path / "nope.tle"
    with pytest.raises(FileNotFoundError):
        resolve_tle_path(missing, fetch=False)
    p = resolve_tle_path(FIXTURE, fetch=False)
    assert p.is_file()
