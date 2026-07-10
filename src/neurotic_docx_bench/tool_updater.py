"""Resolve the exact version of each tool that produced a result, and (optionally) update
npm-published tools to latest before a run (PLAN §9).

Two kinds of tool:
- **local bundle** (jubarte lives at ``dist/<build>/``, possibly several builds): the
  version is the build's ``package.json`` version if present, else ``<dir>@<content-hash>``
  so distinct builds are distinguishable and every result is attributable to one build.
- **npm-published** (superdoc, docxodus): ``npm i <pkg>@latest`` then read the installed
  version. ``--no-update`` / ``BENCH_NO_UPDATE`` pins to whatever is installed.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path


def resolve_local_version(dist_path: Path) -> str:
    """Version identifier for a local tool build directory.

    ``<build>/package.json``'s ``version`` if present, else ``<dirname>@<sha256[:12]>`` over
    the (path, bytes) of every file in the build — stable and distinct per build.
    """
    dist_path = Path(dist_path)
    if not dist_path.is_dir():
        raise FileNotFoundError(f"tool build dir not found: {dist_path}")
    pkg = dist_path / "package.json"
    if pkg.is_file():
        try:
            version = json.loads(pkg.read_text()).get("version")
            if version:
                return str(version)
        except (json.JSONDecodeError, OSError):
            pass
    digest = hashlib.sha256()
    for f in sorted(p for p in dist_path.rglob("*") if p.is_file()):
        digest.update(f.relative_to(dist_path).as_posix().encode())
        digest.update(f.read_bytes())
    return f"{dist_path.name}@{digest.hexdigest()[:12]}"


def _package_name(spec: str) -> str:
    """'jubarte@latest' → 'jubarte'; '@scope/pkg@latest' → '@scope/pkg'."""
    if spec.startswith("@"):
        at = spec.find("@", 1)
        return spec[:at] if at != -1 else spec
    return spec.split("@", 1)[0]


def installed_npm_version(package: str, cwd: Path) -> str | None:
    """Read the installed version from ``<cwd>/node_modules/<package>/package.json``."""
    pkg_json = Path(cwd) / "node_modules" / package / "package.json"
    if not pkg_json.is_file():
        return None
    try:
        return str(json.loads(pkg_json.read_text()).get("version") or "") or None
    except (json.JSONDecodeError, OSError):
        return None


def update_npm_package(spec: str, cwd: Path, *, no_update: bool | None = None) -> str | None:
    """``npm i <spec>`` (unless pinned) and return the resolved installed version.

    ``no_update=None`` consults ``BENCH_NO_UPDATE``. Returns None if resolution fails.
    """
    if no_update is None:
        no_update = os.environ.get("BENCH_NO_UPDATE") == "1"
    package = _package_name(spec)
    if not no_update:
        subprocess.run(
            ["npm", "install", spec],
            cwd=str(cwd),
            check=True,
            capture_output=True,
            text=True,
        )
    return installed_npm_version(package, cwd)


def _python_package_name(spec: str) -> str:
    """``superdoc-sdk==1.19.2`` → ``superdoc-sdk``; bare names pass through."""
    spec = spec.strip()
    if "==" in spec:
        return spec.split("==", 1)[0].strip()
    return spec


def installed_python_version(package: str) -> str | None:
    """Installed version of a Python (pip/uv) package, e.g. ``superdoc-sdk`` → ``1.19.2``.

    Accepts either a bare name or a pin (``superdoc-sdk==1.19.2``); importlib only
    understands the distribution name.
    """
    from importlib.metadata import PackageNotFoundError, version

    try:
        return version(_python_package_name(package))
    except PackageNotFoundError:
        return None


def resolve_tool_version(
    *,
    dist: Path | None = None,
    package: str | None = None,
    python_package: str | None = None,
    cwd: Path | None = None,
    no_update: bool | None = None,
) -> str | None:
    """Resolve a run's ``tool_version``: local build (``dist``) → npm (``package``) →
    Python package (``python_package``); returns None when none is configured.
    """
    if dist is not None:
        return resolve_local_version(dist)
    if package is not None:
        return update_npm_package(package, cwd or Path.cwd(), no_update=no_update)
    if python_package is not None:
        return installed_python_version(python_package)
    return None
