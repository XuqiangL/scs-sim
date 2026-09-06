"""SAA-band radiation heuristic + dose accumulator.

Phase: 3 (environment)
Completion: 80%

Not AP8/AE8. A Gaussian blob over the South Atlantic Anomaly plus a weak
high-latitude horn term. Good enough to drive a non-zero dose column.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

import numpy as np


class RadiationPort(Protocol):
    name: str

    def proton_flux_cm2_s(
        self,
        r_ecef_m: np.ndarray,
        epoch: datetime,
    ) -> np.ndarray:
        """Integral proton flux, shape (N,)."""


class NullRadiation:
    """Vacuum / no trapped particles (kept for A/B tests)."""

    name = "null_radiation"

    def proton_flux_cm2_s(self, r_ecef_m: np.ndarray, epoch: datetime) -> np.ndarray:
        _ = epoch
        n = int(np.asarray(r_ecef_m).reshape(-1, 3).shape[0])
        return np.zeros(n, dtype=float)


class SAARadiation:
    """South Atlantic Anomaly heuristic in geocentric lat/lon."""

    name = "saa_heuristic"

    def __init__(
        self,
        peak_flux_cm2_s: float = 2.0e3,
        lat0_deg: float = -25.0,
        lon0_deg: float = -50.0,
        lat_sigma_deg: float = 14.0,
        lon_sigma_deg: float = 32.0,
        horn_flux_cm2_s: float = 80.0,
    ) -> None:
        self.peak_flux_cm2_s = peak_flux_cm2_s
        self.lat0_deg = lat0_deg
        self.lon0_deg = lon0_deg
        self.lat_sigma_deg = lat_sigma_deg
        self.lon_sigma_deg = lon_sigma_deg
        self.horn_flux_cm2_s = horn_flux_cm2_s

    def proton_flux_cm2_s(self, r_ecef_m: np.ndarray, epoch: datetime) -> np.ndarray:
        _ = epoch
        r = np.asarray(r_ecef_m, dtype=float).reshape(-1, 3)
        nrm = np.linalg.norm(r, axis=1)
        nrm = np.maximum(nrm, 1.0)
        lat = np.rad2deg(np.arcsin(np.clip(r[:, 2] / nrm, -1.0, 1.0)))
        lon = np.rad2deg(np.arctan2(r[:, 1], r[:, 0]))
        dlat = (lat - self.lat0_deg) / self.lat_sigma_deg
        dlon = _wrap_lon_deg(lon - self.lon0_deg) / self.lon_sigma_deg
        saa = self.peak_flux_cm2_s * np.exp(-(dlat * dlat + dlon * dlon))
        horns = self.horn_flux_cm2_s * np.clip((np.abs(lat) - 50.0) / 40.0, 0.0, 1.0)
        return saa + horns


class DoseAccumulator:
    """Running fluence: dose += flux * dt (protons / cm²)."""

    def __init__(self, n: int) -> None:
        self.dose_cm2 = np.zeros(n, dtype=float)

    def step(self, flux_cm2_s: np.ndarray, dt_s: float) -> np.ndarray:
        self.dose_cm2 = self.dose_cm2 + np.asarray(flux_cm2_s, dtype=float) * float(dt_s)
        return self.dose_cm2


def make_radiation(name: str, *, peak_flux_cm2_s: float = 2.0e3) -> RadiationPort:
    key = (name or "saa_heuristic").strip().lower()
    if key in {"null", "none", "off"}:
        return NullRadiation()
    if key in {"saa", "saa_heuristic", "heuristic"}:
        return SAARadiation(peak_flux_cm2_s=peak_flux_cm2_s)
    raise ValueError(f"unknown radiation model {name!r}")


def _wrap_lon_deg(d: np.ndarray) -> np.ndarray:
    return ((d + 180.0) % 360.0) - 180.0
