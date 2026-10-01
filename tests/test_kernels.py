"""Scorer kernels with the optional torch backend (plan item 9c).

The skimage path is the parity-locked reference; the torch path must reproduce it
within float32 tolerance on every device, and every unavailable device falls back to
the reference with one warning.
"""

from __future__ import annotations

import types
import warnings
from pathlib import Path

import numpy as np
import pytest
from skimage import color, metrics

from neurotic_docx_bench import content_cache as cc
from neurotic_docx_bench import kernels

torch = pytest.importorskip("torch", reason="torch extra not installed")


def _fake_torch(*, cuda: bool, mps: bool) -> types.SimpleNamespace:
    """In-memory stand-in for the parts of torch that device resolution touches."""
    return types.SimpleNamespace(
        cuda=types.SimpleNamespace(is_available=lambda: cuda),
        backends=types.SimpleNamespace(mps=types.SimpleNamespace(is_available=lambda: mps)),
    )


def _page_like(seed: int, shape: tuple[int, int] = (96, 128)) -> np.ndarray:
    """A synthetic page: white paper, dark glyph-like blocks, a few coloured strokes."""
    rng = np.random.default_rng(seed)
    img = np.ones((*shape, 3), dtype=np.float32)
    for _ in range(40):
        y, x = rng.integers(0, shape[0] - 6), rng.integers(0, shape[1] - 12)
        img[y : y + rng.integers(2, 6), x : x + rng.integers(4, 12)] = rng.uniform(0.0, 0.25)
    for _ in range(8):
        y, x = rng.integers(0, shape[0] - 3), rng.integers(0, shape[1] - 30)
        img[y : y + 2, x : x + 30] = rng.uniform(0.0, 1.0, size=3).astype(np.float32)
    img += rng.normal(0.0, 0.01, size=img.shape).astype(np.float32)
    return np.clip(img, 0.0, 1.0).astype(np.float32)


# --- device resolution -------------------------------------------------------------


def test_resolve_device_prefers_cuda_then_mps_then_the_numpy_path() -> None:
    assert kernels.resolve_device("auto", torch_module=_fake_torch(cuda=True, mps=True)) == "cuda"
    assert kernels.resolve_device("auto", torch_module=_fake_torch(cuda=False, mps=True)) == "mps"
    assert kernels.resolve_device("auto", torch_module=_fake_torch(cuda=False, mps=False)) is None
    assert kernels.resolve_device("cpu", torch_module=_fake_torch(cuda=False, mps=False)) == "cpu"
    assert kernels.resolve_device("cuda", torch_module=_fake_torch(cuda=True, mps=False)) == "cuda"
    assert kernels.resolve_device("mps", torch_module=_fake_torch(cuda=False, mps=True)) == "mps"


def test_resolve_device_falls_back_to_numpy_with_one_warning() -> None:
    with pytest.warns(RuntimeWarning, match="cuda.*unavailable"):
        assert kernels.resolve_device("cuda", torch_module=_fake_torch(cuda=False, mps=True)) is None
    with pytest.warns(RuntimeWarning, match="mps.*unavailable"):
        assert kernels.resolve_device("mps", torch_module=_fake_torch(cuda=True, mps=False)) is None
    with pytest.warns(RuntimeWarning, match="torch is not installed"):
        assert kernels.resolve_device("cpu", torch_module=None) is None
    # ``auto`` without torch is the documented default path: silent.
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert kernels.resolve_device("auto", torch_module=None) is None
        assert kernels.resolve_device(None, torch_module=None) is None
        assert kernels.resolve_device("", torch_module=_fake_torch(cuda=True, mps=True)) is None


def test_torch_kernels_refuse_to_run_without_torch(monkeypatch) -> None:
    monkeypatch.setattr(kernels, "_import_torch", lambda: None)
    with pytest.raises(RuntimeError, match="neurotic-docx-bench\\[gpu\\]"):
        kernels.ssim_torch(np.zeros((8, 8), np.float32), np.zeros((8, 8), np.float32), device="cpu")


def test_resolve_device_rejects_unknown_specs() -> None:
    with pytest.raises(ValueError, match="auto, cpu, mps, cuda"):
        kernels.resolve_device("tpu", torch_module=_fake_torch(cuda=False, mps=False))


def test_active_device_and_backend_id_follow_the_environment(monkeypatch) -> None:
    monkeypatch.setenv(kernels.DEVICE_ENV, "numpy")
    kernels.reset()
    assert kernels.active_device() is None
    assert kernels.backend_id() == "numpy"
    monkeypatch.setenv(kernels.DEVICE_ENV, "cpu")
    kernels.reset()
    assert kernels.active_device() == "cpu"
    assert kernels.backend_id() == "torch-cpu"
    kernels.reset()


def test_device_env_sets_and_restores_the_environment(monkeypatch) -> None:
    monkeypatch.setenv(kernels.DEVICE_ENV, "numpy")
    kernels.reset()
    with kernels.device_env("cpu"):
        assert kernels.active_device() == "cpu"
    assert kernels.os.environ[kernels.DEVICE_ENV] == "numpy"
    assert kernels.active_device() is None
    with kernels.device_env(None):
        assert kernels.active_device() == kernels._default_device()


def test_worker_init_shares_the_cores_between_torch_and_the_pool(monkeypatch) -> None:
    """Each pool worker gets ``cpu_count // jobs`` intra-op threads on torch-cpu, so
    ``jobs`` workers never oversubscribe the machine; the numpy path is left alone."""
    monkeypatch.setattr(kernels.os, "cpu_count", lambda: 8)
    before = torch.get_num_threads()
    monkeypatch.setenv(kernels.DEVICE_ENV, "numpy")
    kernels.reset()
    kernels.worker_init(4)
    assert torch.get_num_threads() == before, "no device: torch is not touched"
    monkeypatch.setenv(kernels.DEVICE_ENV, "cpu")
    kernels.reset()
    try:
        kernels.worker_init(4)
        assert torch.get_num_threads() == 2
        kernels.worker_init(16)
        assert torch.get_num_threads() == 1
        kernels.worker_init(1)
        assert torch.get_num_threads() == 8
        monkeypatch.setenv(kernels.THREADS_ENV, "3")
        kernels.worker_init(4)
        assert torch.get_num_threads() == 3
    finally:
        torch.set_num_threads(before)
        kernels.reset()


def test_score_key_changes_with_the_backend() -> None:
    common = {"candidate_sha": "c" * 64, "oracle_sha": "o" * 64, "base_sha": None, "dpi": 144, "renderer_id": "r"}
    assert cc.score_key(**common, backend="numpy") != cc.score_key(**common, backend="torch-cpu")


# --- parity against the skimage reference -------------------------------------------


def test_delta_e_mean_torch_matches_skimage_on_synthetic_pages() -> None:
    a, b = _page_like(1), _page_like(2)
    mask = color.rgb2gray(a) < 0.9
    reference = kernels.delta_e_mean_numpy(a, b, mask)
    lab_a, lab_b = color.rgb2lab(a), color.rgb2lab(b)
    assert reference == pytest.approx(float(color.deltaE_ciede2000(lab_a, lab_b)[mask].mean()))
    got = kernels.delta_e_mean_torch(a, b, mask, device="cpu")
    assert got == pytest.approx(reference, abs=1e-3)
    assert kernels.delta_e_mean_torch(a, a, mask, device="cpu") == pytest.approx(0.0, abs=1e-4)


def test_rgb2lab_and_ciede2000_torch_match_skimage_elementwise() -> None:
    rng = np.random.default_rng(0)
    a = rng.uniform(0.0, 1.0, size=(64, 48, 3)).astype(np.float32)
    b = np.clip(a + rng.normal(0.0, 0.1, size=a.shape), 0.0, 1.0).astype(np.float32)
    lab_a = kernels.rgb2lab_torch(torch.from_numpy(a)).numpy()
    np.testing.assert_allclose(lab_a, color.rgb2lab(a), atol=2e-3)
    de = kernels.ciede2000_torch(torch.from_numpy(color.rgb2lab(a)), torch.from_numpy(color.rgb2lab(b))).numpy()
    np.testing.assert_allclose(de, color.deltaE_ciede2000(color.rgb2lab(a), color.rgb2lab(b)), atol=2e-3)


def test_ssim_torch_matches_skimage() -> None:
    a = color.rgb2gray(_page_like(3)).astype(np.float32)
    b = color.rgb2gray(_page_like(4)).astype(np.float32)
    reference = float(metrics.structural_similarity(a, b, data_range=1.0))
    assert kernels.ssim_numpy(a, b) == pytest.approx(reference)
    assert kernels.ssim_torch(a, b, device="cpu") == pytest.approx(reference, abs=1e-4)
    assert kernels.ssim_torch(a, a, device="cpu") == pytest.approx(1.0, abs=1e-6)


def test_public_kernels_dispatch_on_the_active_device(monkeypatch) -> None:
    a, b = _page_like(5), _page_like(6)
    mask = color.rgb2gray(a) < 0.9
    ga, gb = color.rgb2gray(a).astype(np.float32), color.rgb2gray(b).astype(np.float32)
    monkeypatch.setenv(kernels.DEVICE_ENV, "numpy")
    kernels.reset()
    ref_de, ref_ssim = kernels.delta_e_mean(a, b, mask), kernels.ssim(ga, gb)
    assert ref_de == kernels.delta_e_mean_numpy(a, b, mask)
    assert ref_ssim == kernels.ssim_numpy(ga, gb)
    calls: list[str] = []
    monkeypatch.setattr(kernels, "delta_e_mean_torch", lambda *args, **kw: calls.append("de") or ref_de)
    monkeypatch.setattr(kernels, "ssim_torch", lambda *args, **kw: calls.append("ssim") or ref_ssim)
    monkeypatch.setenv(kernels.DEVICE_ENV, "cpu")
    kernels.reset()
    assert kernels.delta_e_mean(a, b, mask) == ref_de
    assert kernels.ssim(ga, gb) == ref_ssim
    assert calls == ["de", "ssim"]
    kernels.reset()


def test_score_document_is_the_same_on_torch_cpu_within_float32(tmp_path: Path, monkeypatch) -> None:
    from PIL import Image

    from neurotic_docx_bench import score

    pages = []
    for i, seed in enumerate((7, 8)):
        img = (_page_like(seed, (240, 200)) * 255).round().astype(np.uint8)
        p = tmp_path / f"page_{i}.png"
        Image.fromarray(img).save(p)
        pages.append(p)
    monkeypatch.setenv(kernels.DEVICE_ENV, "numpy")
    kernels.reset()
    reference = score.score_document([pages[0]], [pages[1]])
    monkeypatch.setenv(kernels.DEVICE_ENV, "cpu")
    kernels.reset()
    try:
        got = score.score_document([pages[0]], [pages[1]])
    finally:
        kernels.reset()
    assert got["config"] == reference["config"], "the torch device is not part of the scorer config"
    for key in ("overall_score", "overall_score_strict", "overall_score_drift"):
        assert got[key] == pytest.approx(reference[key], abs=1e-3), key
    for key, value in reference["pages"][0].items():
        if isinstance(value, float):
            assert got["pages"][0][key] == pytest.approx(value, abs=1e-3), key
        else:
            assert got["pages"][0][key] == value, key


def test_score_document_parity_on_real_oracle_pages(tmp_path: Path, monkeypatch, sample_oracle_pdfs) -> None:
    """Two real Word renders (corpus only): torch-cpu within 0.01 points of the reference."""
    from neurotic_docx_bench import raster, score

    pages = []
    for i, pdf in enumerate(sample_oracle_pdfs):
        out = tmp_path / f"p{i}"
        raster.rasterize_pdf(pdf, out, dpi=144)
        pages.append(min(out.glob("page_*.png")))
    monkeypatch.setenv(kernels.DEVICE_ENV, "numpy")
    kernels.reset()
    reference = score.score_document([pages[0]], [pages[1]])
    monkeypatch.setenv(kernels.DEVICE_ENV, "cpu")
    kernels.reset()
    try:
        got = score.score_document([pages[0]], [pages[1]])
    finally:
        kernels.reset()
    assert got["overall_score"] == pytest.approx(reference["overall_score"], abs=1e-2)
    page_ref, page_got = reference["pages"][0], got["pages"][0]
    for key in ("ssim_full", "ssim_small", "color_sim", "drift_ssim_full", "drift_color_sim"):
        assert page_got[key] == pytest.approx(page_ref[key], abs=1e-4), key
    assert page_got["delta_e"] == pytest.approx(page_ref["delta_e"], abs=1e-3)


def test_hardware_info_stamps_the_scorer_backend(monkeypatch) -> None:
    from neurotic_docx_bench import hardware

    monkeypatch.setenv(kernels.DEVICE_ENV, "numpy")
    kernels.reset()
    assert hardware.hardware_info()["scorer_backend"] == "numpy"
