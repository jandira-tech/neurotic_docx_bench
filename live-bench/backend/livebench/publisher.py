# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# SPDX-License-Identifier: AGPL-3.0-only
import hashlib
import json
from pathlib import Path
from urllib.parse import quote

import httpx

from livebench.models import MAX_FILE_BYTES


def archive_files(run: dict, results: list[dict], key: str, limit: int = MAX_FILE_BYTES) -> dict[str, bytes]:
    """Keep complete archive evidence while bounding every individual object."""

    def encode(value):
        return json.dumps(value, separators=(",", ":"), allow_nan=False).encode()

    full = encode({"run": run, "results": results})
    if len(full) <= limit:
        return {key: full}
    files, parts = {}, []
    # Ingestion bounds each review to 256 KiB, so ten reviews fit comfortably.
    for offset in range(0, len(results), 10):
        part_key = key.removesuffix(".json") + f"-part-{offset // 10 + 1:03d}.json"
        data = encode({"results": results[offset : offset + 10]})
        if len(data) > limit:
            raise ValueError("archive part exceeds file size limit")
        files[part_key] = data
        parts.append({"key": part_key, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    index = encode({"run": run, "result_parts": parts})
    if len(index) > limit:
        raise ValueError("archive index exceeds file size limit")
    files[key] = index
    return files


class Publisher:
    def __init__(self, url: str, token: str, client: httpx.Client):
        self.url, self.token, self.client = url, token, client

    def post(self, kind: str, payload: dict) -> None:
        response = self.client.post(
            f"{self.url}/api/ingest/{kind}",
            json=payload,
            headers={"Authorization": f"Bearer {self.token}"},
            timeout=10 if kind == "live" else 120,
        )
        response.raise_for_status()

    def upload(self, key: str, content_type: str, data: bytes) -> None:
        if len(data) > MAX_FILE_BYTES:
            raise ValueError("artifact exceeds 20 MB file size limit")
        response = self.client.put(
            f"{self.url}/api/ingest/artifacts/{quote(key, safe='/')}",
            content=data,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": content_type,
                "X-Content-SHA256": hashlib.sha256(data).hexdigest(),
            },
        )
        response.raise_for_status()

    def result(self, result: dict, work: Path) -> None:
        for artifact in result["artifacts"]:
            path = work / artifact["key"].rsplit("/", 1)[1]
            if path.stat().st_size > MAX_FILE_BYTES:
                raise ValueError("artifact exceeds 20 MB file size limit")
            data = path.read_bytes()
            if hashlib.sha256(data).hexdigest() != artifact["sha256"]:
                raise ValueError("local artifact differs from committed result metadata")
            self.upload(artifact["key"], artifact["content_type"], data)
        self.post("result", result)
