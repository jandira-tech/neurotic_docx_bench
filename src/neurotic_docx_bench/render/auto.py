"""`auto`: Microsoft Word where this machine has it, LibreOffice otherwise."""

from __future__ import annotations

import os

AUTO = "auto"
# ``word`` or ``soffice`` pins the backend ``auto`` resolves to on this machine.
ENV = "BENCH_RENDERER"


def default_backend() -> str:
    """``$BENCH_RENDERER`` when it names a backend, else ``word`` when Word can print
    here (macOS with Word), else ``soffice``."""
    pinned = os.environ.get(ENV, AUTO)
    if pinned in ("word", "soffice"):
        return pinned
    from neurotic_docx_bench.render import word

    return "word" if word.word_available() else "soffice"


def resolve_backend(name: str) -> str:
    """The concrete backend for ``name``: ``auto`` becomes :func:`default_backend`."""
    return default_backend() if name == AUTO else name
