"""tool_updater — local build version resolution + npm version reading."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from neurotic_docx_bench import tool_updater

REPO_ROOT = Path(__file__).resolve().parents[1]
DIST = REPO_ROOT / "dist"


def test_local_version_from_package_json(tmp_path):
    build = tmp_path / "mytool"
    build.mkdir()
    (build / "package.json").write_text(json.dumps({"version": "1.6.2"}))
    (build / "index.js").write_text("// code")
    assert tool_updater.resolve_local_version(build) == "1.6.2"


def test_local_version_content_hash_fallback(tmp_path):
    build = tmp_path / "nover"
    build.mkdir()
    (build / "a.js").write_text("alpha")
    v = tool_updater.resolve_local_version(build)
    assert v.startswith("nover@") and len(v.split("@")[1]) == 12
    # same content → same version; changed content → different version
    assert tool_updater.resolve_local_version(build) == v
    (build / "a.js").write_text("beta")
    assert tool_updater.resolve_local_version(build) != v


def test_local_version_missing_dir(tmp_path):
    with pytest.raises(FileNotFoundError):
        tool_updater.resolve_local_version(tmp_path / "nope")


def test_local_version_records_engine_source_commit(tmp_path):
    """GET_JUBARTE_RUST.md mandate: record the engine's git commit alongside a
    content-hash pin. ENGINE_*.txt is provenance metadata — it rides in the
    version string as ``+git.<sha>`` and is EXCLUDED from the content hash, so
    stamping provenance never changes the pin itself."""
    build = tmp_path / "jubarte-rust"
    build.mkdir()
    (build / "redline").write_bytes(b"\x7fELF-fake-binary")
    bare = tool_updater.resolve_local_version(build)

    (build / "ENGINE_COMMIT.txt").write_text("dea8d27\n")
    stamped = tool_updater.resolve_local_version(build)
    assert stamped == f"{bare}+git.dea8d27"

    # Provenance metadata must not perturb the content hash.
    (build / "ENGINE_COMMIT.txt").write_text("othersha\n")
    restamped = tool_updater.resolve_local_version(build)
    assert restamped == f"{bare}+git.othersha"


@pytest.mark.skipif(
    not (DIST / "jubarte-final").is_dir(),
    reason="dist/ jubarte-final build absent (git-ignored)",
)
def test_jubarte_final_version():
    v = tool_updater.resolve_local_version(DIST / "jubarte-final")
    assert v, "jubarte-final build must resolve to a version"


def test_installed_npm_version(tmp_path):
    pkg_dir = tmp_path / "node_modules" / "docxodus"
    pkg_dir.mkdir(parents=True)
    (pkg_dir / "package.json").write_text(json.dumps({"version": "3.1.0"}))
    assert tool_updater.installed_npm_version("docxodus", tmp_path) == "3.1.0"
    assert tool_updater.installed_npm_version("missing", tmp_path) is None


def test_update_npm_no_update_reads_installed(tmp_path):
    pkg_dir = tmp_path / "node_modules" / "superdoc"
    pkg_dir.mkdir(parents=True)
    (pkg_dir / "package.json").write_text(json.dumps({"version": "0.9.1"}))
    # no_update=True must not shell out to npm; just resolve installed version
    assert tool_updater.update_npm_package("superdoc@latest", tmp_path, no_update=True) == "0.9.1"


def test_resolve_precedence(tmp_path):
    build = tmp_path / "b"
    build.mkdir()
    (build / "package.json").write_text(json.dumps({"version": "9.9.9"}))
    assert tool_updater.resolve_tool_version(dist=build) == "9.9.9"
    assert tool_updater.resolve_tool_version() is None


def test_package_name_parsing():
    assert tool_updater._package_name("jubarte@latest") == "jubarte"
    assert tool_updater._package_name("@harbour-enterprises/superdoc@latest") == (
        "@harbour-enterprises/superdoc"
    )
    assert tool_updater._package_name("docxodus") == "docxodus"


def test_python_package_name_strips_pin():
    assert tool_updater._python_package_name("superdoc-sdk==1.19.2") == "superdoc-sdk"
    assert tool_updater._python_package_name("superdoc-sdk") == "superdoc-sdk"
    assert tool_updater._python_package_name("  foo==1.0.0  ") == "foo"


def test_resolve_python_package_pin_reads_installed(monkeypatch):
    """``python_package: name==x.y.z`` must resolve via the bare distribution name."""
    monkeypatch.setattr(
        tool_updater,
        "installed_python_version",
        lambda pkg: "1.19.2" if tool_updater._python_package_name(pkg) == "superdoc-sdk" else None,
    )
    assert (
        tool_updater.resolve_tool_version(python_package="superdoc-sdk==1.19.2") == "1.19.2"
    )
