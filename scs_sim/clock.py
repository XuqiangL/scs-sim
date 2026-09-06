"""Discrete simulation clock / time steps.

Phase: 1 (core)
Completion: 90%
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


def ensure_utc(dt: datetime) -> datetime:
    """Return an aware UTC datetime."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@dataclass
class SimClock:
    """Fixed-step discrete clock.

    Hexagonal note: later event-driven clocks (DSNS-style) can implement the
    same ``now`` / ``advance`` surface without changing callers.
    """

    epoch: datetime
    dt_seconds: float
    step: int = 0

    def __post_init__(self) -> None:
        self.epoch = ensure_utc(self.epoch)
        if self.dt_seconds <= 0:
            raise ValueError("dt_seconds must be positive")

    @property
    def now(self) -> datetime:
        return self.epoch + timedelta(seconds=self.elapsed_seconds)

    @property
    def elapsed_seconds(self) -> float:
        return float(self.step) * float(self.dt_seconds)

    def advance(self, n: int = 1) -> datetime:
        if n < 0:
            raise ValueError("cannot advance a negative number of steps")
        self.step += n
        return self.now

    def reset(self) -> None:
        self.step = 0
