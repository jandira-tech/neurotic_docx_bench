#!/usr/bin/env -S uv run --script
# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# /// script
# requires-python = ">=3.14"
# dependencies = ["typer>=0.12"]
# ///
"""Send docx files to the Word endpoint and save what it returns.

``POST /v1/compare`` takes the file fields ``original`` and ``revised``.
``POST /v1/convert`` takes the file field ``document``. The base URL is
``WORD_PUBLIC_URL`` and the bearer token is ``WORD_API_TOKEN``, from the
environment or from ``.env`` in the current directory. A non-200 response
is an error and the body is not treated as a document.

    endpoint_word.py compare original.docx revised.docx -o redline.docx
    endpoint_word.py convert document.docx -o document.pdf
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import typer

app = typer.Typer(add_completion=False, help=__doc__)

DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def load_endpoint() -> tuple[str, str]:
    """Return ``(base_url, token)`` without printing either."""
    env = dict(os.environ)
    env_path = Path(".env")
    if env_path.is_file():
        for raw in env_path.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            env.setdefault(key.strip(), value.strip().strip('"').strip("'"))
    url = env.get("WORD_PUBLIC_URL", "").rstrip("/")
    token = env.get("WORD_API_TOKEN", "")
    if not url or not token:
        raise RuntimeError("WORD_PUBLIC_URL and WORD_API_TOKEN are required")
    return url, token


def _post(url: str, token: str, fields: list[str], dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")
    header = dest.with_suffix(dest.suffix + ".hdr")
    cmd = [
        "curl",
        "-sS",
        "-m",
        "300",
        "-H",
        f"Authorization: Bearer {token}",
        "-D",
        str(header),
        "-o",
        str(part),
        "-w",
        "%{http_code}",
    ]
    for field in fields:
        cmd.extend(["-F", field])
    cmd.append(url)
    completed = subprocess.run(cmd, check=False, capture_output=True)
    status = completed.stdout.decode().strip()
    if completed.returncode != 0 or status != "200":
        detail = ""
        if part.is_file():
            body = part.read_bytes()[:300]
            if not body.startswith(b"PK") and not body.startswith(b"%PDF"):
                detail = body.decode("utf-8", "replace")
        stderr = completed.stderr.decode()[-300:]
        part.unlink(missing_ok=True)
        header.unlink(missing_ok=True)
        raise RuntimeError(f"status={status or completed.returncode} {detail} {stderr}")
    part.replace(dest)
    header.unlink(missing_ok=True)


@app.command()
def compare(
    original: Path = typer.Argument(..., help="Base docx, sent as original."),
    revised: Path = typer.Argument(..., help="Revision docx, sent as revised."),
    out: Path = typer.Option(..., "--out", "-o", help="Where to write the redline docx."),
) -> None:
    """POST /v1/compare and save the comparison file."""
    url, token = load_endpoint()
    _post(
        f"{url}/v1/compare",
        token,
        [
            f"original=@{original};type={DOCX}",
            f"revised=@{revised};type={DOCX}",
        ],
        out,
    )
    typer.echo(f"wrote {out}")


@app.command()
def convert(
    document: Path = typer.Argument(..., help="Docx, sent as document."),
    out: Path = typer.Option(..., "--out", "-o", help="Where to write the PDF."),
) -> None:
    """POST /v1/convert and save the PDF."""
    url, token = load_endpoint()
    _post(
        f"{url}/v1/convert",
        token,
        [f"document=@{document};type={DOCX}"],
        out,
    )
    typer.echo(f"wrote {out}")


if __name__ == "__main__":
    app()
