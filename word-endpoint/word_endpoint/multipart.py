"""Strict multipart parser.

Only the file bytes are kept. Filenames from the client are ignored, transfer
encodings other than identity are rejected, and the part count is capped.
"""

from __future__ import annotations

import re

# RFC 2046 5.1.1: 1 to 70 bchars, the last one not a space.
_BOUNDARY = re.compile(r"[A-Za-z0-9'()+_,\-./:=? ]{0,69}[A-Za-z0-9'()+_,\-./:=?]")
# One ";" parameter: a token name, "=", then a quoted-string or a token (RFC
# 9110 5.6.6). A value holding a separator such as "," ":" "/" or "=" must be
# quoted; read bare, other parsers could split it differently.
_PARAMETER = re.compile(
    r"""[ \t]*;[ \t]*([!#$%&'*+.^_`|~0-9A-Za-z-]+)[ \t]*=[ \t]*("(?:[^"\\\r\n]|\\[^\r\n])*"|[!#$%&'*+.^_`|~0-9A-Za-z-]+)"""
)
_QUOTED_PAIR = re.compile(r"\\(.)")
_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,31}$")
_ALLOWED_HEADERS = {"content-disposition", "content-type", "content-transfer-encoding"}
_ALLOWED_ENCODINGS = {"binary", "7bit", "8bit", "identity"}


class MultipartError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def parse_multipart(content_type: str, body: bytes, max_file_bytes: int) -> dict[str, bytes]:
    if not isinstance(body, (bytes, bytearray)):
        raise MultipartError("bad_multipart")
    if len(body) > 42 * 1024 * 1024:
        raise MultipartError("too_large")
    boundary = _boundary(content_type)
    files: dict[str, bytes] = {}
    for part in _split_parts(bytes(body), boundary):
        name, data = _parse_part(part, max_file_bytes)
        if name in files:
            raise MultipartError("bad_multipart")
        files[name] = data
    return files


def _boundary(content_type: str) -> bytes:
    if (
        not isinstance(content_type, str)
        or len(content_type) > 300
        or "\n" in content_type
        or "\r" in content_type
    ):
        raise MultipartError("bad_multipart")
    parsed = _parameters(content_type)
    if parsed is None or parsed[0] != "multipart/form-data":
        raise MultipartError("bad_multipart")
    boundary = parsed[1].get("boundary")
    if boundary is None or _BOUNDARY.fullmatch(boundary) is None:
        raise MultipartError("bad_multipart")
    return boundary.encode("ascii")


def _split_parts(body: bytes, boundary: bytes) -> list[bytes]:
    delimiter = b"--" + boundary
    if not body.startswith(delimiter):
        marker = b"\r\n" + delimiter
        index = body.find(marker)
        if index < 0 or index > 8192:
            raise MultipartError("bad_multipart")
        body = body[index + 2 :]
    parts: list[bytes] = []
    for _ in range(5):
        if body.startswith(delimiter + b"--"):
            return parts
        if not body.startswith(delimiter):
            raise MultipartError("bad_multipart")
        body = body[len(delimiter) :]
        if body.startswith(b"--"):
            return parts
        # RFC 2046 transport-padding: spaces or tabs may follow a delimiter.
        pad = 0
        while pad < len(body) and pad < 1024 and body[pad] in b" \t":
            pad += 1
        if body[pad : pad + 2] != b"\r\n":
            raise MultipartError("bad_multipart")
        body = body[pad + 2 :]
        next_at = body.find(b"\r\n" + delimiter)
        if next_at < 0:
            raise MultipartError("bad_multipart")
        parts.append(body[:next_at])
        body = body[next_at + 2 :]
        if len(parts) > 3:
            raise MultipartError("too_many_parts")
    raise MultipartError("too_many_parts")


def _parse_part(part: bytes, max_file_bytes: int) -> tuple[str, bytes]:
    header_blob, separator, data = part.partition(b"\r\n\r\n")
    if separator != b"\r\n\r\n" or len(header_blob) > 8192 or b"\x00" in header_blob:
        raise MultipartError("bad_multipart")
    if len(data) > max_file_bytes:
        raise MultipartError("too_large")
    try:
        header_text = header_blob.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise MultipartError("bad_multipart") from exc
    headers: dict[str, str] = {}
    for line in header_text.split("\r\n"):
        if not line:
            continue
        if line[0] in " \t" or ":" not in line:
            raise MultipartError("bad_multipart")
        key, value = line.split(":", 1)
        key = key.strip().lower()
        if key in headers:
            raise MultipartError("bad_multipart")
        headers[key] = value.strip()
    if set(headers) - _ALLOWED_HEADERS or "content-disposition" not in headers:
        raise MultipartError("bad_multipart")
    encoding = headers.get("content-transfer-encoding", "binary").lower()
    if encoding not in _ALLOWED_ENCODINGS:
        raise MultipartError("bad_multipart")
    name = _disposition_name(headers["content-disposition"])
    if name is None or _NAME.fullmatch(name) is None:
        raise MultipartError("unexpected_field")
    return name, data


def _disposition_name(value: str) -> str | None:
    if len(value) > 512:
        return None
    parsed = _parameters(value)
    if parsed is None or parsed[0] != "form-data":
        return None
    return parsed[1].get("name")


def _parameters(value: str) -> tuple[str, dict[str, str | None]] | None:
    """A header value's type and its parameters, honouring quoted-strings, so
    a ";" or "name=" inside a quoted filename stays part of the filename.
    None when the value does not parse; a parameter given twice maps to None,
    so a caller that reads it treats it as missing."""
    kind, _, _ = value.partition(";")
    position = len(kind)
    params: dict[str, str | None] = {}
    while position < len(value):
        match = _PARAMETER.match(value, position)
        if match is None:
            if value[position:].strip(" \t;"):
                return None
            break
        key, raw = match.group(1).lower(), match.group(2)
        if raw.startswith('"'):
            raw = _QUOTED_PAIR.sub(r"\1", raw[1:-1])
        params[key] = None if key in params else raw
        position = match.end()
    return kind.strip().lower(), params
