"""Loopback HTTP API for compare and convert.

The listen address is fixed to 127.0.0.1. Callers authenticate with a bearer
token. Uploads are files only: there is no URL fetch and no client-supplied path.
"""

from __future__ import annotations

import atexit
import hashlib
import hmac
import json
import logging
import os
import re
import socket
import threading
import time
import urllib.parse
import uuid
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from logging.handlers import RotatingFileHandler

from word_endpoint.config import Settings, load_settings
from word_endpoint.guard import GuardError, prepare_docx, validate_docx
from word_endpoint.multipart import MultipartError, parse_multipart
from word_endpoint.paths import LOG_DIR
from word_endpoint.responses import PUBLIC, public_code
from word_endpoint.runner import REQUEST_ID, JobError, WordRunner, cleanup_old_work

Runner = Callable[[str, dict[str, bytes]], bytes]
_FILENAME = re.compile(r"[A-Za-z0-9._-]{1,64}")
_LENGTH = re.compile(r"\d{1,12}")
# RFC 6750 b64token: what a client can send after "Bearer ".
TOKEN68 = re.compile(r"[A-Za-z0-9\-._~+/]+=*")

# Seconds a client has to send a whole request body, however it paces it.
UPLOAD_DEADLINE_S = 120.0


class RateLimiter:
    def __init__(self, limit: int):
        self.limit = limit
        self.hits: deque[float] = deque()
        self.lock = threading.Lock()

    def allow(self) -> bool:
        now = time.monotonic()
        with self.lock:
            while self.hits and now - self.hits[0] > 60:
                self.hits.popleft()
            if len(self.hits) >= self.limit:
                return False
            self.hits.append(now)
            return True


@dataclass
class App:
    settings: Settings
    runner: Runner
    limiter: RateLimiter
    admission: threading.BoundedSemaphore
    # Failed authentication has its own budget, so unauthenticated traffic
    # cannot use up the quota that authorized jobs draw from.
    auth_failures: RateLimiter


class Server(ThreadingHTTPServer):
    allow_reuse_address = False
    daemon_threads = True
    request_queue_size = 128
    app: App
    connections: threading.BoundedSemaphore

    def process_request(self, request, client_address) -> None:
        if not self.connections.acquire(blocking=False):
            payload = b'{"code":"busy","error":"The server is busy. Try again shortly."}'
            try:
                request.settimeout(1)
                request.sendall(b"HTTP/1.1 503 Service Unavailable\r\nConnection: close\r\nRetry-After: 5\r\nContent-Type: application/json\r\nContent-Length: "
                                + str(len(payload)).encode("ascii") + b"\r\n\r\n" + payload)
            except OSError:
                pass
            finally:
                self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self.connections.release()
            raise

    def process_request_thread(self, request, client_address) -> None:
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.connections.release()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server: Server

    def version_string(self) -> str:
        return "WordEndpoint"

    def setup(self) -> None:
        super().setup()
        self.request.settimeout(15)
        self.request_id = uuid.uuid4().hex
        self._responded = False
        self._status = 500
        self._code = "-"
        self._started = time.monotonic()
        self._unread_body = 0

    def log_message(self, fmt: str, *args) -> None:
        return

    # http.server refuses some requests itself, before any do_* method runs: a
    # request line or headers it cannot read, or a method with no do_*
    # handler. Its send_error answers with an HTML page; these get the same
    # JSON error body as every other refusal.
    _PARSER_REFUSALS = {400: "bad_request", 414: "uri_too_long", 431: "headers_too_large",
                        501: "not_implemented", 505: "http_version"}

    def send_error(self, code: int, message: str | None = None, explain: str | None = None) -> None:
        # message can quote the request line, query string included, so it is
        # not logged.
        status = int(code)
        name = self._PARSER_REFUSALS.get(status, "bad_request" if status < 500 else "word_failed")
        self.close_connection = True
        logging.info("%s refused by the HTTP parser: %d %s peer=%s", self.request_id, status, name,
                     _client_identity(self.client_address[0], getattr(self, "headers", None) or {}))
        # The parser stopped partway through the request, so how much of it is
        # still arriving is unknown. Drain under the same byte and time budget
        # as a refused upload, so a reset does not destroy this answer.
        self._unread_body = 65536
        self._fail(name)

    def do_GET(self) -> None:
        self._dispatch(self._get)

    def do_HEAD(self) -> None:
        self._dispatch(self._head)

    def do_POST(self) -> None:
        self._dispatch(self._post)

    def do_PUT(self) -> None:
        self._dispatch(lambda: self._fail("method_not_allowed"))

    def do_DELETE(self) -> None:
        self._dispatch(lambda: self._fail("method_not_allowed"))

    def do_PATCH(self) -> None:
        self._dispatch(lambda: self._fail("method_not_allowed"))

    def do_OPTIONS(self) -> None:
        self._dispatch(lambda: self._fail("method_not_allowed"))

    def _dispatch(self, action) -> None:
        context = REQUEST_ID.set(self.request_id)
        try:
            action()
        except Exception:
            logging.exception("request failed")
            self._fail("word_failed")
        finally:
            path = self._log_path()
            elapsed = int((time.monotonic() - self._started) * 1000)
            if not (self.command in {"GET", "HEAD"} and path in {"/health", "/live"} and self._status == 200):
                logging.info(
                    "%s %s %s %s %s %sms peer=%s",
                    self.request_id,
                    self.command,
                    path,
                    self._status,
                    self._code,
                    elapsed,
                    _client_identity(self.client_address[0], self.headers),
                )
            REQUEST_ID.reset(context)

    def _get(self, *, include_body: bool = True) -> None:
        path = self._route()
        if path is None:
            return
        if path == "/live":
            self._send(200, "application/json; charset=utf-8", b'{"status":"ok"}', "ok", include_body)
            return
        if path in {"/health", "/ready"}:
            self._health(include_body=include_body, readiness=path == "/ready")
            return
        self._fail("not_found")

    def _head(self) -> None:
        self._get(include_body=False)

    def _post(self) -> None:
        path = self._route()
        if path is None:
            return
        if path not in {"/v1/compare", "/v1/compare-pdf", "/v1/convert"}:
            self._fail("not_found")
            return
        if self.headers.get("Transfer-Encoding") or self.headers.get("Content-Encoding"):
            self._fail("unsupported_encoding")
            return
        length = self._length()
        if length is None:
            return
        self._unread_body = length
        if not self._authorized():
            self._fail("rate_limited" if not self.server.app.auth_failures.allow() else "unauthorized")
            return
        if not self.server.app.limiter.allow():
            self._fail("rate_limited")
            return
        if not self.server.app.admission.acquire(blocking=False):
            self._fail("busy")
            return
        try:
            self._accepted_post(path, length)
        finally:
            self.server.app.admission.release()

    def _accepted_post(self, path: str, length: int) -> None:
        body = self._read_exact(length)
        if body is None:
            return
        try:
            files = parse_multipart(
                self.headers.get("Content-Type", ""),
                body,
                self.server.app.settings.max_file_bytes,
            )
        except MultipartError as exc:
            self._fail(exc.code)
            return
        if path in {"/v1/compare", "/v1/compare-pdf"}:
            self._compare(files, as_pdf=path == "/v1/compare-pdf")
        else:
            self._convert(files)

    def _compare(self, files: dict[str, bytes], *, as_pdf: bool = False) -> None:
        fields = set(files)
        expected = {"original", "revised"}
        if fields != expected:
            self._fail("unexpected_field" if fields - expected else "missing_compare_files")
            return
        if not self._guard_inputs(files):
            return
        try:
            data = self.server.app.runner("compare_pdf" if as_pdf else "compare", files)
        except JobError as exc:
            self._fail(exc.code)
            return
        if as_pdf:
            self._pdf("comparison.pdf", data)
            return
        if not getattr(self.server.app.runner, "validates_output", False):
            try:
                validate_docx(data, max_bytes=80 * 1024 * 1024)
            except GuardError:
                self._fail("compare_failed")
                return
        self._file(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "comparison.docx",
            data,
        )

    def _convert(self, files: dict[str, bytes]) -> None:
        if set(files) != {"document"}:
            self._fail("unexpected_field" if files else "missing_document")
            return
        if not self._guard_inputs(files):
            return
        try:
            data = self.server.app.runner("convert", files)
        except JobError as exc:
            self._fail(exc.code)
            return
        self._pdf("document.pdf", data)

    def _guard_inputs(self, files: dict[str, bytes]) -> bool:
        started = time.monotonic()
        for key, blob in files.items():
            try:
                files[key] = prepare_docx(blob)
            except GuardError as exc:
                logging.warning("guard request=%s code=%s reason=%s part=%r field=%s", self.request_id, exc.code, exc.reason, exc.part, key)
                self._fail(exc.code)
                return False
        logging.info("validation request=%s bytes=%s ms=%d", self.request_id,
                     sum(len(blob) for blob in files.values()), (time.monotonic() - started) * 1000)
        return True

    def _target(self) -> urllib.parse.SplitResult | None:
        try:
            # A request the parser refused can lack a path.
            return urllib.parse.urlsplit(getattr(self, "path", ""))
        except ValueError:
            return None

    def _log_path(self) -> str:
        parsed = self._target()
        return parsed.path[:64] if parsed is not None else "<invalid-target>"

    def _route(self) -> str | None:
        parsed = self._target()
        if parsed is None:
            self._fail("not_found")
            return None
        if parsed.query or parsed.fragment or "\\" in parsed.path:
            self._fail("query_rejected" if parsed.query or parsed.fragment else "not_found")
            return None
        if len(parsed.path) > 64:
            self._fail("not_found")
            return None
        return parsed.path

    def _length(self) -> int | None:
        if self.headers.get_all("Transfer-Encoding"):
            self._fail("unsupported_encoding")
            return None
        values = self.headers.get_all("Content-Length") or []
        if len(values) != 1 or _LENGTH.fullmatch(values[0].strip()) is None:
            self._fail("length_required")
            return None
        value = int(values[0])
        if value <= 0 or value > self.server.app.settings.max_request_bytes:
            self._fail("too_large")
            return None
        return value

    def _authorized(self) -> bool:
        headers = self.headers.get_all("Authorization") or []
        if len(headers) != 1:
            return False
        scheme, separator, presented = headers[0].partition(" ")
        if separator != " " or scheme.lower() != "bearer":
            return False
        presented = presented.strip()
        if not presented or len(presented) > 512:
            return False
        return _token_ok(presented, self.server.app.settings.token)

    def _read_exact(self, length: int) -> bytes | None:
        chunks = []
        remaining = length
        deadline = time.monotonic() + UPLOAD_DEADLINE_S
        while remaining:
            try:
                time_left = deadline - time.monotonic()
                if time_left <= 0:
                    raise TimeoutError
                self.request.settimeout(time_left)
                # read1 makes at most one socket read, so each read gets the
                # time left; read() could loop past the deadline.
                chunk = self.rfile.read1(min(65536, remaining))
            except (TimeoutError, socket.timeout, ConnectionError):
                self._fail("timeout")
                return None
            if not chunk:
                self._fail("bad_multipart")
                return None
            if time.monotonic() > deadline:
                self._fail("timeout")
                return None
            chunks.append(chunk)
            remaining -= len(chunk)
            self._unread_body = remaining
        return b"".join(chunks)

    def _health(self, include_body: bool = True, readiness: bool = False) -> None:
        health = getattr(self.server.app.runner, "health", None)
        status = health() if health else {"status": "ok"}
        ready = status["status"] == "ok"
        if health:
            # Both answer with the Health body. Existing deployed supervisors
            # use /health for HTTP liveness, so its status stays "ok" and Word
            # readiness is in "ready"; /ready reports the workers' status.
            status = {"status": status["status"] if readiness else "ok", "ready": ready,
                      "workers": status["workers"]}
        body = json.dumps(status, separators=(",", ":")).encode("utf-8")
        self._send(200 if not readiness or ready else 503,
                   "application/json; charset=utf-8", body, status["status"], include_body)

    def _fail(self, code: str) -> None:
        safe = public_code(code)
        if safe != code:
            logging.error("replacing unknown code %s", code)
        status, message = PUBLIC[safe]
        if status >= 500:
            logging.warning("request failed request=%s code=%s path=%s",
                            self.request_id, safe, self._log_path())
        body = json.dumps(
            {"error": message, "code": safe, "request_id": self.request_id}
        ).encode("utf-8")
        self._send(status, "application/json; charset=utf-8", body, safe, True,
                   (("Retry-After", "5"),) if safe in {"busy", "rate_limited"} else ())

    def _pdf(self, filename: str, data: bytes) -> None:
        if not data.startswith(b"%PDF-") or not 64 <= len(data) <= 80 * 1024 * 1024:
            self._fail("convert_failed")
            return
        self._file("application/pdf", filename, data)

    def _file(self, media: str, filename: str, data: bytes) -> None:
        if _FILENAME.fullmatch(filename) is None:
            raise RuntimeError("refusing to send an unsafe download name")
        self._send(
            200,
            media,
            data,
            "ok",
            True,
            (("Content-Disposition", f'attachment; filename="{filename}"'),),
        )

    def _send(
        self,
        status: int,
        content_type: str,
        payload: bytes,
        code: str,
        include_body: bool,
        extra: tuple[tuple[str, str], ...] = (),
    ) -> None:
        if self._responded:
            return
        self._responded = True
        self._status = status
        self._code = code
        if self.command == "HEAD":
            # RFC 9110 9.3.2: HEAD carries the length GET would send, no body.
            body = b""
            length = len(payload)
        else:
            body = payload if include_body else b""
            length = len(payload) if include_body else 0
        try:
            self.send_response(status)
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Request-Id", self.request_id)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(length))
            self.send_header("Connection", "close")
            for key, value in extra:
                self.send_header(key, value)
            self.end_headers()
            if body:
                self.wfile.write(body)
            self.wfile.flush()
            self.request.shutdown(socket.SHUT_WR)
            # Windows can reset a connection closed with unread upload bytes,
            # hiding a 401/429/503 response from the client. Drain only a small,
            # already-arriving body, with a strict time and byte budget.
            budget = min(self._unread_body, 65536)
            deadline = time.monotonic() + 0.1
            while budget and time.monotonic() < deadline:
                self.request.settimeout(max(0.001, deadline - time.monotonic()))
                chunk = self.rfile.read1(min(budget, 8192))
                if not chunk:
                    break
                budget -= len(chunk)
        except OSError:
            # The client left, or (after the upload deadline) the socket timed
            # out, which makes every later read raise a plain OSError
            # ("cannot read from timed out object"). The response is out
            # either way, so there is nothing left to do.
            return


_PEER_SAFE = re.compile(r"[0-9a-zA-Z.:_\-\[\]]+")


def _client_identity(address: str, headers) -> str:
    """Best client identity: tunnel-forwarded IP when present, else the peer."""
    forwarded = headers.get("Cf-Connecting-Ip") or headers.get("X-Forwarded-For") or ""
    candidate = forwarded.split(",")[0].strip()
    if candidate and _PEER_SAFE.fullmatch(candidate):
        return candidate
    if address and _PEER_SAFE.fullmatch(address):
        return address
    return "unknown"


def _token_ok(presented: str, expected: str) -> bool:
    left = hashlib.sha256(presented.encode("utf-8", errors="replace")).digest()
    right = hashlib.sha256(expected.encode("utf-8")).digest()
    return hmac.compare_digest(left, right)


def create_server(settings: Settings, runner: Runner) -> Server:
    if settings.host != "127.0.0.1":
        raise RuntimeError("Refusing to listen on a non-loopback address.")
    if not 32 <= len(settings.token) <= 256 or TOKEN68.fullmatch(settings.token) is None:
        raise RuntimeError("Refusing to start with an invalid token.")
    if not 0 <= settings.port <= 65535:
        raise RuntimeError("Invalid port.")
    server = Server((settings.host, settings.port), Handler)
    server.connections = threading.BoundedSemaphore(settings.max_concurrent + 16)
    server.app = App(settings, runner, RateLimiter(settings.rate_limit_per_minute),
                     threading.BoundedSemaphore(settings.max_concurrent),
                     RateLimiter(settings.rate_limit_per_minute))
    return server


def configure_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        LOG_DIR / "server.log",
        maxBytes=2_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    logging.basicConfig(
        level=logging.INFO,
        handlers=[file_handler],
        format="%(asctime)s %(levelname)s %(message)s",
    )


def _record_server_pid() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    path = LOG_DIR / "server.pid"
    path.write_text(str(os.getpid()), encoding="ascii")

    def clear() -> None:
        try:
            if path.is_file() and path.read_text(encoding="ascii").strip() == str(os.getpid()):
                path.unlink()
        except OSError:
            pass

    atexit.register(clear)


def main() -> None:
    _record_server_pid()
    configure_logging()
    cleanup_old_work()
    settings = load_settings()
    runner = WordRunner(settings)
    runner.warm()
    atexit.register(runner.shutdown)
    server = create_server(settings, runner)
    host, port = server.server_address
    logging.info(
        "listening on http://%s:%s warm-word=compare,convert rate=%s/min",
        host,
        port,
        settings.rate_limit_per_minute,
    )
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        logging.info("stopping")
    finally:
        runner.shutdown()
        server.server_close()
