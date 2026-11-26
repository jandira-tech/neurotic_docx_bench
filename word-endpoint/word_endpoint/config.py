"""Runtime settings. The listen address is always loopback."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from word_endpoint.paths import ROOT

_PLACEHOLDER = "replace-with-at-least-32-random-characters"
_KEY = re.compile(r"[A-Z][A-Z0-9_]{0,40}")


@dataclass(frozen=True)
class Settings:
    token: str
    host: str = "127.0.0.1"
    port: int = 8787
    max_file_bytes: int = 20 * 1024 * 1024
    max_request_bytes: int = 42 * 1024 * 1024
    job_timeout_s: int = 120
    queue_timeout_s: float = 180
    rate_limit_per_minute: int = 300
    max_concurrent: int = 4


def load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        if not _KEY.fullmatch(key) or key in os.environ:
            continue
        os.environ[key] = value


def _bounded_int(name: str, default: int, low: int, high: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    if not re.fullmatch(r"-?\d+", raw):
        raise SystemExit(f"{name} must be an integer")
    value = int(raw)
    if value < low:
        return low
    if value > high:
        return high
    return value


def load_settings() -> Settings:
    load_dotenv(ROOT / ".env")
    token = os.environ.get("WORD_API_TOKEN", "").strip()
    if token == _PLACEHOLDER or len(token) < 32 or len(token) > 256:
        raise SystemExit(
            "WORD_API_TOKEN must be 32 to 256 characters. Run scripts\\start.ps1."
        )
    if any(character.isspace() for character in token):
        raise SystemExit("WORD_API_TOKEN cannot contain whitespace.")
    if re.fullmatch(r"[A-Za-z0-9\-._~+/]+=*", token) is None:
        raise SystemExit(
            "WORD_API_TOKEN must be a bearer token: letters, digits and - . _ ~ + /, optionally ending in =."
        )
    file_bytes = _bounded_int("MAX_FILE_BYTES", 20 * 1024 * 1024, 1024, 20 * 1024 * 1024)
    return Settings(
        token=token,
        host="127.0.0.1",
        port=_bounded_int("PORT", 8787, 1, 65535),
        max_file_bytes=file_bytes,
        max_request_bytes=min(file_bytes * 2 + 1024 * 1024, 42 * 1024 * 1024),
        job_timeout_s=_bounded_int("JOB_TIMEOUT_SECONDS", 120, 10, 300),
        queue_timeout_s=_bounded_int("QUEUE_TIMEOUT_SECONDS", 180, 0, 600),
        rate_limit_per_minute=_bounded_int("RATE_LIMIT_PER_MINUTE", 300, 1, 1000),
        max_concurrent=_bounded_int("MAX_CONCURRENT", 4, 1, 8),
    )
