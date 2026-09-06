"""CelesTrak catalog ingest (opt-in fetch) and TLE↔Walker alignment."""

from scs_sim.catalog.align import align_tle_to_walker, propagate_tle_eci_m, write_align_report
from scs_sim.catalog.celestrak import (
    CELESTRAK_STARLINK_TLE,
    fetch_starlink_tles,
    load_tles,
    resolve_tle_path,
)

__all__ = [
    "CELESTRAK_STARLINK_TLE",
    "align_tle_to_walker",
    "fetch_starlink_tles",
    "load_tles",
    "propagate_tle_eci_m",
    "resolve_tle_path",
    "write_align_report",
]
