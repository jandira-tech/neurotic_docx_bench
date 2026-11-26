"""Run compare and PDF jobs on two long-lived Word processes.

One child owns the comparison Word and another owns the PDF Word. Each Word
stays open and is reused. A hung job is killed, including only the WINWORD
process that child started, and the next job starts a fresh one.
"""

from __future__ import annotations

import json
import logging
import os
import re
import queue
import shutil
import stat
import subprocess
import sys
import threading
import time
import uuid
from contextvars import ContextVar
from pathlib import Path

from word_endpoint.config import Settings
from word_endpoint.guard import GuardError, PreparedDocx, prepare_docx, sanitize_output_docx
from word_endpoint.paths import LOG_DIR, ROOT, WORK_ROOT
from word_endpoint.processes import process_name as _process_name, terminate_recorded

_HEX_DIR = re.compile(r"^[0-9a-f]{32}$")
_REPARSE = 0x400
REQUEST_ID = ContextVar("request_id", default="-")


class JobError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


class WordRunner:
    validates_output = True

    def __init__(self, settings: Settings, command_for=None, word_image: str = "winword.exe"):
        self.settings = settings
        self._slots = threading.BoundedSemaphore(settings.max_concurrent)
        self._closed = threading.Event()
        self._maintenance_thread = None
        self._maintenance_interval_s = 15
        self._locks = {
            "compare": threading.Lock(),
            "convert": threading.Lock(),
        }
        spawn = command_for or _default_worker_command
        self._lanes = {
            "compare": _Lane("compare", spawn, word_image),
            "convert": _Lane("convert", spawn, word_image),
        }

    def warm(self) -> None:
        for kind, lane in self._lanes.items():
            threading.Thread(
                target=self._warm_one,
                args=(kind, lane),
                name=f"warm-{kind}",
                daemon=True,
            ).start()
        if self._maintenance_thread is None:
            self._maintenance_thread = threading.Thread(target=self._maintain, name="word-maintenance", daemon=True)
            self._maintenance_thread.start()

    def _maintain(self) -> None:
        while not self._closed.wait(self._maintenance_interval_s):
            cleanup_old_work()
            for kind, lane in self._lanes.items():
                if self._closed.is_set():
                    return
                if self._locks[kind].acquire(blocking=False):
                    try:
                        lane.ensure(self.settings.job_timeout_s)
                    except JobError:
                        logging.exception("worker recovery failed kind=%s", kind)
                    finally:
                        self._locks[kind].release()

    def health(self) -> dict:
        lanes = {kind: lane.health() for kind, lane in self._lanes.items()}
        return {"status": "ok" if all(v["state"] in {"ready", "busy"} for v in lanes.values()) else "degraded",
                "workers": lanes}

    def _warm_one(self, kind: str, lane: "_Lane") -> None:
        try:
            lane.ensure(self.settings.job_timeout_s)
            logging.info("%s Word is ready", kind)
        except JobError:
            logging.exception("could not start %s Word", kind)

    def __call__(self, kind: str, files: dict[str, bytes]) -> bytes:
        lane_kind = "compare" if kind == "compare_pdf" else kind
        if lane_kind not in self._locks:
            raise JobError("word_failed")
        if self._closed.is_set() or not self._slots.acquire(blocking=False):
            raise JobError("busy")
        try:
            queued = time.monotonic()
            if not self._locks[lane_kind].acquire(timeout=self.settings.queue_timeout_s):
                raise JobError("busy")
            try:
                logging.info("job request=%s kind=%s queue_ms=%d", REQUEST_ID.get(), kind, (time.monotonic() - queued) * 1000)
                return self._execute(kind, files)
            finally:
                self._locks[lane_kind].release()
        finally:
            self._slots.release()

    def shutdown(self) -> None:
        self._closed.set()
        if self._maintenance_thread is not None:
            self._maintenance_thread.join(timeout=self.settings.job_timeout_s + 5)
        for lane in self._lanes.values():
            lane.stop()

    def _execute(self, kind: str, files: dict[str, bytes]) -> bytes:
        workdir = _make_workdir()
        try:
            started = time.monotonic()
            _write_inputs(kind, files, workdir)
            logging.info("job request=%s id=%s kind=%s input_ms=%d", REQUEST_ID.get(), workdir.name, kind, (time.monotonic() - started) * 1000)
            lane_kind = "compare" if kind == "compare_pdf" else kind
            total_bytes = sum(len(data) for data in files.values())
            return self._lanes[lane_kind].run(kind, workdir,
                                              job_timeout_for(self.settings, total_bytes))
        finally:
            _dispose(workdir, keep_log=False)


# Heavy but valid documents can need far more than the base budget. Large
# uploads get extra time instead of being killed mid-export at the deadline.
_EXTRA_TIMEOUT_PER_MB_S = 20
_EXTRA_TIMEOUT_FREE_MB = 2
_MAX_EXTRA_TIMEOUT_S = 180


def job_timeout_for(settings: Settings, total_bytes: int) -> int:
    """Scale the per-job timeout with the uploaded input size."""
    extra_mb = max(0.0, total_bytes / (1024 * 1024) - _EXTRA_TIMEOUT_FREE_MB)
    extra = min(_MAX_EXTRA_TIMEOUT_S, int(extra_mb * _EXTRA_TIMEOUT_PER_MB_S))
    return settings.job_timeout_s + extra


def _default_worker_command(kind: str) -> list[str]:
    code = (
        "import sys; "
        "sys.path.insert(0, sys.argv[1]); "
        "from word_endpoint.worker import main; "
        "raise SystemExit(main(['worker', 'serve', sys.argv[2]]))"
    )
    return [sys.executable, "-c", code, str(ROOT), kind]


class _Lane:
    def __init__(self, kind: str, command_for, word_image: str):
        self.kind = kind
        self._command_for = command_for
        self._image = word_image.lower()
        self._mu = threading.Lock()
        self._proc: subprocess.Popen[bytes] | None = None
        self._word_pid: int | None = None
        self._died = False
        self._lines: queue.Queue[tuple[str, bytes]] = queue.Queue()
        self._log = None
        self._state = "stopped"
        self._active_since: float | None = None
        self._restarts = 0
        # Set by stop() under _mu; _spawn checks it under _mu, so a warm-up
        # thread or a request still queued on this lane cannot start a Word
        # after shutdown has stopped it.
        self._closed = False

    def health(self) -> dict:
        proc = self._proc
        state = self._state
        if state in {"ready", "busy"} and (proc is None or proc.poll() is not None):
            state = "stopped"
        return {"state": state, "restarts": self._restarts,
                "active_seconds": round(time.monotonic() - self._active_since, 1) if self._active_since else 0}

    def ensure(self, timeout: float) -> None:
        with self._mu:
            if self._proc is not None and self._proc.poll() is None:
                try:
                    self._proc.stdin.write(b"ping\n")
                    self._proc.stdin.flush()
                    event, payload = self._lines.get(timeout=min(timeout, 5))
                    if event == "line" and payload.strip() == b"alive":
                        self._state = "ready"
                        return
                except (OSError, queue.Empty):
                    pass
            self._spawn(timeout)

    def run(self, kind: str, workdir: Path, timeout: float) -> bytes:
        with self._mu:
            deadline = time.monotonic() + timeout
            try:
                try:
                    return self._attempt(kind, workdir, timeout)
                except JobError as exc:
                    if exc.code in {"timeout", "corrupt", "password_protected", "unsafe_package", "active_content", "external_content"} or not self._died:
                        raise
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise JobError("timeout")
                return self._attempt(kind, workdir, remaining)
            finally:
                self._active_since = None
                if self._proc is not None and self._proc.poll() is None:
                    self._state = "ready"

    def _attempt(self, kind: str, workdir: Path, timeout: float) -> bytes:
        deadline = time.monotonic() + timeout
        self._died = False
        self._spawn_if_needed(timeout)
        self._state = "busy"
        self._active_since = time.monotonic()
        proc = self._proc
        if proc is None or proc.stdin is None:
            self._died = True
            raise JobError("word_failed")
        try:
            proc.stdin.write((kind + "\t" + str(workdir) + "\n").encode("ascii"))
            proc.stdin.flush()
        except (OSError, UnicodeEncodeError) as exc:
            self._died = True
            self._kill_locked()
            raise JobError("word_failed") from exc
        try:
            event, payload = self._lines.get(timeout=max(0, deadline - time.monotonic()))
        except queue.Empty:
            logging.warning("job id=%s kind=%s hit the deadline, killing the worker and WINWORD",
                            workdir.name, kind)
            salvaged = _try_output(kind, workdir)
            self._died = True
            self._kill_locked()
            if salvaged is not None:
                return salvaged
            raise JobError("timeout") from None
        if event != "line" or payload.strip() not in {b"done", b"dead"}:
            salvaged = _try_output(kind, workdir)
            self._died = True
            self._kill_locked()
            if salvaged is not None:
                return salvaged
            raise JobError("word_failed")
        died = payload.strip() == b"dead" or proc.poll() is not None
        if died:
            self._died = True
            self._kill_locked()
        result = _read_result(workdir)
        if not result.get("ok"):
            code = result.get("error") if isinstance(result.get("error"), str) else None
            raise JobError(code or "word_failed")
        started = time.monotonic()
        data = _load_output(kind, workdir)
        logging.info("job id=%s kind=%s output_ms=%d output_bytes=%d", workdir.name, kind, (time.monotonic() - started) * 1000, len(data))
        return data

    def stop(self) -> None:
        with self._mu:
            self._closed = True
            proc = self._proc
            if proc is not None and proc.poll() is None and proc.stdin is not None:
                try:
                    proc.stdin.write(b"quit\n")
                    proc.stdin.flush()
                    proc.wait(timeout=10)
                except (OSError, subprocess.TimeoutExpired):
                    pass
            self._kill_locked()

    def _spawn_if_needed(self, timeout: float) -> None:
        if self._proc is not None and self._proc.poll() is None:
            return
        self._spawn(timeout)

    def _spawn(self, timeout: float) -> None:
        if self._closed:
            raise JobError("busy")
        try:
            self._spawn_impl(timeout)
        except OSError as exc:
            self._kill_locked()
            logging.exception("worker startup failed kind=%s", self.kind)
            raise JobError("word_failed") from exc

    def _spawn_impl(self, timeout: float) -> None:
        self._kill_locked()
        self._state = "starting"
        self._restarts += 1
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        self._log = open(LOG_DIR / f"{self.kind}-stderr.log", "ab")
        proc = subprocess.Popen(
            self._command_for(self.kind),
            cwd=str(ROOT),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=self._log,
            shell=False,
        )
        self._proc = proc
        self._lines = queue.Queue()
        lines = self._lines

        def read() -> None:
            assert proc.stdout is not None
            while True:
                chunk = proc.stdout.readline()
                if not chunk:
                    lines.put(("eof", b""))
                    return
                lines.put(("line", chunk))

        threading.Thread(target=read, name=f"read-{self.kind}", daemon=True).start()
        try:
            event, payload = self._lines.get(timeout=timeout)
        except queue.Empty:
            self._kill_locked()
            raise JobError("word_failed") from None
        pid = _ready_pid(event, payload)
        if pid is None or _process_name(pid).lower() != self._image:
            self._kill_locked()
            raise JobError("word_failed")
        self._word_pid = pid
        self._state = "ready"

    def _kill_locked(self) -> None:
        proc = self._proc
        word_pid = self._word_pid
        self._proc = None
        self._word_pid = None
        self._state = "stopped"
        _kill_recorded(proc, WORK_ROOT / f"{self.kind}.word.pid", word_pid, self._image)
        if self._log is not None:
            self._log.close()
            self._log = None


def cleanup_old_work(max_age_s: int = 86400) -> None:
    if not WORK_ROOT.exists():
        return
    cutoff = time.time() - max_age_s
    for child in WORK_ROOT.iterdir():
        if not child.is_dir() or _HEX_DIR.fullmatch(child.name) is None:
            continue
        try:
            if child.stat().st_mtime < cutoff:
                shutil.rmtree(child, ignore_errors=True)
        except OSError:
            continue


def _make_workdir() -> Path:
    WORK_ROOT.mkdir(parents=True, exist_ok=True)
    workdir = (WORK_ROOT / uuid.uuid4().hex).resolve()
    workdir.relative_to(WORK_ROOT.resolve())
    workdir.mkdir(mode=0o700)
    return workdir


def _write_inputs(kind: str, files: dict[str, bytes], workdir: Path) -> None:
    expected = {
        "convert": {"document": "document.docx"},
        "compare": {"original": "original.docx", "revised": "revised.docx"},
        "compare_pdf": {"original": "original.docx", "revised": "revised.docx"},
    }[kind]
    if set(files) != set(expected):
        raise JobError("word_failed")
    for key, name in expected.items():
        blob = files[key]
        try:
            blob = blob if isinstance(blob, PreparedDocx) else prepare_docx(blob)
        except GuardError as exc:
            logging.warning("guard rejected code=%s reason=%s part=%r", exc.code, exc.reason, exc.part)
            raise JobError(exc.code) from exc
        target = workdir / name
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_BINARY", 0)
        descriptor = os.open(target, flags, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(blob)


def _load_output(kind: str, workdir: Path) -> bytes:
    pdf = kind in {"convert", "compare_pdf"}
    name = "output.pdf" if pdf else "output.docx"
    path = (workdir / name).resolve()
    path.relative_to(workdir.resolve())
    info = _regular_file(path)
    if info.st_size < 64:
        raise JobError("no_output")
    if info.st_size > 80 * 1024 * 1024:
        raise JobError("word_failed")
    data = path.read_bytes()
    if pdf:
        if not data.startswith(b"%PDF-"):
            raise JobError("convert_failed")
        return data
    try:
        return sanitize_output_docx(data)
    except GuardError as exc:
        code = "word_failed" if exc.code == "too_large" else exc.code
        raise JobError(code) from exc


def _try_output(kind: str, workdir: Path) -> bytes | None:
    try:
        result = _read_result(workdir)
    except JobError:
        return None
    if not result.get("ok"):
        return None
    try:
        return _load_output(kind, workdir)
    except JobError:
        return None


def _read_result(workdir: Path) -> dict:
    path = workdir / "result.json"
    if not path.is_file():
        raise JobError("word_failed")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise JobError("word_failed") from exc
    if not isinstance(data, dict):
        raise JobError("word_failed")
    return data


def _regular_file(path: Path) -> os.stat_result:
    try:
        info = path.stat()
    except OSError as exc:
        raise JobError("no_output") from exc
    if not stat.S_ISREG(info.st_mode):
        raise JobError("word_failed")
    attributes = getattr(info, "st_file_attributes", 0)
    if attributes & _REPARSE:
        raise JobError("word_failed")
    return info


def _dispose(workdir: Path, *, keep_log: bool) -> None:
    log_path = workdir / "worker.log"
    if keep_log and log_path.exists():
        try:
            text = log_path.read_text(encoding="utf-8", errors="replace")[-4000:]
        except OSError:
            text = ""
        if text.strip():
            logging.info("worker %s: %s", workdir.name, text)
    for _ in range(5):
        try:
            shutil.rmtree(workdir)
            return
        except OSError:
            time.sleep(0.2)
    logging.warning("could not remove %s", workdir)


def _ready_pid(event: str, payload: bytes) -> int | None:
    if event != "line":
        return None
    parts = payload.decode("ascii", "replace").split()
    if len(parts) != 2 or parts[0] != "ready" or not parts[1].isdigit():
        return None
    pid = int(parts[1])
    if pid <= 4:
        return None
    return pid


def _kill_recorded(
    proc: subprocess.Popen[bytes] | None,
    pid_file: Path,
    remembered: int | None,
    image: str,
) -> None:
    word_pid = remembered if remembered and remembered > 4 else _pid_from_file(pid_file)
    if word_pid is not None:
        terminate_recorded(word_pid, image)
    try:
        pid_file.unlink(missing_ok=True)
    except OSError:
        pass
    if proc is not None and proc.poll() is None:
        proc.kill()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    if proc is not None:
        for stream in (proc.stdin, proc.stdout):
            if stream is not None:
                try:
                    stream.close()
                except OSError:
                    pass


def _pid_from_file(path: Path) -> int | None:
    try:
        text = path.read_text(encoding="ascii").strip()
    except OSError:
        return None
    if not text.isdigit():
        return None
    pid = int(text)
    if pid <= 4 or _process_name(pid).lower() != "winword.exe":
        return None
    return pid


