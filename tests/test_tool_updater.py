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


def test_missing_node_modules_raises_naming_bun_install(tmp_path):
    """A configured npm package that resolves to None poisons the skip identity.

    Runs are skipped on (vendor, tool_version, config_hash). With tool_version None a
    run both records `tool_version: null` in the JSONL and collides with every OTHER
    unresolved run in that identity — so a stale line can suppress a real run. Failing
    loudly at resolution is the only place the cause is still visible.
    """
    with pytest.raises(RuntimeError) as exc:
        tool_updater.resolve_tool_version(package="jubarte@latest", cwd=tmp_path, no_update=True)
    msg = str(exc.value)
    assert "bun install" in msg
    assert "jubarte" in msg


def test_missing_python_package_raises_naming_the_distribution(tmp_path):
    with pytest.raises(RuntimeError) as exc:
        tool_updater.resolve_tool_version(python_package="no-such-dist-xyz==1.0.0")
    msg = str(exc.value)
    assert "no-such-dist-xyz" in msg
    assert "uv" in msg


def test_no_configured_source_still_returns_none():
    """Runs with no version pin (generate:-only) legitimately have no version — that
    is not an error, and turning it into one would break every such run."""
    assert tool_updater.resolve_tool_version() is None


def test_resolvable_npm_package_does_not_raise(tmp_path):
    pkg_dir = tmp_path / "node_modules" / "superdoc"
    pkg_dir.mkdir(parents=True)
    (pkg_dir / "package.json").write_text(json.dumps({"version": "0.9.1"}))
    assert tool_updater.resolve_tool_version(
        package="superdoc@latest", cwd=tmp_path, no_update=True,
    ) == "0.9.1"


def test_unresolvable_version_fails_only_its_own_run(tmp_path, monkeypatch):
    """resolve_tool_version now raises — but the driver's skip-check calls it OUTSIDE
    the per-run try/except, so an uncaught raise there would abort the whole bench
    instead of failing one run ("one run's failure must not stop the rest").
    """
    import shutil

    from typer.testing import CliRunner

    from neurotic_docx_bench.cli import app

    root = tmp_path / "corpus"
    (root / "pdf_oracle").mkdir(parents=True)
    (root / "pdf_oracle" / "a_b_redline.pdf").write_bytes(b"%PDF-1.4 oracle-a\n")
    cand = tmp_path / "cand"
    cand.mkdir()
    shutil.copy(root / "pdf_oracle" / "a_b_redline.pdf", cand / "a_b_good_redline.pdf")

    cfg = tmp_path / "bench.yaml"
    cfg.write_text(
        f"source_of_truth: {root / 'pdf_oracle'}\n"
        "runs:\n"
        f"  - {{name: broken, render: passthrough, modified: {cand}, "
        f"package: 'no-such-pkg@1.0.0', jobs: 1}}\n"
        f"  - {{name: good, render: passthrough, modified: {cand}, "
        f"unversioned: true, jobs: 1}}\n",
    )
    monkeypatch.setenv("BENCH_NO_UPDATE", "1")
    result = CliRunner().invoke(
        app,
        ["run", "--config", str(cfg), "--results-dir", str(tmp_path / "results"),
         "--runs-dir", str(tmp_path / "runs"), "--no-gate"],
    )

    assert "no-such-pkg" in result.output, "the broken run must name its cause"
    assert "bun install" in result.output
    # The second run must still have been attempted — that is the whole point.
    assert "good" in result.output
    assert result.exit_code != 0


def test_npm_install_pins_exactly_so_the_recorded_version_cannot_drift(monkeypatch, tmp_path):
    """A bench.yaml pin is exact; the install must not widen it to a caret range.

    Plan Chapter 6 D5. `npm install pkg@9.0.0` writes `"pkg": "^9.0.0"` into
    package.json by default, so a later plain `npm install`/`bun install` can
    resolve 9.1.0 while bench.yaml still says 9.0.0 — the recorded version and
    the measured code drift apart, which is exactly the split-brain D5 names.
    Observed live: a run rewrote `"docxodus": "9.0.0"` to `"^9.0.0"`.
    """
    seen: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        seen.append(list(cmd))
        class R:
            returncode = 0
            stdout = stderr = ""
        return R()

    monkeypatch.setattr(tool_updater.subprocess, "run", fake_run)
    monkeypatch.setattr(tool_updater, "installed_npm_version", lambda *a, **k: "9.0.0")

    tool_updater.update_npm_package("docxodus@9.0.0", tmp_path, no_update=False)

    assert seen, "no install command was issued"
    cmd = seen[0]
    assert any(f in cmd for f in ("--save-exact", "--exact")), (
        f"install must pin exactly or the pin silently widens to a caret: {cmd}"
    )


def test_npm_install_uses_bun_not_npm(monkeypatch, tmp_path):
    """Vendor installs go through bun, the package manager this repo standardises on.

    npm resolves peer dependencies strictly across ONE shared node_modules, so
    installing one vendor can refuse to install another. Observed live: after
    superdoc@2.3.0 landed (peer pdfjs-dist ^5.4.296), `npm install
    @stll/folio-core@0.15.13` exited 1 with ERESOLVE, and BOTH folio and
    superdoc-ts were recorded as failed runs -- our dependency graph, printed as
    their crash. bun installs the same specs without the conflict and writes an
    exact pin.
    """
    seen: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        seen.append(list(cmd))
        class R:
            returncode = 0
            stdout = stderr = ""
        return R()

    monkeypatch.setattr(tool_updater.subprocess, "run", fake_run)
    monkeypatch.setattr(tool_updater, "installed_npm_version", lambda *a, **k: "0.15.13")

    tool_updater.update_npm_package("@stll/folio-core@0.15.13", tmp_path, no_update=False)

    assert seen, "no install command was issued"
    assert seen[0][0] == "bun", f"must install with bun, not {seen[0][0]!r}: {seen[0]}"
