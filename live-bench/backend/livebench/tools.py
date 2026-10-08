# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# SPDX-License-Identifier: AGPL-3.0-only
"""Real tool adapters. Every invocation is synchronous and time bounded."""

import hashlib
import json
import mimetypes
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import httpx

from livebench.config import Config
from livebench.models import MAX_FILE_BYTES, ToolFailure

DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def command(args: list[str], timeout: int) -> str:
    # Native parsers get neither credentials nor Internet access. The wrapper sets
    # resource limits in its own process, avoiding preexec_fn in this threaded worker.
    env = {
        k: v
        for k, v in os.environ.items()
        if k
        in (
            "PATH",
            "HOME",
            "LANG",
            "LC_ALL",
            "DOTNET_ROOT",
            "FONTCONFIG_PATH",
            "PYTHONPATH",
            "SUPERDOC_REPO",
            "BENCH_DEVICE",
        )
    }
    env.update(
        OMP_NUM_THREADS="2",
        OPENBLAS_NUM_THREADS="2",
        RAYON_NUM_THREADS="2",
        DOTNET_PROCESSOR_COUNT="2",
        DOTNET_GCHeapHardLimit="30000000",
    )
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        proc = subprocess.Popen(
            [sys.executable, "-m", "livebench.process_limit", str(timeout), *args],
            stdout=stdout,
            stderr=stderr,
            start_new_session=True,
            env=env,
        )
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
            raise ToolFailure(f"operation timed out after {timeout}s") from None
        if proc.returncode:
            stderr.seek(max(0, stderr.tell() - 1200))
            stdout.seek(max(0, stdout.tell() - 1200))
            detail = (stderr.read(1200) or stdout.read(1200)).decode(errors="replace")
            raise ToolFailure(f"exit={proc.returncode}: {detail}")
        stdout.seek(0)
        data = stdout.read(1024 * 1024 + 1)
        if len(data) > 1024 * 1024:
            raise ToolFailure("tool diagnostic output exceeds size limit")
        return data.decode(errors="replace").strip()


def verify_output(path: Path, dpi: int = 144) -> None:
    if not path.is_file() or path.stat().st_size == 0:
        raise ToolFailure("tool produced no output")
    if path.stat().st_size > MAX_FILE_BYTES:
        raise ToolFailure("tool output exceeds 20 MB file size limit")
    if path.suffix == ".pdf":
        with path.open("rb") as fh:
            if fh.read(5) != b"%PDF-":
                raise ToolFailure("tool output is not a PDF")
        command([sys.executable, "-m", "livebench.pdf_probe", str(path), str(dpi)], 30)
    else:
        try:
            with zipfile.ZipFile(path) as package:
                if "word/document.xml" not in package.namelist():
                    raise ToolFailure("tool output has no Word document part")
        except zipfile.BadZipFile:
            raise ToolFailure("tool output is not a DOCX ZIP package") from None


class RealTools:
    def __init__(self, config: Config, client: httpx.Client):
        self.config, self.client = config, client

    def _word(self, operation: str, inputs: list[Path], output: Path) -> None:
        endpoint = "compare" if operation == "compare" else "convert"
        names = ("original", "revised") if endpoint == "compare" else ("document",)
        # File handles close before any subsequent request, including failures.
        from contextlib import ExitStack

        with ExitStack() as stack:
            files = {
                name: (path.name, stack.enter_context(path.open("rb")), DOCX)
                for name, path in zip(names, inputs, strict=True)
            }
            try:
                with self.client.stream(
                    "POST",
                    f"{self.config.word_url}/v1/{endpoint}",
                    files=files,
                    headers={"Authorization": f"Bearer {self.config.word_token}"},
                    timeout=self.config.timeout,
                ) as response:
                    if response.status_code != 200:
                        diagnostic = bytearray()
                        for chunk in response.iter_bytes(900):
                            diagnostic.extend(chunk[: 900 - len(diagnostic)])
                            if len(diagnostic) >= 900:
                                break
                        body = diagnostic.decode(errors="replace")
                        status = "broken" if response.status_code in (400, 409, 422) else "error"
                        raise ToolFailure(
                            f"Word {endpoint} HTTP {response.status_code}: {body}", status=status
                        )
                    if int(response.headers.get("Content-Length", "0")) > MAX_FILE_BYTES:
                        raise ToolFailure("Word output exceeds 20 MB file size limit")
                    part = output.with_suffix(output.suffix + ".part")
                    length = 0
                    try:
                        with part.open("wb") as fh:
                            for chunk in response.iter_bytes():
                                length += len(chunk)
                                if length > MAX_FILE_BYTES:
                                    raise ToolFailure("Word output exceeds 20 MB file size limit")
                                fh.write(chunk)
                        part.replace(output)
                    finally:
                        part.unlink(missing_ok=True)
            except httpx.HTTPError as exc:
                raise ToolFailure(f"Word {endpoint}: {type(exc).__name__}", status="error") from None

    def perform(self, tool: str, operation: str, inputs: list[Path], output: Path) -> Path:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.unlink(missing_ok=True)
        try:
            if any(path.stat().st_size > MAX_FILE_BYTES for path in inputs):
                raise ToolFailure("input exceeds 20 MB file size limit")
            if tool == "word":
                self._word(operation, inputs, output)
            elif tool == "jubarte":
                args = (
                    [self.config.jubarte, *map(str, inputs), "-o", str(output), "--force", "--quiet"]
                    if operation == "compare"
                    else [
                        self.config.jubarte,
                        "convert",
                        str(inputs[0]),
                        "-o",
                        str(output),
                        "--force",
                        "--revisions",
                        "word",
                        "--compress",
                    ]
                )
                command(args, self.config.timeout)
            elif tool == "docxide":
                command(["docxide-pdf", str(inputs[0]), str(output)], self.config.timeout)
            elif tool == "docxodus":
                command(
                    [sys.executable, "-m", "livebench.docxodus_compare", *map(str, inputs), str(output)],
                    self.config.timeout,
                )
            elif tool == "superdoc-redlines":
                command(
                    [sys.executable, "-m", "livebench.superdoc_compare", *map(str, inputs), str(output)],
                    self.config.timeout,
                )
            elif tool == "soffice":
                with tempfile.TemporaryDirectory(prefix="livebench-lo-") as tmp:
                    root = Path(tmp)
                    command(
                        [
                            "soffice",
                            f"-env:UserInstallation={(root / 'profile').as_uri()}",
                            "--headless",
                            "--convert-to",
                            "pdf:writer_pdf_Export",
                            "--outdir",
                            tmp,
                            str(inputs[0]),
                        ],
                        self.config.timeout,
                    )
                    pdf = root / f"{inputs[0].stem}.pdf"
                    if not pdf.is_file():
                        raise ToolFailure("LibreOffice exited without producing a PDF")
                    shutil.copyfile(pdf, output)
            else:
                raise ToolFailure(f"unknown tool {tool}", status="error")
            verify_output(output, self.config.dpi)
            if output.suffix == ".docx":
                from livebench.safety import UnsafeDocument, inspect_docx

                try:
                    inspect_docx(output.read_bytes())
                except UnsafeDocument as exc:
                    raise ToolFailure(f"unsafe generated package: {exc}") from None
            return output
        except ToolFailure as exc:
            output.unlink(missing_ok=True)
            # No remote diagnostic may echo either of our credentials into published data.
            safe = (
                str(exc)
                .replace(self.config.word_token, "[redacted]")
                .replace(self.config.ingest_token, "[redacted]")
            )
            raise ToolFailure(f"{inputs[0].name}: {safe}", status=exc.status) from None
        except OSError as exc:
            output.unlink(missing_ok=True)
            raise ToolFailure(f"{type(exc).__name__}: tool unavailable", status="error") from None

    def score(self, oracle: Path, candidate: Path, work: Path) -> dict:
        # Separate process both bounds scoring cost and isolates MuPDF/skimage from HTTP threads.
        # The scorer owns and deletes its TemporaryDirectory and never persists page rasters.
        try:
            stdout = command(
                [
                    sys.executable,
                    "-m",
                    "livebench.scorer",
                    str(oracle),
                    str(candidate),
                    str(self.config.dpi),
                    str(work),
                ],
                self.config.timeout,
            )
            return json.loads(stdout)
        except (ToolFailure, ValueError) as exc:
            raise ToolFailure(f"scorer failed: {str(exc)[:1100]}", status="error") from None

    def functional(self, candidate: Path, previous: Path, current: Path, work: Path) -> dict:
        try:
            return json.loads(
                command(
                    [
                        sys.executable,
                        "-m",
                        "livebench.functional",
                        str(candidate),
                        str(previous),
                        str(current),
                    ],
                    self.config.timeout,
                )
            )
        except (ToolFailure, ValueError) as exc:
            raise ToolFailure(f"functional scorer failed: {str(exc)[:1100]}", status="error") from None

    def artifacts(self, work: Path, prefix: str) -> list[dict]:
        artifacts = []
        for path in sorted(work.glob("*")):
            if path.is_file() and path.suffix in (".docx", ".pdf", ".json", ".png"):
                if path.stat().st_size > MAX_FILE_BYTES:
                    raise ToolFailure("artifact exceeds 20 MB file size limit")
                artifacts.append(
                    {
                        "key": f"{prefix}/{path.name}",
                        "content_type": DOCX
                        if path.suffix == ".docx"
                        else mimetypes.guess_type(path.name)[0] or "application/octet-stream",
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                        "size": path.stat().st_size,
                    }
                )
        return artifacts

    def versions(self) -> dict:
        from neurotic_docx_bench import content_cache

        metadata = Path("/app/tool-versions.json")
        versions = json.loads(metadata.read_text()) if metadata.exists() else {}
        from importlib.metadata import version

        from docx_scalpel._host_locator import find_host

        versions["docxodus_wheel"] = version("docx-scalpel")
        command([sys.executable, "-c", "import neurotic_docx_bench.superdoc_redlines_gen"], 30)
        versions["docxodus_host_sha256"] = hashlib.sha256(find_host().read_bytes()).hexdigest()
        versions.update(
            {
                "jubarte": command([self.config.jubarte, "--version"], 30),
                "jubarte_sha256": hashlib.sha256(Path(self.config.jubarte).read_bytes()).hexdigest(),
                "soffice": command(["soffice", "--version"], 30),
                "docxide": versions.get("docxide", "0.18.3"),
                "docxide_sha256": hashlib.sha256(Path("/usr/local/bin/docxide-pdf").read_bytes()).hexdigest(),
                "scorer": content_cache.scorer_fingerprint(),
                "raster": content_cache.raster_engine(),
                "python": sys.version.split()[0],
                "dpi": self.config.dpi,
                "worker_source_sha256": hashlib.sha256(
                    b"".join(path.read_bytes() for path in sorted(Path(__file__).parent.glob("*.py")))
                ).hexdigest(),
            }
        )
        return versions
