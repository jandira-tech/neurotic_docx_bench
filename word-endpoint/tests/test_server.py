import json
import os
import threading
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch

from tests.factory import encode_form, make_docx
from word_endpoint.config import Settings, load_settings
from word_endpoint.runner import JobError, WordRunner
from word_endpoint.server import create_server


class FakeRunner:
    def __init__(self, result: bytes | None = None):
        self.calls: list[tuple[str, dict[str, int]]] = []
        self.result = result or (b"%PDF-1.4\n" + b"a" * 80 + b"\n%%EOF\n")

    def __call__(self, kind: str, files: dict[str, bytes]) -> bytes:
        self.calls.append((kind, {key: len(value) for key, value in files.items()}))
        if kind == "compare":
            return make_docx(["compared"])
        return self.result


def request(base: str, method: str, path: str, data: bytes | None = None, headers: dict | None = None):
    req = urllib.request.Request(base + path, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        with exc:
            return exc.code, exc.read()


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.runner = FakeRunner()
        self.httpd = create_server(self.settings(1000), self.runner)
        self.addCleanup(self.httpd.server_close)
        self.addCleanup(self.httpd.shutdown)
        thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        thread.start()
        self.base = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        self.token = "t" * 40

    def settings(self, rate: int) -> Settings:
        return Settings(
            token="t" * 40,
            host="127.0.0.1",
            port=0,
            rate_limit_per_minute=rate,
            queue_timeout_s=0.1,
            job_timeout_s=5,
        )

    def auth(self, extra: dict | None = None) -> dict:
        headers = {"Authorization": f"Bearer {self.token}"}
        if extra:
            headers.update(extra)
        return headers

    def test_health_and_unknown_route(self):
        status, body = request(self.base, "GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), {"status": "ok"})
        status, body = request(self.base, "GET", "/missing")
        self.assertEqual(status, 404)
        self.assertEqual(json.loads(body)["code"], "not_found")

    def test_head_health_routes_match_get_status_without_a_body(self):
        for state in ('ok', 'degraded'):
            self.runner.health = lambda: {'status': state, 'workers': {}}
            for path in ('/live', '/health', '/ready', '/missing', '/health?token=secret'):
                with self.subTest(state=state, path=path):
                    status, get_body = request(self.base, 'GET', path)
                    req = urllib.request.Request(self.base + path, method='HEAD')
                    try:
                        response = urllib.request.urlopen(req, timeout=5)
                    except urllib.error.HTTPError as exc:
                        response = exc
                    with response:
                        self.assertEqual(response.code, status)
                        self.assertEqual(response.read(), b'')
                        # RFC 9110 9.3.2: the length a GET would send, or nothing.
                        self.assertEqual(response.headers['Content-Length'], str(len(get_body)))
                        self.assertTrue(response.headers['X-Request-Id'])

    def test_requires_bearer_token(self):
        content_type, payload = encode_form(
            [("document", "secret-name.docx", make_docx(["Hello"]))]
        )
        # Repeated uploads reproduce Windows resets when a rejection closes
        # the connection with unread request bytes.
        for _ in range(10):
            status, body = request(
                self.base,
                "POST",
                "/v1/convert",
                payload,
                {"Content-Type": content_type},
            )
            self.assertEqual(status, 401)
            self.assertEqual(json.loads(body)["code"], "unauthorized")
            self.assertNotIn(b"secret-name", body)
        self.assertEqual(self.runner.calls, [])

    def test_rejects_query_token_and_dde_without_calling_word(self):
        status, body = request(self.base, "POST", "/v1/convert?token=secret", b"x", self.auth())
        self.assertEqual(status, 400)
        self.assertEqual(json.loads(body)["code"], "query_rejected")
        content_type, payload = encode_form(
            [
                (
                    "document",
                    "secret-name.docx",
                    make_docx(
                        ["Hello"],
                        "<w:p><w:r><w:instrText>DDEAUTO calc</w:instrText></w:r></w:p>",
                    ),
                )
            ]
        )
        status, body = request(
            self.base,
            "POST",
            "/v1/convert",
            payload,
            self.auth({"Content-Type": content_type}),
        )
        self.assertEqual(status, 400)
        self.assertEqual(json.loads(body)["code"], "active_content")
        self.assertNotIn(b"secret-name", body)
        self.assertNotIn(b"Traceback", body)
        self.assertEqual(self.runner.calls, [])

    def test_convert_and_compare_return_files(self):
        content_type, payload = encode_form(
            [("document", "a.docx", make_docx(["Hello"]))]
        )
        status, body = request(
            self.base,
            "POST",
            "/v1/convert",
            payload,
            self.auth({"Content-Type": content_type}),
        )
        self.assertEqual(status, 200)
        self.assertTrue(body.startswith(b"%PDF-"))
        self.assertEqual(self.runner.calls[0][0], "convert")
        content_type, payload = encode_form(
            [
                ("original", "a.docx", make_docx(["100"])),
                ("revised", "b.docx", make_docx(["250"])),
            ]
        )
        status, body = request(
            self.base,
            "POST",
            "/v1/compare",
            payload,
            self.auth({"Content-Type": content_type}),
        )
        self.assertEqual(status, 200)
        self.assertTrue(body.startswith(b"PK"))

    def test_bad_runner_output_is_not_returned(self):
        self.runner.result = b"hello"
        content_type, payload = encode_form(
            [("document", "a.docx", make_docx(["Hello"]))]
        )
        status, body = request(
            self.base,
            "POST",
            "/v1/convert",
            payload,
            self.auth({"Content-Type": content_type}),
        )
        self.assertEqual(status, 500)
        self.assertEqual(json.loads(body)["code"], "convert_failed")
        self.assertNotIn(b"hello", body)

    def test_comparison_pdf_validates_inputs_and_output_and_requires_auth(self):
        content_type, payload = encode_form([
            ('original', 'original.docx', make_docx(['100'])),
            ('revised', 'revised.docx', make_docx(['250']))])
        headers = {'Content-Type': content_type}
        status, _ = request(self.base, 'POST', '/v1/compare-pdf', payload, headers)
        self.assertEqual(status, 401)
        self.assertEqual(self.runner.calls, [])
        status, body = request(self.base, 'POST', '/v1/compare-pdf', payload, self.auth(headers))
        self.assertEqual(status, 200)
        self.assertTrue(body.startswith(b'%PDF-'))
        self.assertEqual(self.runner.calls[-1][0], 'compare_pdf')
        self.runner.result = make_docx(['A DOCX must not be returned as a PDF.'])
        status, body = request(self.base, 'POST', '/v1/compare-pdf', payload, self.auth(headers))
        self.assertEqual(status, 500)
        self.assertEqual(json.loads(body)['code'], 'convert_failed')
        content_type, payload = encode_form([
            ('original', 'original.docx', make_docx(['100'])),
            ('revised', 'revised.docx', make_docx(['250'], '<w:p><w:r><w:instrText>DDEAUTO calc</w:instrText></w:r></w:p>'))])
        calls = len(self.runner.calls)
        status, body = request(self.base, 'POST', '/v1/compare-pdf', payload, self.auth({'Content-Type': content_type}))
        self.assertEqual(status, 400)
        self.assertEqual(json.loads(body)['code'], 'active_content')
        self.assertEqual(len(self.runner.calls), calls)

    def test_comparison_pdf_requires_both_documents(self):
        content_type, payload = encode_form([('original', 'original.docx', make_docx(['100']))])
        status, body = request(self.base, 'POST', '/v1/compare-pdf', payload, self.auth({'Content-Type': content_type}))
        self.assertEqual(status, 400)
        self.assertEqual(json.loads(body)['code'], 'missing_compare_files')
        self.assertEqual(self.runner.calls, [])

    def test_refuses_public_bind_and_short_token(self):
        with self.assertRaises(RuntimeError):
            create_server(Settings(token="t" * 40, host="0.0.0.0", port=0), FakeRunner())
        with self.assertRaises(RuntimeError):
            create_server(Settings(token="short", host="127.0.0.1", port=0), FakeRunner())
        # Long enough, but no client can send it as a bearer credential.
        with self.assertRaises(RuntimeError):
            create_server(Settings(token="\u0436" * 40, host="127.0.0.1", port=0), FakeRunner())

    def test_load_settings_rejects_a_token_outside_the_bearer_grammar(self):
        for token in ("\u0436" * 40, "a" * 39 + "!", "=" + "a" * 39):
            with self.subTest(token=token), patch.dict(os.environ, {"WORD_API_TOKEN": token}), \
                    patch("word_endpoint.config.load_dotenv"), self.assertRaises(SystemExit):
                load_settings()

    def test_unauthorized_posts_cannot_spend_the_job_quota(self):
        httpd = create_server(self.settings(2), FakeRunner())
        self.addCleanup(httpd.server_close)
        self.addCleanup(httpd.shutdown)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{httpd.server_address[1]}"
        content_type, payload = encode_form(
            [("document", "a.docx", make_docx(["Hello"]))]
        )
        headers = {"Content-Type": content_type}
        first, _ = request(base, "POST", "/v1/convert", payload, headers)
        second, _ = request(base, "POST", "/v1/convert", payload, headers)
        third, body = request(base, "POST", "/v1/convert", payload, headers)
        self.assertEqual(first, 401)
        self.assertEqual(second, 401)
        self.assertEqual(third, 429)
        self.assertEqual(json.loads(body)["code"], "rate_limited")
        health, _ = request(base, "GET", "/health")
        self.assertEqual(health, 200)
        # The failed attempts had their own budget: authorized jobs still get
        # the whole quota, and only they spend it.
        authorized = dict(headers, Authorization=f"Bearer {self.token}")
        statuses = [request(base, "POST", "/v1/convert", payload, authorized)[0] for _ in range(3)]
        self.assertEqual(statuses, [200, 200, 429])

    def test_placeholder_token_is_rejected(self):
        previous = os.environ.get("WORD_API_TOKEN")
        os.environ["WORD_API_TOKEN"] = "replace-with-at-least-32-random-characters"
        try:
            with patch("word_endpoint.config.load_dotenv"), self.assertRaises(SystemExit):
                load_settings()
        finally:
            if previous is None:
                os.environ.pop("WORD_API_TOKEN", None)
            else:
                os.environ["WORD_API_TOKEN"] = previous

    def test_runner_slot_rejects_a_second_job(self):
        base = self.settings(10)
        runner = WordRunner(
            Settings(
                token=base.token,
                host=base.host,
                port=base.port,
                rate_limit_per_minute=base.rate_limit_per_minute,
                queue_timeout_s=base.queue_timeout_s,
                job_timeout_s=base.job_timeout_s,
                max_concurrent=1,
            )
        )
        started = threading.Event()
        release = threading.Event()

        def hold(kind, files):
            started.set()
            release.wait(2)
            return b"%PDF-1.4\n" + b"x" * 80

        runner._execute = hold
        thread = threading.Thread(target=lambda: runner("convert", {"document": b"a"}))
        thread.start()
        self.assertTrue(started.wait(2))
        with self.assertRaises(JobError) as caught:
            runner("convert", {"document": b"b"})
        self.assertEqual(caught.exception.code, "busy")
        release.set()
        thread.join(2)

    def test_upload_admission_rejects_before_reading_and_releases_after_errors(self):
        import socket
        self.assertTrue(self.httpd.app.admission.acquire(blocking=False))
        # Occupy the remaining slots. Send headers but never an upload body:
        # overload must be rejected immediately rather than waiting for data.
        for _ in range(self.httpd.app.settings.max_concurrent - 1):
            self.assertTrue(self.httpd.app.admission.acquire(blocking=False))
        try:
            with socket.create_connection(self.httpd.server_address, timeout=2) as sock:
                sock.sendall((f"POST /v1/convert HTTP/1.1\r\nHost: localhost\r\nAuthorization: Bearer {self.token}\r\nContent-Length: 1000\r\nContent-Type: multipart/form-data\r\n\r\n").encode())
                self.assertIn(b"503", sock.recv(4096).split(b"\r\n")[0])
        finally:
            for _ in range(self.httpd.app.settings.max_concurrent):
                self.httpd.app.admission.release()
        status, _ = request(self.base, "POST", "/v1/convert", b"invalid", self.auth({"Content-Type": "bad"}))
        self.assertEqual(status, 400)
        # Every permit must come back, not just one of them: with four
        # permits, one leaked by the error path would still let a POST through.
        self.assertTrue(self._all_admission_permits_free())
        content_type, payload = encode_form([("document", "a.docx", make_docx(["Hello"]))])
        status, _ = request(self.base, "POST", "/v1/convert", payload, self.auth({"Content-Type": content_type}))
        self.assertEqual(status, 200)

    def _all_admission_permits_free(self, timeout: float = 2.0) -> bool:
        import time
        admission, total = self.httpd.app.admission, self.httpd.app.settings.max_concurrent
        deadline = time.monotonic() + timeout
        while True:
            taken = 0
            while taken < total and admission.acquire(blocking=False):
                taken += 1
            for _ in range(taken):
                admission.release()
            # The handler releases its permit just after the response is sent.
            if taken == total or time.monotonic() > deadline:
                return taken == total
            time.sleep(0.01)

    def test_malformed_request_target_gets_a_controlled_rejection(self):
        import socket
        with socket.create_connection(self.httpd.server_address, timeout=2) as sock:
            sock.sendall(b"GET http://[::1/live HTTP/1.1\r\nHost: localhost\r\n\r\n")
            status_line = sock.recv(4096).split(b"\r\n")[0]
        self.assertIn(b"404", status_line)
        status, _ = request(self.base, "GET", "/live")
        self.assertEqual(status, 200)

    def test_readiness_can_fail_while_http_liveness_stays_up(self):
        self.runner.health = lambda: {"status": "degraded", "workers": {"compare": {"state": "stopped"}}}
        status, body = request(self.base, "GET", "/ready")
        self.assertEqual(status, 503)
        self.assertEqual(json.loads(body)["status"], "degraded")
        status, body = request(self.base, "GET", "/health")
        self.assertEqual(status, 200)
        self.assertFalse(json.loads(body)["ready"])
        status, _ = request(self.base, "GET", "/live")
        self.assertEqual(status, 200)

    def test_concurrency_limit_applies_across_compare_and_convert(self):
        runner = WordRunner(Settings(token="t" * 40, max_concurrent=1))
        started, release = threading.Event(), threading.Event()
        def hold(kind, files):
            started.set()
            release.wait(2)
            return b"ok"
        runner._execute = hold
        thread = threading.Thread(target=lambda: runner("compare", {}))
        thread.start()
        try:
            self.assertTrue(started.wait(2))
            with self.assertRaises(JobError) as caught:
                runner("convert", {})
            self.assertEqual(caught.exception.code, "busy")
        finally:
            release.set()
            thread.join(2)

    def test_slow_connections_cannot_create_unbounded_handler_threads(self):
        import socket
        count = self.httpd.app.settings.max_concurrent + 16
        for _ in range(count):
            self.assertTrue(self.httpd.connections.acquire(blocking=False))
        try:
            with socket.create_connection(self.httpd.server_address, timeout=2) as sock:
                self.assertIn(b"503", sock.recv(4096).split(b"\r\n")[0])
        finally:
            for _ in range(count):
                self.httpd.connections.release()

    def test_a_body_dripped_slowly_still_times_out_at_the_upload_deadline(self):
        # Each byte comes well inside the per-read timeout, so only a deadline
        # checked around every socket read can end the upload.
        import socket
        import time
        content_type, body = encode_form([("document", "a.docx", make_docx("A"))])
        head = (f"POST /v1/convert HTTP/1.1\r\nHost: x\r\nAuthorization: Bearer {self.token}\r\n"
                f"Content-Type: {content_type}\r\nContent-Length: {len(body)}\r\n\r\n").encode("ascii")
        with patch("word_endpoint.server.UPLOAD_DEADLINE_S", 1.0), \
                socket.create_connection(self.httpd.server_address, timeout=5) as sock:
            sock.sendall(head)
            sock.settimeout(0.2)
            started = time.monotonic()
            reply = b""
            for byte in body[:40]:
                try:
                    sock.sendall(bytes([byte]))
                except OSError:
                    break
                try:
                    reply = sock.recv(4096)
                except TimeoutError:
                    continue
                except ConnectionResetError:
                    pass
                break
            elapsed = time.monotonic() - started
            sock.settimeout(2)
            # A byte dripped after the server answered and closed draws a
            # reset; that ends the stream. A reset that destroyed the answer
            # before it was read leaves no 504 below, so it still fails.
            try:
                while chunk := sock.recv(4096):
                    reply += chunk
            except ConnectionResetError:
                pass
        self.assertIn(b" 504 ", reply.split(b"\r\n")[0])
        self.assertIn(b'"code": "timeout"', reply)
        self.assertLess(elapsed, 4.0)

    def test_a_timed_out_upload_is_not_logged_as_an_internal_failure(self):
        # After the deadline the drain read a socket that had timed out, which
        # raises a plain OSError; it escaped to _dispatch as "request failed"
        # with a traceback (MiniMax review).
        import socket
        import time
        content_type, body = encode_form([("document", "a.docx", make_docx("A"))])
        head = (f"POST /v1/convert HTTP/1.1\r\nHost: x\r\nAuthorization: Bearer {self.token}\r\n"
                f"Content-Type: {content_type}\r\nContent-Length: {len(body)}\r\n\r\n").encode("ascii")
        with self.assertLogs(level="INFO") as logs, \
                patch("word_endpoint.server.UPLOAD_DEADLINE_S", 0.5), \
                socket.create_connection(self.httpd.server_address, timeout=5) as sock:
            sock.sendall(head + body[:10])
            sock.settimeout(3)
            reply = b""
            while chunk := sock.recv(4096):
                reply += chunk
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline and not any(" POST /v1/convert " in line for line in logs.output):
                time.sleep(0.05)
        self.assertIn(b" 504 ", reply.split(b"\r\n")[0])
        self.assertTrue(any(" POST /v1/convert " in line for line in logs.output), logs.output)
        self.assertEqual([line for line in logs.output if line.startswith("ERROR")], [])

    def test_compare_and_convert_overlap_on_separate_words(self):
        base = self.settings(10)
        runner = WordRunner(
            Settings(
                token=base.token,
                host=base.host,
                port=base.port,
                queue_timeout_s=2,
            )
        )
        started = threading.Semaphore(0)
        release = threading.Event()

        def hold(kind, files):
            started.release()
            self.assertTrue(release.wait(2))
            if kind == "compare":
                return make_docx(["compared"])
            return b"%PDF-1.4\n" + b"x" * 80

        runner._execute = hold
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(2) as pool:
            try:
                compare = pool.submit(runner, "compare", {"original": b"a", "revised": b"b"})
                convert = pool.submit(runner, "convert", {"document": b"a"})
                # Both jobs are inside Word at the same time before either is let go.
                self.assertTrue(started.acquire(timeout=2))
                self.assertTrue(started.acquire(timeout=2))
            finally:
                release.set()
            # result() re-raises a failed assertion or JobError from either job.
            self.assertTrue(compare.result(timeout=2).startswith(b"PK"))
            self.assertTrue(convert.result(timeout=2).startswith(b"%PDF-"))


class ClientIdentityTests(unittest.TestCase):
    def _headers(self, values: dict[str, str]):
        import email.message
        message = email.message.Message()
        for key, value in values.items():
            message[key] = value
        return message

    def test_prefers_tunnel_forwarded_ip(self):
        from word_endpoint.server import _client_identity
        headers = self._headers({"Cf-Connecting-Ip": "203.0.113.9"})
        self.assertEqual(_client_identity("127.0.0.1", headers), "203.0.113.9")

    def test_falls_back_to_forwarded_for_first_value(self):
        from word_endpoint.server import _client_identity
        headers = self._headers({"X-Forwarded-For": "198.51.100.7, 10.0.0.1"})
        self.assertEqual(_client_identity("127.0.0.1", headers), "198.51.100.7")

    def test_uses_peer_address_without_forward_headers(self):
        from word_endpoint.server import _client_identity
        self.assertEqual(_client_identity("127.0.0.1", self._headers({})), "127.0.0.1")

    def test_garbage_forward_values_are_ignored(self):
        from word_endpoint.server import _client_identity
        headers = self._headers({"X-Forwarded-For": "not an ip !!"})
        self.assertEqual(_client_identity("127.0.0.1", headers), "127.0.0.1")


if __name__ == "__main__":
    unittest.main()
