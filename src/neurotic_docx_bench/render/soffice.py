"""LibreOffice (``soffice``) DOCX→PDF renderer — Python port of ``.old/docx-to-pdf.sh``.

Faithful port requirements (must match the shell script's behaviour):
- **Locate soffice:** ``$SOFFICE`` env override → ``shutil.which("soffice")`` →
  ``/Applications/LibreOffice.app/Contents/MacOS/soffice`` → raise ``RuntimeError``.
- **Per-worker isolated profile:** each conversion gets its own
  ``tempfile.mkdtemp()`` and passes ``-env:UserInstallation=file://<profile>`` so
  concurrent soffice instances don't fight over the profile lock; remove it afterwards.
- **Convert command:** ``soffice -env:UserInstallation=file://<profile> --headless
  --norestore --nofirststartwizard --convert-to pdf --outdir <out_dir> <docx>`` and then
  verify ``<out_dir>/<stem>.pdf`` exists (soffice can exit 0 without producing a file).
- **Skip/force:** if not ``force`` and the target PDF already exists → skip (``ok=True,
  skipped=True``).
- **Parallelism:** ``ThreadPoolExecutor(max_workers=jobs)`` over the source ``*.docx``
  (top-level only, sorted), default ``jobs=4``.
- **Output dir:** ``<work_dir>/pdf`` (mirrors the shell script's ``<folder>/pdf``).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from neurotic_docx_bench.render.base import RenderReport, RenderResult

_APP_SOFFICE = Path("/Applications/LibreOffice.app/Contents/MacOS/soffice")


def find_soffice() -> Path:
    """Locate the soffice binary; raise RuntimeError if not found.

    Order (matches docx-to-pdf.sh): ``$SOFFICE`` → ``which soffice`` → the macOS app path.
    """
    override = os.environ.get("SOFFICE")
    if override:
        return Path(override)
    which = shutil.which("soffice")
    if which:
        return Path(which)
    if _APP_SOFFICE.exists():
        return _APP_SOFFICE
    raise RuntimeError("soffice / LibreOffice not found (set $SOFFICE to override)")


def convert_one(
    soffice: Path,
    docx: Path,
    out_dir: Path,
    *,
    force: bool = False,
    timeout: float = 1200.0,
    retries: int = 1,
) -> RenderResult:
    """Convert a single DOCX to PDF inside an isolated LibreOffice user profile.

    A failed attempt is retried up to ``retries`` times: concurrent soffice instances
    occasionally fail transiently even with isolated profiles, and a retry converts a
    flaky parallel run into a deterministic one. Each attempt still requires BOTH a
    clean exit AND the output file (shell parity).
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf = out_dir / f"{docx.stem}.pdf"
    t0 = time.perf_counter_ns()
    if pdf.exists():
        if not force:
            return RenderResult(source=docx, pdf=pdf, ok=True, skipped=True, duration_ns=time.perf_counter_ns() - t0)
        # Force: remove the stale PDF first so a crashed re-render can't masquerade as
        # success by leaving the previous output in place (shell parity: `&& [[ -f pdf ]]`).
        pdf.unlink()

    err = "soffice failed"
    for _attempt in range(max(1, retries + 1)):
        profile = Path(tempfile.mkdtemp(prefix="lo-profile."))
        try:
            proc = subprocess.run(
                [
                    str(soffice),
                    f"-env:UserInstallation=file://{profile}",
                    "--headless",
                    "--norestore",
                    "--nofirststartwizard",
                    "--convert-to",
                    "pdf",
                    "--outdir",
                    str(out_dir),
                    str(docx),
                ],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            err = "soffice timed out"
            continue
        finally:
            shutil.rmtree(profile, ignore_errors=True)

        # Require BOTH a clean exit AND the output file (soffice can exit 0 without
        # writing, or exit non-zero after leaving a partial/old file).
        if proc.returncode == 0 and pdf.exists():
            return RenderResult(source=docx, pdf=pdf, ok=True, duration_ns=time.perf_counter_ns() - t0)
        err = (proc.stderr or proc.stdout or "").strip() or f"exit {proc.returncode}"
        pdf.unlink(missing_ok=True)  # never leave a partial file for the next attempt
    return RenderResult(source=docx, pdf=None, ok=False, error=err, duration_ns=time.perf_counter_ns() - t0)


class SofficeRenderer:
    name = "soffice"

    def __init__(self, soffice: Path | None = None) -> None:
        self._soffice = soffice

    def _resolve_soffice(self) -> Path:
        return self._soffice if self._soffice is not None else find_soffice()

    def to_pdfs(
        self,
        source_dir: Path,
        work_dir: Path,
        *,
        force: bool = False,
        jobs: int = 4,
        timeout: float = 1200.0,
    ) -> RenderReport:
        soffice = self._resolve_soffice()
        out_dir = work_dir / "pdf"
        out_dir.mkdir(parents=True, exist_ok=True)
        docs = sorted(source_dir.glob("*.docx"))

        results: list[RenderResult] = []
        if docs:
            with ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
                results = list(
                    pool.map(
                        lambda d: convert_one(soffice, d, out_dir, force=force, timeout=timeout),
                        docs,
                    ),
                )
        return RenderReport(pdf_dir=out_dir, results=results)
