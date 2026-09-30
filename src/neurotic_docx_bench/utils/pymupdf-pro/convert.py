"""pymupdf-pro DOCX to PDF, one document per call: ``convert.py <src.docx> <dest.pdf>``.

Runs in this directory's own env (pymupdfpro pins its own MuPDF, which must not
replace the bench scorer's). ``PYMUPDFPRO_LICENSE_KEY`` unlocks the full product;
without it pymupdf-pro converts only the first 3 pages of any document, and
``--version`` says so, so every ledger row records which mode produced it.
"""

from __future__ import annotations

import importlib.metadata
import os
import sys
import tempfile

UNLICENSED_PAGE_CAP = 3
# The Restricted Mode banner is already recorded by ``--version``.
NOISE_PREFIXES = ("Fontconfig ", "PyMuPDFPro: Restricted Mode")


def version() -> str:
    mode = "licensed" if os.environ.get("PYMUPDFPRO_LICENSE_KEY") else f"unlicensed, first {UNLICENSED_PAGE_CAP} pages"
    return f"pymupdf-pro {importlib.metadata.version('pymupdfpro')} ({mode})"


def main(argv: list[str]) -> int:
    if argv == ["--version"]:
        print(version())
        return 0
    if len(argv) != 2:
        print("usage: convert.py <src.docx> <dest.pdf>", file=sys.stderr)
        return 2
    # MuPDF and fontconfig write straight to fd 2, so a failure record would be
    # dozens of font-cache warnings around the one line that matters. Capture fd 2
    # and pass on only the lines that are not that noise.
    saved = os.dup(2)
    with tempfile.TemporaryFile() as captured:
        os.dup2(captured.fileno(), 2)
        try:
            import pymupdf.pro

            pymupdf.pro.unlock(os.environ.get("PYMUPDFPRO_LICENSE_KEY") or None)
            pymupdf.pro.office_to_pdf(argv[0], argv[1])
            error = None
        except Exception as exc:  # the bench records any convert error as a generate failure
            error = f"{type(exc).__name__}: {exc}"
        finally:
            sys.stderr.flush()
            os.dup2(saved, 2)
            os.close(saved)
        captured.seek(0)
        noise = captured.read().decode("utf-8", "replace").splitlines()
    kept = [line for line in noise if line.strip() and not line.startswith(NOISE_PREFIXES)]
    for line in [*kept, *([error] if error else [])]:
        print(line, file=sys.stderr)
    return 1 if error else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
