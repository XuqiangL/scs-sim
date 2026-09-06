"""GPU-accelerated Kepler + J2 propagator (PyTorch CUDA when available).

Phase: vNext GPU
Completion: 94%

Optional runtime dependency: torch (CUDA). Not required for packaging.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import numpy as np

from scs_sim.constants import J2, MU_EARTH_M3_S2, R_EARTH_M
from scs_sim.orbit.elements import KeplerianBatch
from scs_sim.orbit.frames import eci_to_ecef
from scs_sim.orbit.kepler import KeplerJ2Propagator

_torch = None
_device = None


def gpu_backend_info() -> dict[str, Any]:
    info: dict[str, Any] = {
        "requested": "kepler_j2_gpu",
        "torch": False,
        "cuda": False,
        "device": "cpu",
        "name": None,
    }
    try:
        import torch

        info["torch"] = True
        info["torch_version"] = torch.__version__
        if torch.cuda.is_available():
            info["cuda"] = True
            info["device"] = "cuda:0"
            info["name"] = torch.cuda.get_device_name(0)
            info["capability"] = ".".join(str(x) for x in torch.cuda.get_device_capability(0))
        else:
            info["device"] = "cpu"
    except Exception as exc:  # noqa: BLE001
        info["error"] = str(exc)
    return info


def _get_torch():
    global _torch, _device
    if _torch is not None:
        return _torch, _device
    import torch

    _torch = torch
    _device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return _torch, _device


def _t(arr, torch, device, dtype=None):
    dt = dtype or torch.float64
    return torch.as_tensor(np.asarray(arr), dtype=dt, device=device)


def _j2_rates_torch(a_m, e, i_rad, torch):
    n = torch.sqrt(torch.as_tensor(MU_EARTH_M3_S2, device=a_m.device, dtype=a_m.dtype) / a_m**3)
    p = a_m * (1.0 - e * e)
    fac = 1.5 * n * J2 * (R_EARTH_M / p) ** 2
    c = torch.cos(i_rad)
    raan_dot = -fac * c
    argp_dot = 0.5 * fac * (5.0 * c * c - 1.0)
    m_dot = n + 0.5 * fac * torch.sqrt(torch.clamp(1.0 - e * e, min=0.0)) * (3.0 * c * c - 1.0)
    return raan_dot, argp_dot, m_dot


def _eccentric_anomaly_torch(M, e, torch, *, n_iter: int = 12, tol: float = 1e-10):
    two_pi = 2.0 * torch.pi
    M = torch.remainder(M, two_pi)
    E = torch.where(e < 0.8, M, torch.full_like(M, torch.pi))
    for _ in range(n_iter):
        f = E - e * torch.sin(E) - M
        dE = f / (1.0 - e * torch.cos(E))
        E = E - dE
        if float(torch.max(torch.abs(dE))) < tol:
            break
    return E


def _keplerian_to_eci_torch(a, e, i, raan, argp, M, torch):
    """Supports shapes (N,) or (T, N) for all angles; a,e,i broadcastable."""
    E = _eccentric_anomaly_torch(M, e, torch)
    sin_E, cos_E = torch.sin(E), torch.cos(E)
    sqrt_1e2 = torch.sqrt(torch.clamp(1.0 - e * e, min=0.0))
    nu = torch.atan2(sqrt_1e2 * sin_E, cos_E - e)
    r_mag = a * (1.0 - e * cos_E)
    cos_u = torch.cos(argp + nu)
    sin_u = torch.sin(argp + nu)
    cos_raan, sin_raan = torch.cos(raan), torch.sin(raan)
    cos_i, sin_i = torch.cos(i), torch.sin(i)
    rx = r_mag * (cos_raan * cos_u - sin_raan * sin_u * cos_i)
    ry = r_mag * (sin_raan * cos_u + cos_raan * sin_u * cos_i)
    rz = r_mag * (sin_u * sin_i)
    r = torch.stack((rx, ry, rz), dim=-1)
    mu = torch.as_tensor(MU_EARTH_M3_S2, device=a.device, dtype=a.dtype)
    vx_pqw = -torch.sqrt(mu * a) / r_mag * sin_E
    vy_pqw = torch.sqrt(mu * a) / r_mag * sqrt_1e2 * cos_E
    cos_w, sin_w = torch.cos(argp), torch.sin(argp)
    px = cos_w * vx_pqw - sin_w * vy_pqw
    py = sin_w * vx_pqw + cos_w * vy_pqw
    vx = cos_raan * px - sin_raan * cos_i * py
    vy = sin_raan * px + cos_raan * cos_i * py
    vz = sin_i * py
    v = torch.stack((vx, vy, vz), dim=-1)
    return r, v


class GpuKeplerJ2Propagator:
    name = "kepler_j2_gpu"

    def __init__(self, atmosphere: object | None = None, apply_drag: bool = False) -> None:
        self.atmosphere = atmosphere
        self.apply_drag = bool(apply_drag)
        self._cpu = KeplerJ2Propagator(atmosphere=atmosphere, apply_drag=apply_drag)
        self._use_cuda = False
        try:
            torch, device = _get_torch()
            self._use_cuda = device.type == "cuda"
            self._torch = torch
            self._device = device
        except Exception:
            self._torch = None
            self._device = None

    @property
    def using_cuda(self) -> bool:
        return bool(self._use_cuda)

    def elements_at(self, elements: KeplerianBatch, elapsed_s: float) -> KeplerianBatch:
        if not self._use_cuda or self.apply_drag:
            return self._cpu.elements_at(elements, elapsed_s)
        torch = self._torch
        device = self._device
        a = _t(elements.a_m, torch, device)
        e = _t(elements.e, torch, device)
        i = _t(elements.i_rad, torch, device)
        raan = _t(elements.raan_rad, torch, device)
        argp = _t(elements.argp_rad, torch, device)
        m = _t(elements.m_rad, torch, device)
        raan_dot, argp_dot, m_dot = _j2_rates_torch(a, e, i, torch)
        dt = float(elapsed_s)
        two_pi = 2.0 * torch.pi
        out = elements.copy()
        out.raan_rad = torch.remainder(raan + raan_dot * dt, two_pi).detach().cpu().numpy()
        out.argp_rad = torch.remainder(argp + argp_dot * dt, two_pi).detach().cpu().numpy()
        out.m_rad = torch.remainder(m + m_dot * dt, two_pi).detach().cpu().numpy()
        return out

    def state_eci_m(self, elements: KeplerianBatch, elapsed_s: float):
        if not self._use_cuda:
            return self._cpu.state_eci_m(elements, elapsed_s)
        torch = self._torch
        device = self._device
        a = _t(elements.a_m, torch, device)
        e = _t(elements.e, torch, device)
        i = _t(elements.i_rad, torch, device)
        raan = _t(elements.raan_rad, torch, device)
        argp = _t(elements.argp_rad, torch, device)
        m = _t(elements.m_rad, torch, device)
        raan_dot, argp_dot, m_dot = _j2_rates_torch(a, e, i, torch)
        dt = float(elapsed_s)
        two_pi = 2.0 * torch.pi
        raan2 = torch.remainder(raan + raan_dot * dt, two_pi)
        argp2 = torch.remainder(argp + argp_dot * dt, two_pi)
        m2 = torch.remainder(m + m_dot * dt, two_pi)
        r, v = _keplerian_to_eci_torch(a, e, i, raan2, argp2, m2, torch)
        if device.type == "cuda":
            torch.cuda.synchronize()
        return r.detach().cpu().numpy(), v.detach().cpu().numpy()

    def positions_eci_batch(self, elements: KeplerianBatch, elapsed_s_list) -> np.ndarray:
        """True T×N GPU broadcast. Returns (T, N, 3)."""
        times = np.asarray(elapsed_s_list, dtype=float).ravel()
        if not self._use_cuda:
            return np.stack([self._cpu.positions_eci_m(elements, float(t)) for t in times], axis=0)
        torch = self._torch
        device = self._device
        a = _t(elements.a_m, torch, device)
        e = _t(elements.e, torch, device)
        i = _t(elements.i_rad, torch, device)
        raan0 = _t(elements.raan_rad, torch, device)
        argp0 = _t(elements.argp_rad, torch, device)
        m0 = _t(elements.m_rad, torch, device)
        raan_dot, argp_dot, m_dot = _j2_rates_torch(a, e, i, torch)
        tt = torch.as_tensor(times, dtype=a.dtype, device=device)[:, None]  # (T,1)
        two_pi = 2.0 * torch.pi
        raan = torch.remainder(raan0[None, :] + raan_dot[None, :] * tt, two_pi)
        argp = torch.remainder(argp0[None, :] + argp_dot[None, :] * tt, two_pi)
        m = torch.remainder(m0[None, :] + m_dot[None, :] * tt, two_pi)
        a2 = a[None, :].expand_as(m)
        e2 = e[None, :].expand_as(m)
        i2 = i[None, :].expand_as(m)
        r, _v = _keplerian_to_eci_torch(a2, e2, i2, raan, argp, m, torch)
        if device.type == "cuda":
            torch.cuda.synchronize()
        return r.detach().cpu().numpy()

    def positions_eci_m(self, elements: KeplerianBatch, elapsed_s: float) -> np.ndarray:
        r, _v = self.state_eci_m(elements, elapsed_s)
        return r

    def positions_ecef_m(self, elements: KeplerianBatch, epoch: datetime, elapsed_s: float) -> np.ndarray:
        r_eci = self.positions_eci_m(elements, elapsed_s)
        when = epoch + timedelta(seconds=float(elapsed_s))
        return eci_to_ecef(r_eci, when)
