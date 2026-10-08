# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# SPDX-License-Identifier: AGPL-3.0-only
import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from livebench.models import MAX_FILE_BYTES


@dataclass(frozen=True)
class Config:
    data_dir: Path
    word_url: str
    word_token: str
    ingest_url: str
    ingest_token: str
    batch_size: int = 100
    prefetch_at: int = 90
    timeout: int = 240
    download_timeout: int = 45
    max_bytes: int = MAX_FILE_BYTES
    dpi: int = 144
    seed: int = 20261008
    max_batches: int = 0
    jubarte: str = "/usr/local/bin/jubarte"
    index_path: str = ""
    heartbeat_seconds: int = 15

    @classmethod
    def from_env(cls) -> "Config":
        size = int(os.environ.get("BATCH_SIZE", "100"))
        config = cls(
            data_dir=Path(os.environ.get("DATA_DIR", "/data")),
            word_url=os.environ.get("WORD_PUBLIC_URL", "https://docx.rodrigues.ai").strip().rstrip("/"),
            word_token=os.environ.get("WORD_API_TOKEN", ""),
            ingest_url=os.environ.get("INGEST_URL", "").strip().rstrip("/"),
            ingest_token=os.environ.get("INGEST_TOKEN", ""),
            batch_size=size,
            prefetch_at=int(os.environ.get("PREFETCH_AT", str(max(1, int(size * 0.9))))),
            timeout=int(os.environ.get("TOOL_TIMEOUT", "240")),
            download_timeout=int(os.environ.get("DOWNLOAD_TIMEOUT", "45")),
            max_bytes=int(os.environ.get("MAX_FIXTURE_BYTES", str(MAX_FILE_BYTES))),
            dpi=int(os.environ.get("SCORE_DPI", "144")),
            seed=int(os.environ.get("CORPUS_SEED", "20261008")),
            max_batches=int(os.environ.get("MAX_BATCHES", "0")),
            jubarte=os.environ.get("JUBARTE_BINARY", "/usr/local/bin/jubarte"),
            index_path=os.environ.get("CORPUS_INDEX", ""),
        )
        config.validate()
        return config

    def validate(self) -> None:
        if not self.word_token or not self.ingest_token or not self.ingest_url:
            raise ValueError("WORD_API_TOKEN, INGEST_TOKEN and INGEST_URL are required")
        for url in (self.word_url, self.ingest_url):
            parsed = urlsplit(url)
            if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username:
                raise ValueError("service URLs must be absolute HTTP(S) URLs without credentials")
        if not 1 <= self.batch_size <= 100 or not 1 <= self.prefetch_at <= self.batch_size:
            raise ValueError("batch size must be 1..100 and prefetch threshold within the batch")
        if self.dpi < 36 or self.dpi > 300 or self.timeout < 1 or not 1 <= self.max_bytes <= MAX_FILE_BYTES:
            raise ValueError("invalid benchmark resource limits")
