"""Drive the shipped runner and handler. The peer is not a reimplementation of run()."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from pathlib import Path

from tests.factory import encode_form, make_docx
from tests.test_server import request
from word_endpoint.config import Settings
from word_endpoint.responses import PUBLIC
from word_endpoint.runner import JobError, WordRunner, _load_output
from word_endpoint.server import create_server
from word_endpoint.worker import lane_reusable


ROOT = Path(__file__).resolve().parents[1]
PEER = ROOT / "tests" / "protocol_peer.py"


def _alive(pid: int) -> bool:
    from word_endpoint.processes import process_name
    return bool(process_name(pid))


def _exit_waiter(test: unittest.TestCase, pid: int):
    """A waitable handle on a process known to be alive now. _alive() reads a
    failed lookup as "exited"; the handle is signalled only when the process
    has actually terminated, and it keeps the pid from being reused."""
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE
    test.assertTrue(handle, f"could not open a waitable handle on pid {pid}")
    test.addCleanup(kernel.CloseHandle, handle)

    def exited(seconds: float) -> bool:
        return kernel.WaitForSingleObject(handle, int(seconds * 1000)) == 0  # WAIT_OBJECT_0
    test.assertFalse(exited(0), f"pid {pid} had already exited")
    return exited


class HandlerErrorTests(unittest.TestCase):
    def test_job_errors_use_the_public_catalog(self):
        token = "t" * 40
        content_type, payload = encode_form(
            [("document", "a.docx", make_docx(["Hello"]))]
        )
        codes = (
            "busy",
            "timeout",
            "word_failed",
            "corrupt",
            "compare_failed",
            "convert_failed",
            "no_output",
        )

        class Raiser:
            def __init__(self, code: str):
                self.code = code

            def __call__(self, kind, files):
                raise JobError(self.code)

        for code in codes:
            httpd = create_server(
                Settings(token=token, host="127.0.0.1", port=0, queue_timeout_s=1, job_timeout_s=5),
                Raiser(code),
            )
            threading.Thread(target=httpd.serve_forever, daemon=True).start()
            base = f"http://127.0.0.1:{httpd.server_address[1]}"
            status, body = request(
                base,
                "POST",
                "/v1/convert",
                payload,
                {"Authorization": f"Bearer {token}", "Content-Type": content_type},
            )
            parsed = json.loads(body)
            self.assertEqual(status, PUBLIC[code][0], code)
            self.assertEqual(parsed["code"], code)
            self.assertEqual(parsed["error"], PUBLIC[code][1])
            self.assertTrue(parsed["request_id"])
            self.assertNotIn(b"Traceback", body)
            self.assertNotIn(b"word-endpoint", body.lower())
            httpd.shutdown()
            httpd.server_close()


class OutputMappingTests(unittest.TestCase):
    def test_comparison_output_may_exceed_the_upload_limit(self):
        from tests.factory import standard_files
        workdir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, workdir, True)
        files = standard_files(["Comparison"])
        files["[Content_Types].xml"] = files["[Content_Types].xml"].replace("</Types>", '<Default Extension="bin" ContentType="application/octet-stream"/></Types>')
        files["word/media/large.bin"] = b"x" * (21 * 1024 * 1024)
        import zipfile
        with zipfile.ZipFile(workdir / "output.docx", "w", compression=zipfile.ZIP_STORED) as archive:
            for name, data in files.items():
                archive.writestr(name, data)
        self.assertGreater(len(_load_output("compare", workdir)), 20 * 1024 * 1024)

    def test_oversized_output_is_not_an_upload_error(self):
        workdir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, workdir, True)
        target = workdir / "output.pdf"
        with target.open("wb") as handle:
            handle.write(b"%PDF-1.4\n")
            handle.seek(80 * 1024 * 1024)
            handle.write(b"x")
        with self.assertRaises(JobError) as caught:
            _load_output("convert", workdir)
        self.assertEqual(caught.exception.code, "word_failed")

    def test_dirty_word_is_not_reusable(self):
        self.assertFalse(lane_reusable(True, 1))
        self.assertFalse(lane_reusable(True, None))
        self.assertFalse(lane_reusable(False, 0))
        self.assertTrue(lane_reusable(True, 0))


class LaneSupervisionTests(unittest.TestCase):
    def test_comparison_pdf_uses_the_existing_comparison_lane_and_lock(self):
        control = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, control, True)
        self.enterContext(patch('word_endpoint.runner.WORK_ROOT', control / 'work'))
        self.enterContext(patch('word_endpoint.runner.LOG_DIR', control / 'logs'))
        runner = WordRunner(Settings(token='t' * 40, queue_timeout_s=.05, job_timeout_s=5),
                            command_for=lambda kind: [sys.executable, str(PEER), kind, str(control)],
                            word_image='python.exe')
        self.addCleanup(runner.shutdown)
        files = {'original': make_docx(['100']), 'revised': make_docx(['250'])}
        with runner._locks['compare']:
            with self.assertRaises(JobError) as caught:
                runner('compare_pdf', files)
        self.assertEqual(caught.exception.code, 'busy')
        self.assertTrue(runner('compare_pdf', files).startswith(b'%PDF-'))
        self.assertEqual(int((control / 'compare.count').read_text()), 1)
        self.assertFalse((control / 'convert.pid').exists())
        self.assertEqual(set(runner._lanes), {'compare', 'convert'})
    def test_log_access_failure_is_reported_and_the_lane_can_retry(self):
        control = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, control, True)
        self.enterContext(patch("word_endpoint.runner.WORK_ROOT", control / "work"))
        self.enterContext(patch("word_endpoint.runner.LOG_DIR", control / "logs"))
        runner = WordRunner(Settings(token="t" * 40, job_timeout_s=3),
                            command_for=lambda kind: [sys.executable, str(PEER), kind, str(control)],
                            word_image="python.exe")
        self.addCleanup(runner.shutdown)
        lane = runner._lanes["convert"]
        with patch("word_endpoint.runner.open", side_effect=PermissionError("denied")), self.assertLogs(level="ERROR"):
            with self.assertRaises(JobError) as caught:
                lane.ensure(3)
        self.assertEqual(caught.exception.code, "word_failed")
        self.assertEqual(lane.health()["state"], "stopped")
        lane.ensure(3)
        self.assertEqual(lane.health()["state"], "ready")

    def test_idle_failed_worker_recovers_without_a_customer_request(self):
        control = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, control, True)
        self.enterContext(patch("word_endpoint.runner.WORK_ROOT", control / "work"))
        self.enterContext(patch("word_endpoint.runner.LOG_DIR", control / "logs"))
        runner = WordRunner(Settings(token="t" * 40, job_timeout_s=3),
                            command_for=lambda kind: [sys.executable, str(PEER), kind, str(control)],
                            word_image="python.exe")
        self.addCleanup(runner.shutdown)
        runner._maintenance_interval_s = 0.1
        runner.warm()
        deadline = time.monotonic() + 5
        while runner.health()["status"] != "ok" and time.monotonic() < deadline:
            time.sleep(0.05)
        self.assertEqual(runner.health()["status"], "ok")
        compare_pid = runner._lanes["compare"]._word_pid
        convert = runner._lanes["convert"]
        old_pid = convert._word_pid
        old_exited = _exit_waiter(self, old_pid)
        convert._proc.kill()
        convert._proc.wait(timeout=2)
        deadline = time.monotonic() + 5
        # Recovery clears the PID before finishing teardown. Wait for the
        # replacement to be ready, rather than treating that interim None as it.
        while (convert._word_pid in (None, old_pid) or convert.health()['state'] != 'ready') and time.monotonic() < deadline:
            time.sleep(0.05)
        self.assertNotEqual(convert._word_pid, old_pid)
        self.assertEqual(convert.health()['state'], 'ready')
        self.assertTrue(old_exited(5))
        self.assertEqual(runner._lanes["compare"]._word_pid, compare_pid)
        self.assertTrue(_alive(compare_pid))

    def test_dead_lane_is_reaped_and_the_other_lane_continues(self):
        control = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, control, True)
        self.enterContext(patch("word_endpoint.runner.WORK_ROOT", control / "work"))
        self.enterContext(patch("word_endpoint.runner.LOG_DIR", control / "logs"))
        runner = WordRunner(
            Settings(token="t" * 40, host="127.0.0.1", port=0, queue_timeout_s=0.4, job_timeout_s=2),
            command_for=lambda kind: [sys.executable, str(PEER), kind, str(control)],
            word_image="python.exe",
        )
        self.addCleanup(runner.shutdown)
        (control / "compare.mode").write_text("ok", encoding="ascii")
        (control / "convert.mode").write_text("ok", encoding="ascii")
        original = make_docx(["The fee is 100 dollars."])
        revised = make_docx(["The fee is 250 dollars."])
        document = make_docx(["Hello"])
        errors: list[BaseException] = []

        def call(kind, files):
            try:
                return runner(kind, files)
            except BaseException as exc:
                errors.append(exc)
                return b""

        threads = [
            threading.Thread(target=call, args=("compare", {"original": original, "revised": revised})),
            threading.Thread(target=call, args=("convert", {"document": document})),
        ]
        for thread in threads:
            thread.start()
        self.assertTrue(_wait_file(control / "compare.started", 5))
        self.assertTrue(_wait_file(control / "convert.started", 5))
        for thread in threads:
            thread.join(5)
        self.assertEqual(errors, [])
        compare_pid = int((control / "compare.pid").read_text(encoding="ascii"))
        first_convert = int((control / "convert.pid").read_text(encoding="ascii"))
        self.assertTrue(_alive(compare_pid))
        self.assertTrue(_alive(first_convert))
        first_convert_exited = _exit_waiter(self, first_convert)

        (control / "convert.started").unlink()
        (control / "convert.mode").write_text("hang", encoding="ascii")
        hung = threading.Thread(target=call, args=("convert", {"document": document}))
        hung.start()
        self.assertTrue(_wait_file(control / "convert.started", 3))
        with self.assertRaises(JobError) as busy:
            runner("convert", {"document": document})
        self.assertEqual(busy.exception.code, "busy")
        hung.join(8)
        self.assertTrue(any(isinstance(item, JobError) and item.code == "timeout" for item in errors))
        self.assertTrue(first_convert_exited(5))
        self.assertTrue(_alive(compare_pid))

        (control / "convert.mode").write_text("ok", encoding="ascii")
        (control / "convert.pid").unlink()
        produced = runner("convert", {"document": document})
        self.assertTrue(produced.startswith(b"%PDF-"))
        second_convert = int((control / "convert.pid").read_text(encoding="ascii"))
        self.assertNotEqual(second_convert, first_convert)
        self.assertTrue(_alive(second_convert))
        self.assertTrue(_alive(compare_pid))
        self.assertGreaterEqual(int((control / "convert.count").read_text(encoding="ascii")), 2)


def _wait_file(path: Path, seconds: float) -> bool:
    deadline = time.time() + seconds
    while time.time() < deadline:
        if path.exists():
            return True
        time.sleep(0.05)
    return False


if __name__ == "__main__":
    unittest.main()
