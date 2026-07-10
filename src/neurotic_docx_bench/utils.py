"""Utility functions for superdoc-benchmark."""

import hashlib
import re
from pathlib import Path


def find_docx_files(path: Path) -> list[Path]:
    """Find all .docx files in a path.

    If path is a file, returns it (if it's a .docx).
    If path is a directory, recursively finds all .docx files.

    Args:
        path: File or directory path to search.

    Returns:
        List of paths to .docx files, sorted alphabetically.
    """
    if path.is_file():
        if path.suffix.lower() == ".docx":
            return [path]
        return []

    if path.is_dir():
        docx_files = list(path.rglob("*.docx"))
        # Filter out temp files (start with ~$)
        docx_files = [f for f in docx_files if not f.name.startswith("~$")]
        return sorted(docx_files)

    return []


def validate_path(path_str: str) -> Path | None:
    """Validate and resolve a path string.

    Handles shell-escaped paths (e.g., spaces as '\\ ') that users may
    copy from terminal or get from tab-completion.

    Args:
        path_str: Path string from user input.

    Returns:
        Resolved Path if valid, None otherwise.
    """
    if not path_str.strip():
        return None

    # Remove shell escape characters (backslash before space, parens, etc.)
    # This handles paths like: /path/to/My\ File\ \(1\).docx
    unescaped = re.sub(r"\\(.)", r"\1", path_str.strip())

    path = Path(unescaped).expanduser().resolve()

    if not path.exists():
        return None

    return path


def make_docx_output_name(docx_path: Path, root: Path | None = None) -> str:
    """Build a filesystem-safe name for outputs tied to a docx file.

    Uses a relative path when under root; otherwise uses a short name + hash
    to avoid unreadably long absolute paths and collisions.
    """
    if root is None:
        try:
            root = Path.cwd()
        except OSError:
            root = None

    base_path: Path | None = None
    if root is not None:
        try:
            base_path = docx_path.relative_to(root)
        except ValueError:
            base_path = None

    if base_path is None:
        parent = docx_path.parent.name or "documents"
        stem = docx_path.stem
        safe_parent = re.sub(r"[^A-Za-z0-9._-]+", "_", parent).strip("_") or "documents"
        safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("_") or "document"
        path_hash = hashlib.md5(str(docx_path).encode()).hexdigest()[:6]
        return f"{safe_parent}__{safe_stem}__{path_hash}"

    base_path = base_path.with_suffix("")
    name = base_path.as_posix()
    name = re.sub(r"[\\/]+", "__", name)
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    name = name.strip("_")
    return name or docx_path.stem


def make_docx_output_path(docx_path: Path, root: Path | None = None) -> Path:
    """Build a filesystem-safe relative path for outputs tied to a docx file."""
    if root is not None:
        try:
            rel_path = docx_path.relative_to(root).with_suffix("")
        except ValueError:
            rel_path = None
        if rel_path is not None:
            safe_parts = []
            for part in rel_path.parts:
                safe = re.sub(r"[^A-Za-z0-9._-]+", "_", part).strip("_")
                safe_parts.append(safe or "document")
            return Path(*safe_parts)

    return Path(make_docx_output_name(docx_path, root))
