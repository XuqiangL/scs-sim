"""CelesTrak Starlink TLE fetch + local cache (opt-in network).

Default path is a local file. HTTP download runs only when ``fetch=True``
or ``--fetch-tle`` is passed. CI stays offline.
"""

from __future__ import annotations

from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from scs_sim.ops.tle import TleRecord, parse_tle_file, parse_tle_text

CELESTRAK_STARLINK_TLE = (
    "https://celestrak.org/NORAD/elements/gp.php?GROUP=starlink&FORMAT=tle"
)
USER_AGENT = "scs-sim/0.8 (offline-first constellation sim; opt-in catalog fetch)"


def fetch_starlink_tles(
    dest: str | Path,
    *,
    url: str = CELESTRAK_STARLINK_TLE,
    timeout_s: float = 30.0,
) -> Path:
    """Download a CelesTrak GROUP=starlink TLE file. **Network — opt-in only.**"""
    dest_p = Path(dest)
    dest_p.parent.mkdir(parents=True, exist_ok=True)
    req = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(req, timeout=float(timeout_s)) as resp:  # noqa: S310 — operator-opt-in
            raw = resp.read()
    except URLError as exc:
        raise RuntimeError(f"CelesTrak fetch failed ({url}): {exc}") from exc
    text = raw.decode("utf-8", errors="replace")
    if "1 " not in text or "2 " not in text:
        raise RuntimeError("CelesTrak response did not look like a TLE catalog")
    dest_p.write_text(text, encoding="utf-8")
    return dest_p


def resolve_tle_path(
    path: str | Path | None,
    *,
    fetch: bool = False,
    cache_path: str | Path = "out/starlink.tle",
    url: str = CELESTRAK_STARLINK_TLE,
) -> Path:
    """Return a readable TLE path. Fetch only when ``fetch`` is true."""
    if path is not None:
        p = Path(path)
        if p.is_file():
            if fetch:
                fetch_starlink_tles(p, url=url)
            return p
        if fetch:
            return fetch_starlink_tles(p, url=url)
        raise FileNotFoundError(
            f"TLE file not found: {p}. Pass a local path or set catalog.fetch / --fetch-tle."
        )
    cache = Path(cache_path)
    if fetch:
        return fetch_starlink_tles(cache, url=url)
    if cache.is_file():
        return cache
    raise FileNotFoundError(
        "no TLE path given and cache is empty; "
        "use tests/fixtures/starlink_sample.tle or --fetch-tle"
    )


def load_tles(path: str | Path) -> list[TleRecord]:
    return parse_tle_file(path)


def load_tle_text(text: str) -> list[TleRecord]:
    return parse_tle_text(text)
