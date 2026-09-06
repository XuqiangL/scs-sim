"""CelesTrak-style TLE ingest (optional alignment hook).

Phase: 5 (ops)
Completion: 85%

If ``deployment.tle_path`` is set, Two-Line Element sets replace the synthetic
Walker batch. Real Starlink GP / TLE files from CelesTrak
(https://celestrak.org/NORAD/elements/gp.php?GROUP=starlink&FORMAT=tle)
can be dropped in later without changing the propagator port: parse here,
then feed ``KeplerianBatch`` (or the SGP4 adapter) as today.

Does not download catalogs. Offline fixture or operator-provided file only.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sgp4.api import Satrec

from scs_sim.constants import MU_EARTH_M3_S2, R_EARTH_M
from scs_sim.orbit.elements import KeplerianBatch


@dataclass(frozen=True)
class TleRecord:
    name: str
    line1: str
    line2: str
    satnum: int


def tle_checksum(line: str) -> int:
    """NORAD checksum: digits sum + 1 per minus, modulo 10."""
    total = 0
    for ch in line[:68]:
        if ch.isdigit():
            total += int(ch)
        elif ch == "-":
            total += 1
    return total % 10


def parse_tle_text(text: str) -> list[TleRecord]:
    """Parse 2-line or 3-line (name + L1 + L2) CelesTrak blocks."""
    lines = [ln.rstrip("\n") for ln in text.splitlines() if ln.strip()]
    out: list[TleRecord] = []
    i = 0
    while i < len(lines):
        name = "UNKNOWN"
        if not lines[i].startswith("1 "):
            name = lines[i].strip()
            i += 1
        if i + 1 >= len(lines):
            break
        l1, l2 = lines[i].strip(), lines[i + 1].strip()
        if not (l1.startswith("1 ") and l2.startswith("2 ")):
            i += 1
            continue
        try:
            satnum = int(l1[2:7])
        except ValueError:
            satnum = 0
        out.append(TleRecord(name=name, line1=l1, line2=l2, satnum=satnum))
        i += 2
    return out


def parse_tle_file(path: str | Path) -> list[TleRecord]:
    return parse_tle_text(Path(path).read_text(encoding="utf-8"))


def tle_to_elements(records: list[TleRecord], epoch: datetime) -> KeplerianBatch:
    """Map TLE mean elements onto a KeplerianBatch (SGP4 mean motion → a)."""
    n = len(records)
    if n == 0:
        raise ValueError("no TLE records")
    sat_id = np.empty(n, dtype=object)
    a_m = np.zeros(n)
    e = np.zeros(n)
    i_rad = np.zeros(n)
    raan = np.zeros(n)
    argp = np.zeros(n)
    m = np.zeros(n)
    for k, rec in enumerate(records):
        sat = Satrec.twoline2rv(rec.line1, rec.line2)
        if sat.error != 0:
            raise ValueError(f"SGP4 rejected TLE {rec.name}: error {sat.error}")
        sat_id[k] = rec.name.replace(" ", "-") or f"tle-{rec.satnum:05d}"
        n_rad_s = float(sat.no_kozai) / 60.0  # kozai mean motion rad/min
        a_m[k] = (MU_EARTH_M3_S2 / n_rad_s**2) ** (1.0 / 3.0)
        e[k] = float(sat.ecco)
        i_rad[k] = float(sat.inclo)
        raan[k] = float(sat.nodeo)
        argp[k] = float(sat.argpo)
        m[k] = float(sat.mo)
    shell = np.full(n, "tle", dtype=object)
    return KeplerianBatch(
        sat_id=sat_id,
        shell_id=shell,
        plane=np.zeros(n, dtype=np.int32),
        slot=np.arange(n, dtype=np.int32),
        a_m=a_m,
        e=e,
        i_rad=i_rad,
        raan_rad=raan,
        argp_rad=argp,
        m_rad=m,
        epoch=epoch if epoch.tzinfo else epoch.replace(tzinfo=timezone.utc),
        n_planes=np.ones(n, dtype=np.int32),
        n_slots=np.full(n, n, dtype=np.int32),
    )


def format_tle_line(body68: str) -> str:
    """Pad/truncate to 68 chars and append checksum."""
    body = f"{body68:<68}"[:68]
    return body + str(tle_checksum(body))
