"""Device selection policy without requiring the optional torch dependency."""

from __future__ import annotations

import warnings
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from neurotic_docx_bench import kernels


@pytest.fixture(autouse=True)
def reset_devices():
    kernels.reset()
    yield
    kernels.reset()


def fake_torch(*, mps=False, cuda=False):
    return SimpleNamespace(
        cuda=SimpleNamespace(is_available=lambda: cuda),
        backends=SimpleNamespace(mps=SimpleNamespace(is_available=lambda: mps)),
    )


@pytest.mark.parametrize("env", [None, ""])
@pytest.mark.parametrize(
    ("torch_module", "expected"),
    [
        (None, None),
        (fake_torch(), None),
        (fake_torch(cuda=True), None),
        (fake_torch(mps=True), "mps"),
        (fake_torch(mps=True, cuda=True), "mps"),
    ],
    ids=["no-torch", "no-gpu", "cuda-only", "mps", "both-gpus"],
)
def test_default_uses_only_mps_and_falls_back_silently(monkeypatch, env, torch_module, expected):
    if env is None:
        monkeypatch.delenv(kernels.DEVICE_ENV, raising=False)
    else:
        monkeypatch.setenv(kernels.DEVICE_ENV, env)
    monkeypatch.setattr(kernels, "_import_torch", lambda: torch_module)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert kernels.active_device() == expected
        assert kernels.backend_id() == ("torch-mps" if expected else "numpy")


def test_explicit_numpy_never_imports_torch(monkeypatch):
    importer = Mock(side_effect=AssertionError("numpy must not load torch"))
    monkeypatch.setattr(kernels, "_import_torch", importer)
    monkeypatch.setenv(kernels.DEVICE_ENV, "numpy")
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert kernels.resolve_device("numpy") is None
        assert kernels.active_device() is None
        assert kernels.backend_id() == "numpy"
    importer.assert_not_called()


@pytest.mark.parametrize("spec", ["numpy", "auto", "cpu", "cuda", "mps"])
def test_explicit_device_overrides_cached_default(monkeypatch, spec):
    monkeypatch.delenv(kernels.DEVICE_ENV, raising=False)
    monkeypatch.setattr(kernels, "_import_torch", lambda: fake_torch(mps=True, cuda=True))
    assert kernels.active_device() == "mps"
    monkeypatch.setenv(kernels.DEVICE_ENV, spec)
    expected = {"numpy": None, "auto": "cuda"}.get(spec, spec)
    assert kernels.active_device() == expected
    assert kernels.backend_id() == (f"torch-{expected}" if expected else "numpy")


@pytest.mark.parametrize("torch_module", [None, fake_torch(cuda=True)], ids=["no-torch", "no-mps"])
def test_explicit_mps_warns_once_even_after_silent_default_fallback(monkeypatch, torch_module):
    monkeypatch.delenv(kernels.DEVICE_ENV, raising=False)
    monkeypatch.setattr(kernels, "_import_torch", lambda: torch_module)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert kernels.active_device() is None
    monkeypatch.setenv(kernels.DEVICE_ENV, "mps")
    with pytest.warns(RuntimeWarning, match="--device mps.*using the numpy path") as caught:
        assert kernels.active_device() is None
        assert kernels.backend_id() == "numpy"
    assert len(caught) == 1


@pytest.mark.parametrize("initial_mps", [False, True])
def test_default_resolution_is_cached_until_reset(monkeypatch, initial_mps):
    monkeypatch.delenv(kernels.DEVICE_ENV, raising=False)
    importer = Mock(return_value=fake_torch(mps=initial_mps))
    monkeypatch.setattr(kernels, "_import_torch", importer)
    expected = "mps" if initial_mps else None
    assert kernels.active_device() == expected
    importer.return_value = fake_torch(mps=not initial_mps)
    assert kernels.active_device() == expected
    importer.assert_called_once_with()
    kernels.reset()
    assert kernels.active_device() == (None if initial_mps else "mps")
    assert importer.call_count == 2


@pytest.mark.parametrize("previous", [None, "mps"])
def test_numpy_context_restores_default_or_explicit_device_after_error(monkeypatch, previous):
    if previous is None:
        monkeypatch.delenv(kernels.DEVICE_ENV, raising=False)
    else:
        monkeypatch.setenv(kernels.DEVICE_ENV, previous)
    monkeypatch.setattr(kernels, "_import_torch", lambda: fake_torch(mps=True))
    assert kernels.active_device() == "mps"
    with pytest.raises(RuntimeError, match="scoring failed"):
        with kernels.device_env("numpy"):
            assert kernels.backend_id() == "numpy"
            raise RuntimeError("scoring failed")
    assert kernels.os.environ.get(kernels.DEVICE_ENV) == previous
    assert kernels.backend_id() == "torch-mps"
