"""Hugging Face hub round trip: sha256 manifests, fixture download/upload, results upload.

Every network call goes through an injected ``api`` object; ``FakeHub`` records the
calls and plays the hub back (snapshot_download copies what was uploaded, list_repo_tree
reports the stored hashes), so the prune-after-verify rule is tested without a token.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from neurotic_docx_bench import hub

runner = CliRunner()


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


class FakeHub:
    """Records calls; stores uploaded folders by (repo_id, path_in_repo)."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []
        self.stored: dict[str, dict[str, bytes]] = {}
        self.corrupt: set[str] = set()

    def create_repo(
        self, repo_id: str, *, repo_type: str, exist_ok: bool = False
    ) -> str:
        self.calls.append(
            (
                "create_repo",
                {"repo_id": repo_id, "repo_type": repo_type, "exist_ok": exist_ok},
            )
        )
        self.stored.setdefault(repo_id, {})
        return repo_id

    def upload_folder(
        self,
        *,
        repo_id: str,
        folder_path: str | Path,
        repo_type: str,
        path_in_repo: str | None = None,
        commit_message: str | None = None,
        ignore_patterns: list[str] | None = None,
    ) -> str:
        self.calls.append(
            (
                "upload_folder",
                {
                    "repo_id": repo_id,
                    "folder_path": str(folder_path),
                    "repo_type": repo_type,
                    "path_in_repo": path_in_repo,
                    "commit_message": commit_message,
                },
            )
        )
        store = self.stored.setdefault(repo_id, {})
        root = Path(folder_path)
        prefix = (path_in_repo or "").strip("/")
        for p in sorted(root.rglob("*")):
            if p.is_file():
                rel = p.relative_to(root).as_posix()
                store[f"{prefix}/{rel}" if prefix else rel] = p.read_bytes()
        return "https://huggingface.co/fake"

    def snapshot_download(
        self,
        repo_id: str,
        *,
        repo_type: str,
        revision: str | None = None,
        local_dir: str | Path | None = None,
    ) -> str:
        self.calls.append(
            (
                "snapshot_download",
                {
                    "repo_id": repo_id,
                    "repo_type": repo_type,
                    "revision": revision,
                    "local_dir": str(local_dir),
                },
            )
        )
        assert local_dir is not None
        dest = Path(local_dir)
        for rel, data in self.stored.get(repo_id, {}).items():
            out = dest / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(data)
        return str(dest)

    def list_repo_tree(
        self,
        repo_id: str,
        *,
        repo_type: str,
        path_in_repo: str | None = None,
        recursive: bool = True,
        expand: bool = True,
    ):
        self.calls.append(
            ("list_repo_tree", {"repo_id": repo_id, "repo_type": repo_type})
        )
        for rel, data in self.stored.get(repo_id, {}).items():
            if path_in_repo and not rel.startswith(path_in_repo.strip("/") + "/"):
                continue
            sha256 = hashlib.sha256(data).hexdigest()
            if rel in self.corrupt:
                sha256 = "0" * 64
            if len(data) > 64:
                yield SimpleNamespace(
                    path=rel,
                    lfs={"sha256": sha256, "size": len(data)},
                    blob_id=None,
                    size=len(data),
                )
            else:
                blob = hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()
                if rel in self.corrupt:
                    blob = "0" * 40
                yield SimpleNamespace(path=rel, lfs=None, blob_id=blob, size=len(data))


@pytest.fixture
def corpus(tmp_path: Path) -> Path:
    root = tmp_path / "corpus"
    (root / "word_based" / "pdf_redlines_word").mkdir(parents=True)
    (root / "word_based" / "pdf_redlines_word" / "a_redline.pdf").write_bytes(
        b"%PDF-a" * 40
    )
    (root / "word_based" / "pdf_redlines_word" / "b_redline.pdf").write_bytes(
        b"%PDF-b" * 40
    )
    (root / "word_based" / "pdf_source").mkdir()
    (root / "word_based" / "pdf_source" / "a.pdf").write_bytes(b"%PDF-plain")
    (root / "holdout_combined.txt").write_text("b\n")
    return root


@pytest.fixture
def repo(tmp_path: Path, corpus: Path) -> Path:
    """A repository root with results stores, pages, a run folder and the corpus."""
    root = tmp_path
    results = root / "results"
    (results / "detail").mkdir(parents=True)
    (results / "archive").mkdir()
    (results / "docx_to_pdf_speed").mkdir()
    (results / "bench.jsonl").write_text('{"id_run": "r1", "vendor": "x"}\n')
    (results / "converters.jsonl").write_text("")
    (results / "docsets.json").write_text(
        json.dumps(
            {
                "56a686ebe1a8": {
                    "benchmark": "visual_redlines",
                    "holdout_mode": "excluded",
                    "n": 1,
                    "source_dirs": ["corpus/word_based/pdf_redlines_word"],
                },
                "6cc8f3b525d3": {
                    "benchmark": "visual_rendering",
                    "holdout_mode": "excluded",
                    "n": 1,
                    "source_dirs": ["corpus/word_based/pdf_source"],
                },
            }
        )
    )
    (results / "detail" / "r1__visual_redlines.json.gz").write_bytes(
        b"\x1f\x8b" + b"x" * 100
    )
    (results / "archive" / "MANIFEST.md").write_text("# archive\n")
    (results / "bench.jsonl.lock").write_text("")
    (results / "scratch.log").write_text("noise")
    (root / "RESULTS.md").write_text("# results\n")
    (root / "RESULTS_DETAILED.md").write_text("# detailed\n")
    (root / "bench.registry.yaml").write_text("tools: {}\n")
    run = root / "runs" / "t_2026-09-27_10-58"
    (run / "score" / "doc1").mkdir(parents=True)
    (run / "score" / "doc1" / "page1.png").write_bytes(b"\x89PNG" + b"p" * 200)
    (run / "report.html").write_text("<html></html>")
    return root


# --- manifests -------------------------------------------------------------


def test_build_manifest_hashes_every_file_and_skips_itself(corpus: Path) -> None:
    (corpus / hub.MANIFEST_NAME).write_text("{}")
    manifest = hub.build_manifest(corpus)
    assert list(manifest) == sorted(manifest)
    assert hub.MANIFEST_NAME not in manifest
    assert manifest["word_based/pdf_redlines_word/a_redline.pdf"] == _sha(
        corpus / "word_based/pdf_redlines_word/a_redline.pdf"
    )
    assert manifest["holdout_combined.txt"] == _sha(corpus / "holdout_combined.txt")
    assert len(manifest) == 4


def test_write_then_verify_manifest_is_clean(corpus: Path) -> None:
    path = hub.write_manifest(corpus)
    assert path == corpus / hub.MANIFEST_NAME
    data = json.loads(path.read_text())
    assert data["algorithm"] == "sha256"
    assert data["files"]["holdout_combined.txt"] == _sha(
        corpus / "holdout_combined.txt"
    )
    report = hub.verify_manifest(corpus)
    assert report.ok
    assert report.checked == 4


def test_verify_manifest_reports_missing_mismatched_and_extra(corpus: Path) -> None:
    hub.write_manifest(corpus)
    (corpus / "word_based" / "pdf_source" / "a.pdf").write_bytes(b"tampered")
    (corpus / "holdout_combined.txt").unlink()
    (corpus / "stray.txt").write_text("extra")
    report = hub.verify_manifest(corpus)
    assert not report.ok
    assert report.mismatched == ("word_based/pdf_source/a.pdf",)
    assert report.missing == ("holdout_combined.txt",)
    assert report.extra == ("stray.txt",)


def test_verify_manifest_without_a_manifest_raises(corpus: Path) -> None:
    with pytest.raises(hub.ManifestError, match="MANIFEST"):
        hub.verify_manifest(corpus)


# --- fixtures repo ---------------------------------------------------------


def test_upload_fixtures_writes_the_manifest_then_uploads_the_folder(
    corpus: Path,
) -> None:
    api = FakeHub()
    report = hub.upload_fixtures(corpus, api=api)
    assert (corpus / hub.MANIFEST_NAME).exists()
    names = [c[0] for c in api.calls]
    assert names[:2] == ["create_repo", "upload_folder"]
    assert api.calls[0][1] == {
        "repo_id": hub.FIXTURES_REPO,
        "repo_type": "dataset",
        "exist_ok": True,
    }
    up = api.calls[1][1]
    assert up["folder_path"] == str(corpus)
    assert up["repo_type"] == "dataset"
    assert up["path_in_repo"] in (None, "", ".")
    assert hub.MANIFEST_NAME in api.stored[hub.FIXTURES_REPO]
    assert report.verified
    assert report.n_files == 6  # 4 fixtures + dataset card + manifest


def test_upload_fixtures_dry_run_makes_no_hub_calls(corpus: Path) -> None:
    api = FakeHub()
    report = hub.upload_fixtures(corpus, api=api, dry_run=True)
    assert api.calls == []
    assert not (corpus / hub.MANIFEST_NAME).exists()
    assert report.n_files == 6
    assert report.repo_id == hub.FIXTURES_REPO


def test_download_fixtures_verifies_the_manifest(corpus: Path, tmp_path: Path) -> None:
    api = FakeHub()
    hub.upload_fixtures(corpus, api=api)
    dest = tmp_path / "fresh"
    report = hub.download_fixtures(dest, api=api, revision="v0.7.0")
    assert report.ok and report.checked == 5  # 4 fixtures + dataset card
    assert (
        dest / "word_based/pdf_redlines_word/a_redline.pdf"
    ).read_bytes() == b"%PDF-a" * 40
    dl = next(c for c in api.calls if c[0] == "snapshot_download")[1]
    assert dl == {
        "repo_id": hub.FIXTURES_REPO,
        "repo_type": "dataset",
        "revision": "v0.7.0",
        "local_dir": str(dest),
    }


def test_download_fixtures_refuses_a_tampered_snapshot(
    corpus: Path, tmp_path: Path
) -> None:
    api = FakeHub()
    hub.upload_fixtures(corpus, api=api)
    api.stored[hub.FIXTURES_REPO]["word_based/pdf_source/a.pdf"] = b"evil"
    with pytest.raises(hub.ManifestError, match="word_based/pdf_source/a.pdf"):
        hub.download_fixtures(tmp_path / "fresh", api=api)


def test_download_fixtures_refuses_a_snapshot_without_a_manifest(
    tmp_path: Path,
) -> None:
    api = FakeHub()
    api.stored[hub.FIXTURES_REPO] = {"x.pdf": b"%PDF"}
    with pytest.raises(hub.ManifestError):
        hub.download_fixtures(tmp_path / "fresh", api=api)


# --- results repo ----------------------------------------------------------


def test_fixtures_used_lists_every_docset_source_file_with_its_hash(repo: Path) -> None:
    used = hub.fixtures_used(repo)
    assert set(used) == {"56a686ebe1a8", "6cc8f3b525d3"}
    entry = used["56a686ebe1a8"]
    assert entry["benchmark"] == "visual_redlines"
    assert entry["source_dirs"] == ["corpus/word_based/pdf_redlines_word"]
    assert entry["files"] == [
        {
            "path": "corpus/word_based/pdf_redlines_word/a_redline.pdf",
            "sha256": _sha(repo / "corpus/word_based/pdf_redlines_word/a_redline.pdf"),
        },
        {
            "path": "corpus/word_based/pdf_redlines_word/b_redline.pdf",
            "sha256": _sha(repo / "corpus/word_based/pdf_redlines_word/b_redline.pdf"),
        },
    ]


def test_stage_results_mirrors_stores_pages_fixtures_and_outputs(repo: Path) -> None:
    staging = repo / "results" / "hub"
    staged = hub.stage_results(
        repo, staging, version="0.7.0", run_dirs=[repo / "runs" / "t_2026-09-27_10-58"]
    )
    assert staged.root == staging
    rel = set(staged.files)
    assert "v0.7.0/bench.jsonl" in rel
    assert "v0.7.0/converters.jsonl" in rel
    assert "v0.7.0/docsets.json" in rel
    assert "v0.7.0/detail/r1__visual_redlines.json.gz" in rel
    assert "v0.7.0/archive/MANIFEST.md" in rel
    assert "v0.7.0/RESULTS.md" in rel
    assert "v0.7.0/RESULTS_DETAILED.md" in rel
    assert "v0.7.0/bench.registry.yaml" in rel
    assert "v0.7.0/fixtures-used.json" in rel
    assert "fixtures/corpus/word_based/pdf_redlines_word/a_redline.pdf" in rel
    assert "fixtures/corpus/word_based/pdf_source/a.pdf" in rel
    assert "outputs/v0.7.0/t_2026-09-27_10-58/score/doc1/page1.png" in rel
    assert "outputs/v0.7.0/t_2026-09-27_10-58/report.html" in rel
    assert "v0.7.0/MANIFEST.sha256.json" in rel
    assert "README.md" in rel
    # noise never leaves the machine
    assert not any(p.endswith((".lock", ".log")) for p in rel)
    # the version manifest covers every staged file but itself
    manifest = json.loads((staging / "v0.7.0" / hub.MANIFEST_NAME).read_text())["files"]
    assert set(manifest) == rel - {"v0.7.0/MANIFEST.sha256.json"}
    assert manifest["v0.7.0/bench.jsonl"] == _sha(repo / "results" / "bench.jsonl")
    # the repo-level dataset card declares the license
    assert "odc-by" in (staging / "README.md").read_text()
    # restaging starts clean
    (staging / "stale.txt").write_text("old")
    hub.stage_results(repo, staging, version="0.7.0", run_dirs=[])
    assert not (staging / "stale.txt").exists()
    assert not (staging / "outputs").exists()


def test_upload_results_uploads_the_staging_root_and_never_prunes_by_default(
    repo: Path,
) -> None:
    api = FakeHub()
    run = repo / "runs" / "t_2026-09-27_10-58"
    report = hub.upload_results(repo, api=api, version="0.7.0", with_outputs=True)
    names = [c[0] for c in api.calls]
    assert names == ["create_repo", "upload_folder", "list_repo_tree"]
    up = api.calls[1][1]
    assert up["repo_id"] == hub.RESULTS_REPO
    assert up["folder_path"] == str(repo / "results" / "hub")
    assert up["path_in_repo"] in (None, "", ".")
    assert "0.7.0" in (up["commit_message"] or "")
    assert report.verified
    assert report.mismatched == ()
    assert report.pruned == ()
    assert run.exists()
    assert (
        "outputs/v0.7.0/t_2026-09-27_10-58/report.html" in api.stored[hub.RESULTS_REPO]
    )


def test_upload_results_prunes_run_outputs_only_after_hash_verification(
    repo: Path,
) -> None:
    api = FakeHub()
    run = repo / "runs" / "t_2026-09-27_10-58"
    report = hub.upload_results(
        repo, api=api, version="0.7.0", with_outputs=True, prune_local=True
    )
    assert report.verified
    assert report.pruned == (run,)
    assert not run.exists()
    # the stores are untouched by pruning
    assert (repo / "results" / "bench.jsonl").exists()


def test_upload_results_refuses_to_prune_when_the_hub_hash_differs(repo: Path) -> None:
    api = FakeHub()
    api.corrupt.add("outputs/v0.7.0/t_2026-09-27_10-58/score/doc1/page1.png")
    run = repo / "runs" / "t_2026-09-27_10-58"
    report = hub.upload_results(
        repo, api=api, version="0.7.0", with_outputs=True, prune_local=True
    )
    assert not report.verified
    assert report.mismatched == (
        "outputs/v0.7.0/t_2026-09-27_10-58/score/doc1/page1.png",
    )
    assert report.pruned == ()
    assert run.exists()


def test_upload_results_prune_without_outputs_deletes_nothing(repo: Path) -> None:
    api = FakeHub()
    run = repo / "runs" / "t_2026-09-27_10-58"
    report = hub.upload_results(
        repo, api=api, version="0.7.0", with_outputs=False, prune_local=True
    )
    assert report.verified
    assert report.pruned == ()
    assert run.exists()
    assert not any(p.startswith("outputs/") for p in api.stored[hub.RESULTS_REPO])


def test_upload_results_small_files_verify_by_git_blob_sha1(repo: Path) -> None:
    api = FakeHub()
    report = hub.upload_results(repo, api=api, version="0.7.0")
    assert report.verified
    assert (
        repo / "results" / "hub" / "v0.7.0" / "converters.jsonl"
    ).stat().st_size == 0
    assert "v0.7.0/converters.jsonl" in report.uploaded


def test_upload_results_dry_run_stages_but_does_not_call_the_hub(repo: Path) -> None:
    api = FakeHub()
    report = hub.upload_results(
        repo,
        api=api,
        version="0.7.0",
        with_outputs=True,
        prune_local=True,
        dry_run=True,
    )
    assert api.calls == []
    assert not report.verified
    assert report.pruned == ()
    assert (repo / "results" / "hub" / "v0.7.0" / "bench.jsonl").exists()
    assert (repo / "runs" / "t_2026-09-27_10-58").exists()


def test_upload_results_default_version_is_the_installed_bench_version(
    repo: Path,
) -> None:
    from neurotic_docx_bench import version

    api = FakeHub()
    report = hub.upload_results(repo, api=api)
    assert report.version == version.bench_version()
    assert f"v{version.bench_version()}/bench.jsonl" in report.uploaded


# --- CLI -------------------------------------------------------------------


def test_cli_fixtures_download_and_results_upload(
    repo: Path, corpus: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from neurotic_docx_bench.cli import app

    api = FakeHub()
    monkeypatch.setattr(hub, "default_api", lambda: api)
    monkeypatch.chdir(repo)

    result = runner.invoke(app, ["fixtures", "upload", "--root", str(corpus)])
    assert result.exit_code == 0, result.output
    assert hub.FIXTURES_REPO in result.output

    dest = tmp_path / "dl"
    result = runner.invoke(
        app, ["fixtures", "download", "--dest", str(dest), "--revision", "main"]
    )
    assert result.exit_code == 0, result.output
    assert "verified 5" in result.output
    assert (dest / "holdout_combined.txt").exists()

    api.stored[hub.FIXTURES_REPO]["holdout_combined.txt"] = b"evil"
    result = runner.invoke(
        app, ["fixtures", "download", "--dest", str(tmp_path / "dl2")]
    )
    assert result.exit_code == 1
    assert "holdout_combined.txt" in result.output

    result = runner.invoke(
        app, ["results", "upload", "--with-outputs", "--prune-local"]
    )
    assert result.exit_code == 0, result.output
    assert hub.RESULTS_REPO in result.output
    assert "pruned 1" in result.output
    assert not (repo / "runs" / "t_2026-09-27_10-58").exists()


def test_cli_results_upload_exits_nonzero_when_verification_fails(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from neurotic_docx_bench.cli import app

    api = FakeHub()
    api.corrupt.add("v0.7.0/bench.jsonl")
    monkeypatch.setattr(hub, "default_api", lambda: api)
    monkeypatch.chdir(repo)
    result = runner.invoke(app, ["results", "upload", "--version", "0.7.0"])
    assert result.exit_code == 1
    assert "v0.7.0/bench.jsonl" in result.output


def test_default_api_is_a_real_hfapi() -> None:
    from huggingface_hub import HfApi

    assert isinstance(hub.default_api(), HfApi)
    assert not hasattr(
        HfApi, "upload_large_folder"
    )  # removed in huggingface_hub 2.0; upload_folder replaces it
