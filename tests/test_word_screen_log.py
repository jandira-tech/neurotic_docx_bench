"""Spec for the Word screen logger (``scripts/word_screen_log.py``).

Everything here is stubbed: no CoreGraphics, no Vision, no screencapture, no tesseract
binary. The module is loaded with fake ``Quartz``/``Vision``/``Foundation`` modules so the
tests drive the OCR fallback chain and the per-poll dialog bookkeeping as pure logic.
The Vision stub's ``returns`` maps a recognition level to the strings it "reads"; an
empty list is a successful request that recognized nothing, ``None`` is a failed request.
"""

from __future__ import annotations

import errno
import importlib.util
import io
import os
import struct
import subprocess
import sys
import tempfile
import types
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "word_screen_log.py"


class _Cand:
    def __init__(self, s: str):
        self._s = s

    def string(self) -> str:
        return self._s


class _Obs:
    def __init__(self, s: str):
        self._s = s

    def topCandidates_(self, n: int):
        return [_Cand(self._s)]


def _make_vision() -> types.ModuleType:
    m = types.ModuleType("Vision")
    m.VNRequestTextRecognitionLevelAccurate = "accurate"
    m.VNRequestTextRecognitionLevelFast = "fast"
    m.returns = {"accurate": ["probe strip"], "fast": []}

    class _Req:
        def __init__(self):
            self.level = None

        @classmethod
        def alloc(cls):
            return cls()

        def init(self):
            return self

        def setRecognitionLevel_(self, level):
            self.level = level

        def results(self):
            return [_Obs(s) for s in (m.returns.get(self.level) or [])]

    class _Handler:
        @classmethod
        def alloc(cls):
            return cls()

        def initWithURL_options_(self, url, opts):
            return self

        def performRequests_error_(self, reqs, err):
            ok = all(m.returns.get(r.level) is not None for r in reqs)
            return ok, None

    m.VNRecognizeTextRequest = _Req
    m.VNImageRequestHandler = _Handler
    return m


@pytest.fixture
def wsl(monkeypatch, tmp_path):
    """The logger module with every macOS dependency stubbed and state reset per test."""
    vis = _make_vision()
    monkeypatch.setitem(sys.modules, "Vision", vis)
    monkeypatch.setitem(sys.modules, "Quartz", types.ModuleType("Quartz"))
    foundation = types.ModuleType("Foundation")
    foundation.NSURL = types.SimpleNamespace(fileURLWithPath_=staticmethod(str))
    monkeypatch.setitem(sys.modules, "Foundation", foundation)
    monkeypatch.setattr(tempfile, "mkdtemp", lambda prefix="": str(tmp_path))
    spec = importlib.util.spec_from_file_location("word_screen_log", _SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["word_screen_log"] = mod
    spec.loader.exec_module(mod)
    mod.vision_stub = vis
    mod.unread = tmp_path / "unread"
    mod.accurate_ok = False
    for d in (mod.shape, mod.read_at, mod.said, mod.last):
        d.clear()
    return mod


def _png(path: Path, width: int = 100) -> Path:
    """Minimal PNG-shaped bytes: only the IHDR width at bytes 16-20 is ever read."""
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR"
                     + struct.pack(">II", width, 40) + b"\x00\x08\x06\x00\x00\x00")
    return path


def _dialog(id=7, w=260, h=282, title="alert") -> dict:
    return {"id": id, "owner": "Microsoft Word", "w": w, "h": h, "layer": 8,
            "title": title, "on": True}


# --- vision(): an empty successful read must look like "no text", not like text ------

def test_vision_empty_result_is_none(wsl, tmp_path):
    wsl.vision_stub.returns["accurate"] = []
    assert wsl.vision(_png(tmp_path / "a.png"), "accurate") is None


def test_vision_failed_request_is_none(wsl, tmp_path):
    wsl.vision_stub.returns["accurate"] = None
    assert wsl.vision(_png(tmp_path / "a.png"), "accurate") is None


def test_ocr_falls_through_empty_accurate_to_tesseract(wsl, monkeypatch, tmp_path):
    wsl.accurate_ok = True
    wsl.vision_stub.returns["accurate"] = []  # accurate ran fine and read nothing
    monkeypatch.setattr(wsl, "tesseract", lambda png: "HELLO")
    assert wsl.ocr(_png(tmp_path / "a.png")) == "HELLO   (tesseract)"


def test_read_keeps_unread_png_when_nothing_reads(wsl, monkeypatch, tmp_path):
    monkeypatch.setattr(wsl, "TESSERACT", None)
    wsl.vision_stub.returns["fast"] = []  # every engine reads nothing
    png = _png(tmp_path / "a.png")
    text = wsl.read(png)
    assert text.startswith("<could not read")
    kept = list(wsl.unread.glob("*a.png"))
    assert len(kept) == 1, "an unreadable screenshot must be kept, not deleted"


def test_read_survives_cross_device_rename(wsl, monkeypatch, tmp_path):
    """$TMPDIR and the log dir can sit on different volumes: keep the evidence anyway."""
    monkeypatch.setattr(wsl, "TESSERACT", None)
    wsl.vision_stub.returns["fast"] = []
    png = _png(tmp_path / "a.png")

    def exdev(src, dst):
        raise OSError(errno.EXDEV, "cross-device link")

    monkeypatch.setattr(os, "rename", exdev)
    text = wsl.read(png)
    assert text.startswith("<could not read")
    assert len(list(wsl.unread.glob("*a.png"))) == 1


# --- tesseract(): bounded subprocesses, timeouts fall through, no _x3 litter --------

def _fake_run_calls(monkeypatch, wsl, sips=None, tesseract=None):
    """Replace subprocess.run inside the module; `sips`/`tesseract` are callables or exceptions."""
    calls = []

    def fake_run(cmd, **kw):
        calls.append((tuple(cmd), kw))
        action = sips if cmd[0] == "sips" else tesseract
        if isinstance(action, BaseException):
            raise action
        return action() if callable(action) else action

    monkeypatch.setattr(wsl.subprocess, "run", fake_run)
    return calls


def _ok(stdout=b"HI\n"):
    return types.SimpleNamespace(returncode=0, stdout=stdout, stderr=b"")


def test_tesseract_reads_and_cleans_up(wsl, monkeypatch, tmp_path):
    monkeypatch.setattr(wsl, "TESSERACT", "/opt/homebrew/bin/tesseract")
    png = _png(tmp_path / "alert.png")
    big = tmp_path / "alert_x3.png"

    def sips():
        big.write_bytes(b"x")
        return _ok(b"")

    calls = _fake_run_calls(monkeypatch, wsl, sips=sips, tesseract=lambda: _ok())
    assert wsl.tesseract(png) == "HI"
    assert not big.exists(), "the 3x upscale must not outlive the call"
    sips_call = next(kw for cmd, kw in calls if cmd[0] == "sips")
    assert sips_call.get("timeout"), "the sips call must be bounded too"
    tess_call = next(kw for cmd, kw in calls if cmd[0] != "sips")
    assert tess_call.get("timeout") == 30


def test_tesseract_timeout_falls_back_and_cleans_up(wsl, monkeypatch, tmp_path):
    monkeypatch.setattr(wsl, "TESSERACT", "/opt/homebrew/bin/tesseract")
    png = _png(tmp_path / "alert.png")
    big = tmp_path / "alert_x3.png"
    big.write_bytes(b"x")
    _fake_run_calls(monkeypatch, wsl, sips=lambda: _ok(b""),
                    tesseract=subprocess.TimeoutExpired(["tesseract"], 30))
    assert wsl.tesseract(png) is None, "a tesseract timeout must not kill the frame"
    assert not big.exists()


def test_sips_timeout_returns_none(wsl, monkeypatch, tmp_path):
    monkeypatch.setattr(wsl, "TESSERACT", "/opt/homebrew/bin/tesseract")
    png = _png(tmp_path / "alert.png")
    _fake_run_calls(monkeypatch, wsl, sips=subprocess.TimeoutExpired(["sips"], 10))
    assert wsl.tesseract(png) is None


# --- handle_frame(): a dialog is "read" only once a capture actually succeeded -------

def test_settled_dialog_not_marked_read_when_capture_fails(wsl, monkeypatch):
    w = _dialog()
    key = (w["title"], w["w"], w["h"])
    wsl.shape[w["id"]] = key  # same geometry as the previous poll: settled, read it
    monkeypatch.setattr(wsl, "shoot", lambda w: None)
    wsl.handle_frame({w["id"]: w}, io.StringIO())
    assert w["id"] not in wsl.read_at, "a failed capture must leave the dialog eligible for retry"


def test_settled_dialog_marked_read_after_usable_capture(wsl, monkeypatch, tmp_path):
    w = _dialog()
    key = (w["title"], w["w"], w["h"])
    wsl.shape[w["id"]] = key
    png = _png(tmp_path / "shot.png")
    monkeypatch.setattr(wsl, "shoot", lambda w: png)
    monkeypatch.setattr(wsl, "read", lambda p: "TEXT")
    fh = io.StringIO()
    wsl.handle_frame({w["id"]: w}, fh)
    assert wsl.read_at[w["id"]] == key
    assert "says: TEXT" in fh.getvalue()


def test_handoff_rerun_command_feeds_collect_fresh_stdout():
    """`collect` parses `<run>/word.stdout` (harvest.py): the recovery command must overwrite it.

    Without the redirect, a rerun pairs the fresh `word_pdf/` PDFs with the interrupted
    run's stale `word.stdout` and misclassifies every failure line in it.
    """
    doc = (Path(__file__).resolve().parents[1] / "docs" / "HANDOFF_LIVE_BENCH_HARVEST_20261017.md").read_text()
    line = next(l for l in doc.splitlines() if "word_pdf.py --src $R/word_in" in l)
    assert '> "$R/word.stdout" 2>&1' in line
