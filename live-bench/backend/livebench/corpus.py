# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# SPDX-License-Identifier: AGPL-3.0-only
import hashlib
import ipaddress
import random
import socket
import time
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from livebench.models import MAX_FILE_BYTES, Document
from livebench.safety import UnsafeDocument, inspect_docx

DATASET = "superdoc-dev/docx-corpus"


def draw_indices(length: int, count: int, seed: int, cycle: int, offset: int) -> tuple[list[int], dict]:
    """A reproducible permutation, exhausting each corpus cycle before repeating."""
    if length < 1 or count < 0 or not 0 <= offset < length:
        raise ValueError("invalid corpus sampling range")
    selected = []
    while len(selected) < count:
        order = list(range(length))
        random.Random(seed + cycle).shuffle(order)
        take = min(count - len(selected), length - offset)
        selected.extend(order[offset : offset + take])
        offset += take
        if offset == length:
            cycle, offset = cycle + 1, 0
    return selected, {"cycle": cycle, "offset": offset}


def public_url(url: str, resolver: Callable = socket.getaddrinfo) -> None:
    parts = urlsplit(url)
    if parts.scheme not in ("https", "http") or not parts.hostname or parts.username or parts.password:
        raise ValueError("fixture URL must use HTTP(S) without credentials")
    if parts.port not in (None, 80, 443):
        raise ValueError("fixture URL has an unsupported port")
    addresses = resolver(
        parts.hostname, parts.port or (443 if parts.scheme == "https" else 80), type=socket.SOCK_STREAM
    )
    if not addresses or any(not ipaddress.ip_address(address[4][0]).is_global for address in addresses):
        raise ValueError("fixture URL resolves to a private or non-routable address")


def fetch_document(
    client: httpx.Client,
    url: str,
    max_bytes: int,
    validate: Callable[[str], None] = public_url,
    metadata: dict | None = None,
    clock: Callable[[], float] = time.monotonic,
    total_timeout: float = 120,
) -> bytes:
    max_bytes = min(max_bytes, MAX_FILE_BYTES)
    started = clock()
    for _ in range(6):
        validate(url)
        with client.stream("GET", url, follow_redirects=False) as response:
            if response.is_redirect:
                url = str(response.next_request.url)
                continue
            if metadata is not None:
                metadata.update(
                    final_url=str(response.url),
                    http_status=response.status_code,
                    response_headers={
                        k: v
                        for k, v in response.headers.items()
                        if k not in ("set-cookie", "authorization", "cookie")
                    },
                )
            response.raise_for_status()
            if int(response.headers.get("Content-Length", "0")) > max_bytes:
                raise ValueError("fixture exceeds download size limit")
            chunks, length = [], 0
            for chunk in response.iter_bytes():
                if clock() - started > total_timeout:
                    raise ValueError("fixture exceeded total download time limit")
                length += len(chunk)
                if length > max_bytes:
                    raise ValueError("fixture exceeds download size limit")
                chunks.append(chunk)
            return b"".join(chunks)
    raise ValueError("fixture redirect limit exceeded")


def download(row: dict, dest: Path, client: httpx.Client, max_bytes: int) -> Document:
    started = time.monotonic()
    metadata = {"corpus": {k: v for k, v in row.items() if k != "review_id"}}
    try:
        blob = fetch_document(client, row["url"], max_bytes, metadata=metadata)
        dest.parent.mkdir(parents=True, exist_ok=True)
        part = dest.with_suffix(".part")
        part.write_bytes(blob)
        part.replace(dest)
        error = None
        try:
            security = inspect_docx(blob)
        except UnsafeDocument as exc:
            security = {"status": "rejected", "error": str(exc), "policy": "ooxml-bounded-v1"}
            error = str(exc)
        metadata.update(download_bytes=len(blob), download_ms=round((time.monotonic() - started) * 1000, 3))
        return Document(
            str(row["id"]),
            row["url"],
            dest,
            hashlib.sha256(blob).hexdigest(),
            row.get("language"),
            row.get("type"),
            error=error,
            review_id=row.get("review_id"),
            metadata=metadata,
            security=security,
        )
    except Exception as exc:
        return Document(
            str(row["id"]),
            row["url"],
            None,
            None,
            row.get("language"),
            row.get("type"),
            f"{type(exc).__name__}: {exc}"[:1200],
            review_id=row.get("review_id"),
            metadata={**metadata, "download_ms": round((time.monotonic() - started) * 1000, 3)},
        )


def load_index(path: str, revision: str | None = None):
    import polars as pl
    from huggingface_hub import HfApi, hf_hub_download

    if path:
        return pl.read_parquet(path), hashlib.sha256(Path(path).read_bytes()).hexdigest()
    revision = revision or HfApi().dataset_info(DATASET).sha
    cached = hf_hub_download(
        DATASET, "data/train-00000-of-00001.parquet", repo_type="dataset", revision=revision
    )
    return pl.read_parquet(cached), revision
