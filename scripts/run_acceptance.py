"""Run the full acceptance campaign and write TEST_REPORT.md + out/test_report.json."""

from __future__ import annotations

import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _run_pytest(args: list[str], junit: Path) -> int:
    junit.parent.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, "-m", "pytest", "-q", "--tb=short", f"--junitxml={junit}", *args]
    print("+", " ".join(cmd))
    return subprocess.call(cmd, cwd=REPO)


def _parse_junit(path: Path) -> dict:
    if not path.is_file():
        return {"tests": 0, "failures": 0, "errors": 0, "skipped": 0, "cases": []}
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
    tests = failures = errors = skipped = 0
    cases = []
    for suite in suites:
        tests += int(suite.attrib.get("tests", 0))
        failures += int(suite.attrib.get("failures", 0))
        errors += int(suite.attrib.get("errors", 0))
        skipped += int(suite.attrib.get("skipped", 0))
        for case in suite.findall("testcase"):
            status = "passed"
            if case.find("failure") is not None:
                status = "failed"
            elif case.find("error") is not None:
                status = "error"
            elif case.find("skipped") is not None:
                status = "skipped"
            cases.append(
                {
                    "name": case.attrib.get("name"),
                    "classname": case.attrib.get("classname"),
                    "status": status,
                    "time": float(case.attrib.get("time", 0.0)),
                }
            )
    passed = tests - failures - errors - skipped
    return {
        "tests": tests,
        "passed": passed,
        "failures": failures,
        "errors": errors,
        "skipped": skipped,
        "cases": cases,
    }


def _merge(a: dict, b: dict) -> dict:
    return {
        "tests": a["tests"] + b["tests"],
        "passed": a["passed"] + b["passed"],
        "failures": a["failures"] + b["failures"],
        "errors": a["errors"] + b["errors"],
        "skipped": a["skipped"] + b["skipped"],
        "cases": a["cases"] + b["cases"],
    }


def main() -> int:
    fast_xml = REPO / "out" / "pytest_fast.xml"
    slow_xml = REPO / "out" / "pytest_slow.xml"
    rc1 = _run_pytest(["-m", "not slow"], fast_xml)
    rc2 = _run_pytest(["-m", "slow"], slow_xml)
    fast = _parse_junit(fast_xml)
    slow = _parse_junit(slow_xml)
    tot = _merge(fast, slow)
    metrics = {}
    mp = REPO / "out" / "physics_metrics.json"
    if mp.is_file():
        metrics = json.loads(mp.read_text(encoding="utf-8"))
    failed = [c for c in tot["cases"] if c["status"] in {"failed", "error"}]
    new_modules = [
        "tests/test_physics_orbit.py",
        "tests/test_physics_env.py",
        "tests/test_physics_link.py",
        "tests/test_physics_walker.py",
        "tests/test_e2e_api.py",
        "tests/test_e2e_demos.py",
        "tests/test_property_chaos.py",
        "tests/test_bench_slow.py",
    ]
    report = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "python": sys.version.split()[0],
        "fast": {k: fast[k] for k in ("tests", "passed", "failures", "errors", "skipped")},
        "slow": {k: slow[k] for k in ("tests", "passed", "failures", "errors", "skipped")},
        "total": {k: tot[k] for k in ("tests", "passed", "failures", "errors", "skipped")},
        "exit_codes": {"not_slow": rc1, "slow": rc2},
        "failed_cases": failed,
        "new_modules": new_modules,
        "physics_metrics": metrics,
        "known_gaps": [
            "Orekit propagate is a stub (NotImplementedError) — not a numeric gold standard.",
            "Signed MSI / production auth / paid Cesium ion are out of scope.",
            "SGP4 vs Kepler+J2 is a short-arc LEO-radius check, not a bit-identical ephemeris match.",
            "CelesTrak HTTP fetch is opt-in and is not exercised in this campaign.",
        ],
        "windows_acceptance": tot["failures"] == 0 and tot["errors"] == 0,
    }
    (REPO / "out").mkdir(parents=True, exist_ok=True)
    (REPO / "out" / "test_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    md = f"""# Test report

Generated **{report['generated_utc']}** (Python {report['python']}).

## Counts

| Pass | Fail | Error | Skip | Total |
|-----:|-----:|------:|-----:|------:|
| {tot['passed']} | {tot['failures']} | {tot['errors']} | {tot['skipped']} | {tot['tests']} |

Fast (`-m "not slow"`): {fast['passed']} passed / {fast['failures']} failed / {fast['skipped']} skipped.  
Slow (`-m slow`): {slow['passed']} passed / {slow['failures']} failed / {slow['skipped']} skipped.

Exit codes: not-slow={rc1}, slow={rc2}.

## New modules this campaign

{chr(10).join(f"- `{n}`" for n in new_modules)}

## Physics measured vs limits

| Metric | Value | Limit / note |
|--------|-------|----------------|
| Kepler period relative error | {metrics.get('period_rel_error', 'n/a')} | ≤ {metrics.get('period_rel_limit', 1e-12)} |
| J2 RAAN rate | {metrics.get('j2_raan_deg_per_day', 'n/a')} deg/day | negative; ~2–8 deg/day at 550 km / 53° |
| Radius relative limit | — | ≤ {metrics.get('radius_rel_limit', 1e-4)} |
| ρ(550 km) | {metrics.get('rho_550_kg_m3', 'n/a')} kg/m³ | > ρ(800 km) > 0 |
| ρ(800 km) | {metrics.get('rho_800_kg_m3', 'n/a')} kg/m³ | positive |

## E2E

- FastAPI `/docs`, `/openapi.json`, load → step → sats → job → KPI → twin: covered in `test_e2e_api.py`.
- Demos phase2/4/5/6 + catalog + bench + `run_all_demos` equivalent: `test_e2e_demos.py`.
- CZML document packet, KPI keys, topology snapshots validated.

## Known gaps

{chr(10).join(f"- {g}" for g in report['known_gaps'])}

## Failed cases

{("none" if not failed else chr(10).join(f"- `{c['classname']}::{c['name']}`" for c in failed))}

## Windows acceptance

{"**Ready** — all non-skipped tests passed. Run `scripts/run_all_demos.bat` then `py -3 -m pytest`." if report["windows_acceptance"] else "**Not ready** — see failed cases."}
"""
    (REPO / "docs" / "TEST_REPORT.md").write_text(md, encoding="utf-8")
    print(f"wrote {REPO / 'docs' / 'TEST_REPORT.md'}")
    print(f"wrote {REPO / 'out' / 'test_report.json'}")
    print(
        f"total {tot['passed']} passed, {tot['failures']} failed, "
        f"{tot['errors']} errors, {tot['skipped']} skipped / {tot['tests']}"
    )
    return 0 if (rc1 == 0 and rc2 == 0) else 1


if __name__ == "__main__":
    raise SystemExit(main())
