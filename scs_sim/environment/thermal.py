"""Lumped radiative thermal state (Stefan–Boltzmann stub).

Phase: 3 (environment)
Completion: 85%
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

STEFAN_BOLTZMANN = 5.670374419e-8
T_SPACE_K = 3.0


@dataclass(frozen=True)
class ThermalConfig:
    mass_kg: float = 300.0
    cp_j_kg_k: float = 900.0
    area_m2: float = 6.0
    absorptivity: float = 0.65
    emissivity: float = 0.80
    initial_temp_k: float = 290.0
    solar_constant_w_m2: float = 1361.0


class ThermalState:
    """One temperature per sat. ``q_internal_w`` is electronics dissipation."""

    def __init__(self, n: int, cfg: ThermalConfig | None = None) -> None:
        self.cfg = cfg or ThermalConfig()
        self.temp_k = np.full(n, float(self.cfg.initial_temp_k), dtype=float)

    def step(self, sunlight: np.ndarray, q_internal_w: np.ndarray, dt_s: float) -> np.ndarray:
        sun = np.asarray(sunlight, dtype=float).reshape(-1)
        q_int = np.asarray(q_internal_w, dtype=float).reshape(-1)
        cfg = self.cfg
        t = np.maximum(self.temp_k, 50.0)
        q_abs = cfg.absorptivity * cfg.solar_constant_w_m2 * (cfg.area_m2 * 0.25) * sun
        q_rad = cfg.emissivity * STEFAN_BOLTZMANN * cfg.area_m2 * (t**4 - T_SPACE_K**4)
        heat_cap = max(cfg.mass_kg * cfg.cp_j_kg_k, 1.0)
        self.temp_k = np.clip(t + (q_abs + q_int - q_rad) * float(dt_s) / heat_cap, 150.0, 400.0)
        return self.temp_k
