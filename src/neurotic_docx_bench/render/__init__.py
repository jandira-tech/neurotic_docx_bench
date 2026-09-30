"""Render backends. ``auto`` is Microsoft Word where this machine has it, LibreOffice otherwise."""

from neurotic_docx_bench.render.auto import AUTO, ENV, default_backend, resolve_backend

__all__ = ["AUTO", "ENV", "default_backend", "resolve_backend"]
