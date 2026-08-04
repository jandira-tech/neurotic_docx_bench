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
import tomllib
from pathlib import Path


def resolve_local_version(dist_path: Path) -> str:
    """Version identifier for a local tool build directory.

    ``<build>/package.json``'s ``version`` if present, else ``<dirname>@<sha256[:12]>`` over
    the (path, bytes) of every file in the build — stable and distinct per build.

    Content-hash pins are untraceable to source on their own, so when the build
    carries an ``ENGINE_COMMIT.txt`` (written at install time; the engine's git
    commit), the pin gains a ``+git.<sha>`` suffix (GET_JUBARTE_RUST.md: "record
    the Jubarte Git commit alongside that hash"). ``ENGINE_*.txt`` files are
    provenance metadata, excluded from the hash — stamping them never changes
    the pin itself.
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
        if f.name.startswith("ENGINE_") and f.suffix == ".txt":
            continue
        digest.update(f.relative_to(dist_path).as_posix().encode())
        digest.update(f.read_bytes())
    pin = f"{dist_path.name}@{digest.hexdigest()[:12]}"
    commit_file = dist_path / "ENGINE_COMMIT.txt"
    if commit_file.is_file():
        commit = commit_file.read_text().strip()
        if commit:
            return f"{pin}+git.{commit}"
    return pin


def resolve_build_recipe(dist_path: Path) -> dict[str, list[str]] | None:
    """The FULL build recipe (rustflags + wasm-opt) that shapes a wasm artifact (TODO §2).

    ``resolve_local_version`` records *which* build produced a result; it does NOT
    record the build FLAGS that shape the artifact. For the wasm dist those flags live
    in two TOML files, one level up from the loaded ``pkg/`` artifact:

    - ``.cargo/config.toml`` → ``[target.wasm32-unknown-unknown] rustflags``
    - ``Cargo.toml`` → ``[package.metadata.wasm-pack.profile.release] wasm-opt``

    Returns ``{"rustflags": [...], "wasm_opt": [...]}`` (either list empty when its
    sub-key is absent), or ``None`` when NEITHER TOML is present — a plain binary dist
    has no cargo build recipe and yields ``None``, not an error.

    ``dist_path`` may be the dir that holds the TOML files directly, or the ``pkg/``
    artifact dir whose parent holds them.
    """
    dist_path = Path(dist_path)
    for base in (dist_path, dist_path.parent):
        cargo_config = base / ".cargo" / "config.toml"
        cargo_toml = base / "Cargo.toml"
        if not cargo_config.is_file() and not cargo_toml.is_file():
            continue
        rustflags: list[str] = []
        wasm_opt: list[str] = []
        if cargo_config.is_file():
            config = tomllib.loads(cargo_config.read_text())
            rustflags = list(
                config.get("target", {})
                .get("wasm32-unknown-unknown", {})
                .get("rustflags", []),
            )
        if cargo_toml.is_file():
            manifest = tomllib.loads(cargo_toml.read_text())
            wasm_opt = list(
                manifest.get("package", {})
                .get("metadata", {})
                .get("wasm-pack", {})
                .get("profile", {})
                .get("release", {})
                .get("wasm-opt", []),
            )
        return {"rustflags": rustflags, "wasm_opt": wasm_opt}
    return None


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
            # --save-exact: bench.yaml pins are EXACT, and the default caret range
            # silently widens them. A run was observed rewriting
            # ``"docxodus": "9.0.0"`` to ``"^9.0.0"``, after which a later install
            # could resolve 9.1.0 while bench.yaml still claimed 9.0.0 — the
            # recorded tool_version and the measured code drifting apart, which is
            # the split-brain of plan Chapter 6 D5.
            ["npm", "install", "--save-exact", spec],
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

    A CONFIGURED source that fails to resolve raises instead of returning None. Runs
    skip on (vendor, tool_version, config_hash), so a None version both records
    ``tool_version: null`` in the JSONL and collides with every other unresolved run in
    that identity — letting a stale line suppress a real one. ``dist`` already raised
    (FileNotFoundError); npm and Python did not.

    No configured source at all still returns None: ``generate:``-only runs legitimately
    have no version pin.
    """
    if dist is not None:
        return resolve_local_version(dist)
    if package is not None:
        version = update_npm_package(package, cwd or Path.cwd(), no_update=no_update)
        if not version:
            raise RuntimeError(
                f"tool_version unresolved for npm package {package!r}: no "
                f"node_modules/{_package_name(package)}/package.json under "
                f"{cwd or Path.cwd()}. Run `bun install` (the repo's package manager) "
                f"before benchmarking, or drop the `package:` pin from this run.",
            )
        return version
    if python_package is not None:
        version = installed_python_version(python_package)
        if not version:
            raise RuntimeError(
                f"tool_version unresolved for Python package "
                f"{_python_package_name(python_package)!r}: not installed in this "
                f"environment. Run `uv sync` (or `uv pip install "
                f"{python_package}`) before benchmarking, or drop the "
                f"`python_package:` pin from this run.",
            )
        return version
    return None
