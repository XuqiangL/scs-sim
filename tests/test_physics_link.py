"""ISL Earth occlusion and GSL elevation-mask accuracy."""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np

from scs_sim.config import GSLConfig, GroundStationConfig, ShellConfig
from scs_sim.constants import R_EARTH_M
from scs_sim.constellation.walker import generate_walker_shell
from scs_sim.network.geometry import earth_occludes_segment
from scs_sim.network.gsl import visible_sats_for_gs
from scs_sim.orbit.frames import ecef_to_geodetic
from scs_sim.orbit.kepler import KeplerJ2Propagator


def test_diametric_leo_sats_occluded_by_earth() -> None:
    r = R_EARTH_M + 550_000.0
    a = np.array([[r, 0.0, 0.0]])
    b = np.array([[-r, 0.0, 0.0]])
    assert bool(earth_occludes_segment(a, b)[0])
    # Neighbors on the same side: short chord stays outside Earth
    c = np.array([[r * np.cos(0.05), r * np.sin(0.05), 0.0]])
    assert not bool(earth_occludes_segment(a, c)[0])


def test_gsl_nadir_passes_farside_fails() -> None:
    epoch = datetime(2026, 9, 6, tzinfo=timezone.utc)
    el = generate_walker_shell(
        ShellConfig(
            id="one",
            altitude_km=550.0,
            inclination_deg=20.0,
            n_planes=1,
            n_sats_per_plane=1,
            phasing_f=0,
        ),
        epoch,
    )
    r_ecef = KeplerJ2Propagator().positions_ecef_m(el, epoch, 0.0)
    lat, lon, _ = ecef_to_geodetic(r_ecef[0])
    nadir = GroundStationConfig(id="nadir", lat_deg=lat, lon_deg=lon, alt_km=0.05)
    far = GroundStationConfig(id="far", lat_deg=-lat, lon_deg=lon + 180.0, alt_km=0.05)
    cfg = GSLConfig(min_elevation_deg=25.0, max_attach=2)
    hit = visible_sats_for_gs(nadir, el.sat_id, r_ecef, cfg)
    miss = visible_sats_for_gs(far, el.sat_id, r_ecef, cfg)
    assert len(hit) == 1
    assert hit[0].elev_deg > 70.0
    assert miss == []
