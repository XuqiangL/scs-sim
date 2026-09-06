"""Launcher help stays import-light."""

from __future__ import annotations

from scs_sim.cli import main


def test_cli_help(capsys) -> None:
    assert main(["--help"]) == 0
    out = capsys.readouterr().out
    assert "api" in out and "viz" in out
