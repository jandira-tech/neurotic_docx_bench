"""Scorer kernels with an optional torch backend (plan item 9c).

``score.py`` spends most of a page in two elementwise kernels: the CIEDE2000 colour
distance (sRGB to Lab, then the distance) and SSIM. Both live here with two
implementations: the skimage/scipy path, which is the parity-locked reference and the
default, and a torch port selected by ``BENCH_DEVICE`` (``bench run --device``).

Device spec: ``auto`` picks cuda, then mps, else the numpy path; ``cpu``, ``mps`` and
``cuda`` ask for that torch device and fall back to the numpy path with one warning
when torch or the device is unavailable. The torch path computes in float32 (mps has
no float64) and reproduces the reference within float32 tolerance; the backend id is
part of the content-cache score key and of the hardware stamp on every result.
"""

from __future__ import annotations

import contextlib
import functools
import importlib
import math
import os
import warnings
from collections.abc import Callable, Iterator
from typing import Any

import numpy as np
from skimage import color, metrics

DEVICE_ENV = "BENCH_DEVICE"
DEVICE_SPECS: tuple[str, ...] = ("auto", "cpu", "mps", "cuda")

# skimage's sRGB (D65) matrices and white point, so the torch path shares its constants.
_XYZ_FROM_RGB = (
    (0.412453, 0.357580, 0.180423),
    (0.212671, 0.715160, 0.072169),
    (0.019334, 0.119193, 0.950227),
)
_D65 = (0.95047, 1.0, 1.08883)
_SSIM_WIN = 7
_SSIM_K1 = 0.01
_SSIM_K2 = 0.03


# --- device resolution -------------------------------------------------------------


def _import_torch() -> Any | None:
    try:
        return importlib.import_module("torch")
    except ImportError:
        return None


def _require_torch() -> Any:
    """torch for the kernels below; only reached after a device resolved, so a missing
    torch here is a programming error rather than a fallback case."""
    torch = _import_torch()
    if torch is None:
        raise RuntimeError("the torch kernels need torch (pip install 'neurotic-docx-bench[gpu]')")
    return torch


_INSTALLED = object()


def resolve_device(
    spec: str | None,
    *,
    torch_module: Any = _INSTALLED,
    warn: Callable[[str], None] | None = None,
) -> str | None:
    """Map a ``--device`` spec to a torch device string, or ``None`` for the numpy path.

    ``torch_module`` is the torch module to consult (``None`` means not installed); by
    default the real one is imported, and only when a device is asked for.
    """
    if not spec:
        return None
    if spec not in DEVICE_SPECS:
        raise ValueError(f"unknown device {spec!r}; expected one of: {', '.join(DEVICE_SPECS)}")
    emit = warn or (lambda msg: warnings.warn(msg, RuntimeWarning, stacklevel=3))
    if torch_module is _INSTALLED:
        torch_module = _import_torch()
    if spec == "auto":
        if torch_module is None:
            return None
        if torch_module.cuda.is_available():
            return "cuda"
        if torch_module.backends.mps.is_available():
            return "mps"
        return None
    if torch_module is None:
        emit(f"--device {spec}: torch is not installed (pip install 'neurotic-docx-bench[gpu]'); using the numpy path")
        return None
    if spec == "cpu":
        return "cpu"
    available = torch_module.cuda.is_available() if spec == "cuda" else torch_module.backends.mps.is_available()
    if not available:
        emit(f"--device {spec}: {spec} is unavailable on this machine; using the numpy path")
        return None
    return spec


@functools.cache
def _resolved(spec: str) -> str | None:
    return resolve_device(spec)


def active_device() -> str | None:
    """The torch device the kernels run on, from ``BENCH_DEVICE``; ``None`` is numpy."""
    spec = os.environ.get(DEVICE_ENV, "")
    return _resolved(spec) if spec else None


def reset() -> None:
    """Forget resolved devices (tests, or after the environment changed)."""
    _resolved.cache_clear()


def backend_id() -> str:
    device = active_device()
    return "numpy" if device is None else f"torch-{device}"


@contextlib.contextmanager
def device_env(spec: str | None) -> Iterator[None]:
    """Export ``BENCH_DEVICE`` for the duration of a command (worker processes inherit
    it), validating the spec first; restore the previous value afterwards."""
    if spec and spec not in DEVICE_SPECS:
        raise ValueError(f"unknown device {spec!r}; expected one of: {', '.join(DEVICE_SPECS)}")
    previous = os.environ.get(DEVICE_ENV)
    if spec:
        os.environ[DEVICE_ENV] = spec
    else:
        os.environ.pop(DEVICE_ENV, None)
    reset()
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(DEVICE_ENV, None)
        else:
            os.environ[DEVICE_ENV] = previous
        reset()


THREADS_ENV = "BENCH_TORCH_THREADS"


def worker_init(jobs: int) -> None:
    """Process-pool initializer: on a torch device, give this worker
    ``cpu_count // jobs`` intra-op threads (at least one) so ``jobs`` workers share the
    cores instead of each starting torch's default thread pool; ``BENCH_TORCH_THREADS``
    overrides the count; no device, no change."""
    if active_device() is None:
        return
    torch = _require_torch()
    override = os.environ.get(THREADS_ENV, "")
    threads = int(override) if override else (os.cpu_count() or 1) // max(1, jobs)
    torch.set_num_threads(max(1, threads))


# --- reference (skimage) kernels ----------------------------------------------------


def delta_e_mean_numpy(a_rgb: np.ndarray, b_rgb: np.ndarray, mask: np.ndarray) -> float:
    a_lab = color.rgb2lab(a_rgb)
    b_lab = color.rgb2lab(b_rgb)
    delta = color.deltaE_ciede2000(a_lab, b_lab)
    return float(delta[mask].mean())


def ssim_numpy(a_gray: np.ndarray, b_gray: np.ndarray) -> float:
    return float(metrics.structural_similarity(a_gray, b_gray, data_range=1.0))


# --- torch kernels ---------------------------------------------------------------------


def rgb2lab_torch(rgb: Any) -> Any:
    """sRGB (0..1, channels last) to CIE Lab under D65, skimage's constants and gamma."""
    torch = _require_torch()
    linear = torch.where(rgb > 0.04045, ((rgb + 0.055) / 1.055) ** 2.4, rgb / 12.92)
    m = torch.tensor(_XYZ_FROM_RGB, dtype=rgb.dtype, device=rgb.device)
    xyz = linear @ m.T
    xyz = xyz / torch.tensor(_D65, dtype=rgb.dtype, device=rgb.device)
    f = torch.where(xyz > 0.008856, xyz.clamp_min(0.0) ** (1.0 / 3.0), 7.787 * xyz + 16.0 / 116.0)
    x, y, z = f[..., 0], f[..., 1], f[..., 2]
    return torch.stack([116.0 * y - 16.0, 500.0 * (x - y), 200.0 * (y - z)], dim=-1)


def ciede2000_torch(lab1: Any, lab2: Any) -> Any:
    """CIEDE2000 with kL = kC = kH = 1, term for term as skimage computes it."""
    torch = _require_torch()
    pi = math.pi
    L1, a1, b1 = lab1[..., 0], lab1[..., 1], lab1[..., 2]
    L2, a2, b2 = lab2[..., 0], lab2[..., 1], lab2[..., 2]
    cbar = 0.5 * (torch.hypot(a1, b1) + torch.hypot(a2, b2))
    c7 = cbar**7
    g = 0.5 * (1 - torch.sqrt(c7 / (c7 + 25.0**7)))
    scale = 1 + g

    def polar(x: Any, y: Any) -> tuple[Any, Any]:
        r, t = torch.hypot(x, y), torch.atan2(y, x)
        return r, torch.where(t < 0.0, t + 2 * pi, t)

    C1, h1 = polar(a1 * scale, b1)
    C2, h2 = polar(a2 * scale, b2)
    lbar = 0.5 * (L1 + L2)
    tmp = (lbar - 50) ** 2
    sl = 1 + 0.015 * tmp / torch.sqrt(20 + tmp)
    l_term = (L2 - L1) / sl
    cbar = 0.5 * (C1 + C2)
    sc = 1 + 0.045 * cbar
    c_term = (C2 - C1) / sc
    h_diff = h2 - h1
    h_sum = h1 + h2
    cc = C1 * C2
    zero = cc == 0.0
    dh = torch.where(h_diff > pi, h_diff - 2 * pi, h_diff)
    dh = torch.where(h_diff < -pi, dh + 2 * pi, dh)
    dh = torch.where(zero, torch.zeros_like(dh), dh)
    dh_term = 2 * torch.sqrt(cc) * torch.sin(dh / 2)
    wrap = (~zero) & (h_diff.abs() > pi)
    hbar = torch.where(wrap & (h_sum < 2 * pi), h_sum + 2 * pi, h_sum)
    hbar = torch.where(wrap & (h_sum >= 2 * pi), hbar - 2 * pi, hbar)
    hbar = torch.where(zero, hbar * 2, hbar)
    hbar = hbar * 0.5
    t = (
        1
        - 0.17 * torch.cos(hbar - math.radians(30))
        + 0.24 * torch.cos(2 * hbar)
        + 0.32 * torch.cos(3 * hbar + math.radians(6))
        - 0.20 * torch.cos(4 * hbar - math.radians(63))
    )
    sh = 1 + 0.015 * cbar * t
    h_term = dh_term / sh
    c7 = cbar**7
    rc = 2 * torch.sqrt(c7 / (c7 + 25.0**7))
    dtheta = math.radians(30) * torch.exp(-(((torch.rad2deg(hbar) - 275) / 25) ** 2))
    r_term = -torch.sin(2 * dtheta) * rc * c_term * h_term
    de2 = l_term**2 + c_term**2 + h_term**2 + r_term
    return torch.sqrt(de2.clamp_min(0.0))


def _to_device(arr: np.ndarray, device: str) -> Any:
    torch = _require_torch()
    return torch.from_numpy(np.ascontiguousarray(arr, dtype=np.float32)).to(device)


def delta_e_mean_torch(a_rgb: np.ndarray, b_rgb: np.ndarray, mask: np.ndarray, *, device: str) -> float:
    torch = _require_torch()
    with torch.no_grad():
        a_lab = rgb2lab_torch(_to_device(a_rgb, device))
        b_lab = rgb2lab_torch(_to_device(b_rgb, device))
        delta = ciede2000_torch(a_lab, b_lab)
        m = torch.from_numpy(np.ascontiguousarray(mask, dtype=bool)).to(device)
        return float(delta[m].mean().item())


def ssim_torch(a_gray: np.ndarray, b_gray: np.ndarray, *, device: str) -> float:
    """skimage's ``structural_similarity`` defaults: 7x7 uniform window, sample
    covariance, K1 = 0.01, K2 = 0.03, data_range 1, mean over the valid interior."""
    torch = _require_torch()
    from torch.nn import functional as fn

    with torch.no_grad():
        x = _to_device(a_gray, device)[None, None]
        y = _to_device(b_gray, device)[None, None]

        def mean(t: Any) -> Any:
            return fn.avg_pool2d(t, _SSIM_WIN, stride=1)

        n = _SSIM_WIN * _SSIM_WIN
        cov_norm = n / (n - 1)
        ux, uy = mean(x), mean(y)
        vx = cov_norm * (mean(x * x) - ux * ux)
        vy = cov_norm * (mean(y * y) - uy * uy)
        vxy = cov_norm * (mean(x * y) - ux * uy)
        c1, c2 = _SSIM_K1**2, _SSIM_K2**2
        s = ((2 * ux * uy + c1) * (2 * vxy + c2)) / ((ux * ux + uy * uy + c1) * (vx + vy + c2))
        if device == "mps":
            return float(s.mean().item())
        return float(s.to(torch.float64).mean().item())


# --- public dispatch --------------------------------------------------------------------


def delta_e_mean(a_rgb: np.ndarray, b_rgb: np.ndarray, mask: np.ndarray) -> float:
    """Mean CIEDE2000 distance over ``mask`` (callers guarantee a non-empty mask)."""
    device = active_device()
    if device is None:
        return delta_e_mean_numpy(a_rgb, b_rgb, mask)
    return delta_e_mean_torch(a_rgb, b_rgb, mask, device=device)


def ssim(a_gray: np.ndarray, b_gray: np.ndarray) -> float:
    device = active_device()
    if device is None:
        return ssim_numpy(a_gray, b_gray)
    return ssim_torch(a_gray, b_gray, device=device)
