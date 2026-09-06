"""Solar generation + battery state of charge.

Phase: 3 (environment)
Completion: 90%

Sunlight fraction drives panel current; eclipse is a drain on the bus load.
SoC is clipped to [0, 1]. Clean-room stub, not a vendor BMS model.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class PowerConfig:
    panel_area_m2: float = 8.0
    panel_efficiency: float = 0.28
    solar_constant_w_m2: float = 1361.0
    battery_capacity_wh: float = 200.0
    initial_soc: float = 0.75
    charge_efficiency: float = 0.95
    platform_idle_w: float = 50.0
    max_charge_w: float = 600.0


class BatteryBank:
    """Per-sat SoC array. ``step`` returns generation and updated SoC."""

    def __init__(self, n: int, cfg: PowerConfig | None = None) -> None:
        self.cfg = cfg or PowerConfig()
        if not (0.0 <= self.cfg.initial_soc <= 1.0):
            raise ValueError("initial_soc must be in [0, 1]")
        self.soc = np.full(n, float(self.cfg.initial_soc), dtype=float)
        self.last_gen_w = np.zeros(n, dtype=float)
        self.last_load_w = np.zeros(n, dtype=float)

    @property
    def capacity_j(self) -> float:
        return float(self.cfg.battery_capacity_wh) * 3600.0

    def generation_w(self, sunlight: np.ndarray) -> np.ndarray:
        raw = (
            np.asarray(sunlight, dtype=float)
            * self.cfg.panel_area_m2
            * self.cfg.panel_efficiency
            * self.cfg.solar_constant_w_m2
        )
        return np.minimum(raw, self.cfg.max_charge_w)

    def step(self, sunlight: np.ndarray, load_w: np.ndarray, dt_s: float) -> np.ndarray:
        """Advance SoC. ``load_w`` is bus consumption (platform + payload)."""
        sun = np.asarray(sunlight, dtype=float).reshape(-1)
        load = np.maximum(np.asarray(load_w, dtype=float).reshape(-1), 0.0)
        gen = self.generation_w(sun)
        surplus = gen - load
        # Charge only the surplus, with charge efficiency; discharge at full load deficit.
        d_e = np.where(surplus >= 0.0, surplus * self.cfg.charge_efficiency, surplus) * float(dt_s)
        self.soc = np.clip(self.soc + d_e / max(self.capacity_j, 1.0), 0.0, 1.0)
        self.last_gen_w = gen
        self.last_load_w = load
        return self.soc
