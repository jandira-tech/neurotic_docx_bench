"""The legacy_cases snapshot as a recorded input: the committed pointer file
``results/legacy_cases.ref.json``, the download the release-views flow performs
through ``hub_get``'s pinned machinery when only the pointer exists, and
``bench cases snapshot-upload`` (the content-addressed upload that writes it).

``SnapshotHub`` follows the repo's FakeHub patterns (``tests/test_hub.py``'s
recorded uploads, ``tests/test_hub_get.py``'s pinned reads): files over 64 bytes
are LFS, every read must carry a resolved commit, and an ``upload_folder`` lands
on a new commit that becomes ``main``.

bench-ops is not a venv dependency (#134): it is a PEP 723 inline dependency of
scripts/release_views.py. This module skips under a plain `uv run pytest` and
runs under the overlay that provides it.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip(
    "bench_ops",
    reason=(
        "bench-ops is a PEP 723 inline dependency of scripts/release_views.py, not a "
        "venv dependency (#134); run: uv run --with 'bench-ops @ git+https://github.com/"
        "arthrod/bench-ops@35ab2cbeb8bc44d5059878d14176dc90c5b46f5d' pytest -q "
        "tests/test_ledger_cases.py tests/test_ledger_speed.py tests/test_ledger_cases_ref.py"
    ),
)

from neurotic_docx_bench import hub
from neurotic_docx_bench.ledger import build as bd
from neurotic_docx_bench.ledger import cases_ref
from pydantic import ValidationError
from test_ledger_build import repo as _ledger_repo  # noqa: F401  the fake-repo fixture, shared with test_ledger_build
from test_ledger_cases import _write_cases_sources
from typer.testing import CliRunner

from bench_ops.models import Case, CaseShard, CasesIndex, dumps_compact

runner = CliRunner()
REPO_ROOT = Path(__file__).resolve().parents[1]
REPO = hub.RESULTS_REPO
SHA_A = "a" * 40  # the hub head a test starts from
SHA_B = "b" * 40  # the commit an upload makes
PINNED = "c" * 40  # the revision a pointer pins
NEXT = {SHA_A: SHA_B, SHA_B: PINNED}  # the commits uploads create, in order
SRC = (
    "cases_adapter.from_published of site/index.html + site/redlines/index.html "
    "at gh-pages 610bc44700000000000000000000000000000000"
)

assert cases_ref.HUB_DIR == "inputs/legacy_cases"


# ---- the snapshot bytes and the hub fake -----------------------------------------------


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _blob(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def _shard_line(kind: str, group: str, case: str) -> str:
    """One compact CaseShard line: a family the stores cannot derive."""
    shard = CaseShard(
        kind=kind,
        group=group,
        cases=[
            Case(
                kind=kind,
                group=group,
                case=case,
                pages={"reference": [f"~/x/{group}/{case}/reference/page_001.webp"]},
                page_counts={"reference": 1},
                scores={},
                times={},
                versions={"reference": "Word"},
                dropped=[],
                reference_app="Microsoft Word",
            )
        ],
    )
    return dumps_compact(shard)


# Two adapter-only families (one per kind), so a merged release provably takes
# them from the snapshot: the synthetic stores cover neither.
SNAPSHOT = (
    "\n".join(
        [
            _shard_line("conversion", "samples", "s1"),
            _shard_line("redline", "redlines/with_comments_clean", "r1"),
        ]
    )
    + "\n"
).encode("utf-8")
assert len(SNAPSHOT) > 64  # LFS on the fake hub, like the real 22.9 MB snapshot


def _entry(path: str, data: bytes) -> SimpleNamespace:
    if len(data) > 64:
        return SimpleNamespace(
            path=path,
            size=len(data),
            blob_id="f" * 40,
            lfs={"sha256": _sha(data), "size": len(data)},
        )
    return SimpleNamespace(path=path, size=len(data), blob_id=_blob(data), lfs=None)


class SnapshotHub:
    """PinnedHub's pinned reads plus FakeHub's uploads, on one dataset repo."""

    def __init__(self, files: dict[str, bytes] | None = None) -> None:
        self.trees: dict[str, dict[str, bytes]] = {SHA_A: dict(files or {})}
        self.branches = {"main": SHA_A}
        self.served: dict[str, bytes] = {}  # what a download returns instead of the stored bytes
        self.calls: list[tuple[str, dict]] = []
        self.drop_upload = False  # a hub that loses the upload before the listing

    def create_repo(self, repo_id: str, *, repo_type: str, exist_ok: bool = False) -> str:
        self.calls.append(("create_repo", {"repo_id": repo_id, "exist_ok": exist_ok}))
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
        parent_commit: str | None = None,
    ) -> str:
        self.calls.append(
            (
                "upload_folder",
                {
                    "repo_id": repo_id,
                    "path_in_repo": path_in_repo,
                    "commit_message": commit_message,
                    "parent_commit": parent_commit,
                },
            )
        )
        head = self.branches["main"]
        assert parent_commit in (None, head), f"upload would overwrite a moved head {parent_commit}"
        staged: dict[str, bytes] = {}
        root = Path(folder_path)
        prefix = (path_in_repo or "").strip("/")
        for p in sorted(root.rglob("*")):
            if p.is_file():
                rel = p.relative_to(root).as_posix()
                staged[f"{prefix}/{rel}" if prefix else rel] = p.read_bytes()
        self.trees[NEXT[head]] = {**self.trees[head], **({} if self.drop_upload else staged)}
        self.branches["main"] = NEXT[head]
        return "https://huggingface.co/fake"

    def repo_info(self, repo_id: str, *, repo_type: str, revision: str | None = None):
        self.calls.append(("repo_info", {"repo_id": repo_id, "revision": revision}))
        rev = revision or "main"
        sha = self.branches.get(rev, rev if rev in self.trees else None)
        if sha is None:
            raise LookupError(f"no revision {rev}")
        return SimpleNamespace(sha=sha)

    def list_repo_tree(
        self, repo_id, *, repo_type, path_in_repo=None, recursive=True, expand=True, revision=None
    ):
        self.calls.append(
            ("list_repo_tree", {"path_in_repo": path_in_repo, "expand": expand, "revision": revision})
        )
        assert revision in self.trees, f"unpinned read: revision={revision!r}"
        prefix = (path_in_repo or "").strip("/")
        folders = set()
        for rel, data in sorted(self.trees[revision].items()):
            if prefix and not rel.startswith(prefix + "/"):
                continue
            parts = rel.split("/")
            for i in range(1, len(parts)):
                folders.add("/".join(parts[:i]))
            yield _entry(rel, data)
        for f in sorted(folders):
            if not prefix or f.startswith(prefix + "/"):
                yield SimpleNamespace(path=f, tree_id="e" * 40)

    def hf_hub_download(self, repo_id, filename, *, repo_type, revision=None, local_dir=None):
        self.calls.append(("hf_hub_download", {"filename": filename, "revision": revision}))
        data = self.served.get(filename, self.trees[revision][filename])
        out = Path(local_dir) / filename
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
        return str(out)

    def uploads(self) -> list[dict]:
        return [c for name, c in self.calls if name == "upload_folder"]

    def read_revisions(self) -> set[str]:
        """The revisions every tree read and download carried (repo_info aside)."""
        return {
            c["revision"]
            for name, c in self.calls
            if name in ("list_repo_tree", "hf_hub_download")
        }


def _hub_path(data: bytes) -> str:
    return f"{cases_ref.HUB_DIR}/{_sha(data)}.jsonl"


def _write_pointer(
    root: Path,
    *,
    data: bytes = SNAPSHOT,
    revision: str = PINNED,
    repo: str = REPO,
    sha256: str | None = None,
    bytes_: int | None = None,
    path: str | None = None,
    source: str = SRC,
) -> Path:
    digest = sha256 or _sha(data)
    payload = {
        "repo": repo,
        "path": path or _hub_path(data),
        "revision": revision,
        "sha256": digest,
        "bytes": len(data) if bytes_ is None else bytes_,
        "source": source,
    }
    p = Path(root) / "results" / "legacy_cases.ref.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return p


def _write_local_snapshot(root: Path, data: bytes = SNAPSHOT) -> Path:
    p = Path(root) / "results" / "release" / "legacy_cases.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    return p


# ---- the pointer model -----------------------------------------------------------------


def test_ref_model_is_strict_and_content_addressed() -> None:
    ref = cases_ref.LegacyCasesRef(
        repo=REPO,
        path=_hub_path(SNAPSHOT),
        revision=PINNED,
        sha256=_sha(SNAPSHOT),
        bytes=len(SNAPSHOT),
        source=SRC,
    )
    assert ref.bytes == len(SNAPSHOT)
    with pytest.raises(ValidationError):
        ref.bytes = 0  # frozen: a pointer is never edited in place
    bad = [
        {"repo": REPO, "path": _hub_path(SNAPSHOT), "revision": "short", "sha256": _sha(SNAPSHOT), "bytes": 1, "source": SRC},
        {"repo": REPO, "path": _hub_path(SNAPSHOT), "revision": PINNED, "sha256": "XYZ", "bytes": 1, "source": SRC},
        {"repo": REPO, "path": _hub_path(SNAPSHOT), "revision": PINNED, "sha256": _sha(SNAPSHOT), "bytes": 0, "source": SRC},
        {"repo": REPO, "path": f"inputs/legacy_cases/{_sha(SNAPSHOT)}.jsonl", "revision": PINNED, "sha256": "0" * 64, "bytes": 1, "source": SRC},  # path not addressed to the hash
        {"repo": REPO, "path": _hub_path(SNAPSHOT), "revision": PINNED, "sha256": _sha(SNAPSHOT), "bytes": 1, "source": SRC, "extra": True},
    ]
    for payload in bad:
        with pytest.raises(ValidationError):
            cases_ref.LegacyCasesRef.model_validate(payload)


# ---- ensure_legacy: the download the release-views flow performs ----------------------


def test_ensure_legacy_downloads_at_the_pinned_revision(tmp_path: Path) -> None:
    """The pointer's revision is the only commit anything reads: main may hold
    different bytes under the same path, the pinned commit holds the snapshot."""
    path = _hub_path(SNAPSHOT)
    api = SnapshotHub({path: b"Z" * 100})  # main's copy is not the snapshot
    api.trees[PINNED] = {path: SNAPSHOT}
    _write_pointer(tmp_path)

    got = cases_ref.ensure_legacy(tmp_path, api=api)

    assert got == tmp_path / "results" / "release" / "legacy_cases.jsonl"
    assert got.read_bytes() == SNAPSHOT
    assert api.read_revisions() == {PINNED}  # pinned: never main, never a branch
    assert not list((tmp_path / "results").glob(".release.hub-*")), "staging cleaned"


def test_ensure_legacy_prefers_the_local_file(tmp_path: Path) -> None:
    local = _write_local_snapshot(tmp_path, b"local bytes, not the hub's\n" * 8)
    api = SnapshotHub({_hub_path(b"other" * 32): b"other" * 32})

    assert cases_ref.ensure_legacy(tmp_path, api=api) == local
    assert api.calls == []


def test_ensure_legacy_accepts_the_committed_location(tmp_path: Path) -> None:
    """Under 2 MB the snapshot is committable at results/legacy_cases.jsonl."""
    p = tmp_path / "results" / "legacy_cases.jsonl"
    p.parent.mkdir(parents=True)
    p.write_bytes(SNAPSHOT)
    _write_pointer(tmp_path)

    assert cases_ref.ensure_legacy(tmp_path, api=SnapshotHub()) == p


def test_ensure_legacy_returns_none_without_file_or_pointer(tmp_path: Path) -> None:
    api = SnapshotHub()
    assert cases_ref.ensure_legacy(tmp_path, api=api) is None
    assert api.calls == []


def test_ensure_legacy_refuses_when_the_hub_copy_differs_from_the_pointer(tmp_path: Path) -> None:
    other = b"different bytes entirely\n" * 8
    api = SnapshotHub({_hub_path(SNAPSHOT): other})
    api.trees[PINNED] = {_hub_path(SNAPSHOT): other}
    _write_pointer(tmp_path)

    with pytest.raises(cases_ref.CasesRefError) as exc:
        cases_ref.ensure_legacy(tmp_path, api=api)
    assert _sha(other) in str(exc.value) and _sha(SNAPSHOT) in str(exc.value)
    assert "\n" not in str(exc.value)  # one line: the console print stays one line
    assert not (tmp_path / "results" / "release" / "legacy_cases.jsonl").exists()


def test_ensure_legacy_refuses_when_the_path_is_absent(tmp_path: Path) -> None:
    api = SnapshotHub()  # the pinned commit holds nothing under inputs/
    api.trees[PINNED] = {}
    _write_pointer(tmp_path)

    with pytest.raises(cases_ref.CasesRefError, match=_hub_path(SNAPSHOT)):
        cases_ref.ensure_legacy(tmp_path, api=api)
    assert not (tmp_path / "results" / "release" / "legacy_cases.jsonl").exists()


def test_ensure_legacy_refuses_a_corrupt_download(tmp_path: Path) -> None:
    """The listing promises the pinned hash, the transfer serves other bytes:
    hub_get refuses the download; the wrapper turns it into the one-line error."""
    path = _hub_path(SNAPSHOT)
    api = SnapshotHub({path: SNAPSHOT})
    api.trees[PINNED] = {path: SNAPSHOT}
    api.served[path] = b"C" * 100
    _write_pointer(tmp_path)

    with pytest.raises(cases_ref.CasesRefError) as exc:
        cases_ref.ensure_legacy(tmp_path, api=api)
    assert "\n" not in str(exc.value)
    assert not (tmp_path / "results" / "release" / "legacy_cases.jsonl").exists()


def test_ensure_legacy_refuses_an_unreadable_pointer(tmp_path: Path) -> None:
    p = tmp_path / "results" / "legacy_cases.ref.json"
    p.parent.mkdir(parents=True)
    p.write_text('{"repo": 3}\n', encoding="utf-8")

    with pytest.raises(cases_ref.CasesRefError, match="legacy_cases.ref.json"):
        cases_ref.ensure_legacy(tmp_path, api=SnapshotHub())


# ---- the release-views flow: the pointer feeds the release -----------------------------


def test_release_views_download_the_legacy_input_through_the_pointer(
    _ledger_repo: Path, monkeypatch  # noqa: F811  fixture parameter
) -> None:
    _write_cases_sources(_ledger_repo)
    path = _hub_path(SNAPSHOT)
    api = SnapshotHub()
    api.trees[PINNED] = {path: SNAPSHOT}
    _write_pointer(_ledger_repo)
    monkeypatch.setattr(hub, "default_api", lambda: api)

    said: list[str] = []
    assert bd.run_release_views(_ledger_repo, echo=said.append) == 0
    downloaded = _ledger_repo / "results" / "release" / "legacy_cases.jsonl"
    assert downloaded.read_bytes() == SNAPSHOT
    index = CasesIndex.model_validate_json(
        (_ledger_repo / "results" / "release" / "cases" / "index.json").read_text(encoding="utf-8")
    )
    groups = {(g.kind, g.group) for g in index.groups}
    assert ("conversion", "samples") in groups and ("redline", "redlines/with_comments_clean") in groups
    assert {("conversion", "v1/clean"), ("redline", "ar/accept_all")} <= groups  # the stores' families
    ok: list[str] = []
    assert bd.run_release_views(_ledger_repo, check=True, echo=ok.append) == 0


def test_release_views_exit_1_when_the_pointer_cannot_be_satisfied(
    _ledger_repo: Path, monkeypatch  # noqa: F811  fixture parameter
) -> None:
    api = SnapshotHub()  # the hub holds nothing at the pinned revision
    _write_pointer(_ledger_repo)
    monkeypatch.setattr(hub, "default_api", lambda: api)

    said: list[str] = []
    assert bd.run_release_views(_ledger_repo, echo=said.append) == 1
    assert "legacy_cases" in " ".join(said)
    assert not (_ledger_repo / "results" / "release" / "cases" / "index.json").exists()


def test_release_views_exit_1_without_case_sources_unless_allowed(
    _ledger_repo: Path,  # noqa: F811  fixture parameter
) -> None:
    """Neither the snapshot nor a pointer, and the stores emit no complete
    family: the release would carry zero cases — an error unless asked for."""
    said: list[str] = []
    assert bd.run_release_views(_ledger_repo, echo=said.append) == 1
    assert "--allow-no-cases" in " ".join(said)
    assert not (_ledger_repo / "results" / "release" / "cases" / "index.json").exists()
    allowed: list[str] = []
    assert bd.run_release_views(_ledger_repo, allow_no_cases=True, echo=allowed.append) == 0
    assert (_ledger_repo / "RESULTS.md").is_file()


def test_release_views_without_stores_but_with_the_snapshot_still_emit_cases(
    _ledger_repo: Path, monkeypatch  # noqa: F811  fixture parameter
) -> None:
    """A fresh clone: no store asset trees at all — the downloaded snapshot is
    the whole cases release, which is why the pointer must never be skipped."""
    path = _hub_path(SNAPSHOT)
    api = SnapshotHub()
    api.trees[PINNED] = {path: SNAPSHOT}
    _write_pointer(_ledger_repo)
    monkeypatch.setattr(hub, "default_api", lambda: api)

    said: list[str] = []
    assert bd.run_release_views(_ledger_repo, echo=said.append) == 0
    index = CasesIndex.model_validate_json(
        (_ledger_repo / "results" / "release" / "cases" / "index.json").read_text(encoding="utf-8")
    )
    assert {(g.kind, g.group) for g in index.groups} == {
        ("conversion", "samples"),
        ("redline", "redlines/with_comments_clean"),
    }


# ---- snapshot-upload: the content-addressed upload that writes the pointer --------------


def test_snapshot_upload_uploads_verifies_and_writes_the_pointer(tmp_path: Path) -> None:
    _write_local_snapshot(tmp_path)
    api = SnapshotHub()

    ref, uploaded = cases_ref.snapshot_upload(tmp_path, api=api, source=SRC)

    assert uploaded is True
    [up] = api.uploads()
    assert up["path_in_repo"] == cases_ref.HUB_DIR
    assert up["parent_commit"] == SHA_A  # content-addressed: never over a moved head
    assert api.branches["main"] == SHA_B
    assert api.trees[SHA_B][_hub_path(SNAPSHOT)] == SNAPSHOT
    assert ref.path == _hub_path(SNAPSHOT)
    assert ref.revision == SHA_B  # the commit the plain listing verified the copy at
    assert ref.sha256 == _sha(SNAPSHOT) and ref.bytes == len(SNAPSHOT)
    pointer = tmp_path / "results" / "legacy_cases.ref.json"
    assert pointer.is_file()
    again = cases_ref.load_ref(tmp_path)
    assert again == ref  # what landed on disk is what was returned
    assert json.loads(pointer.read_text(encoding="utf-8")) == ref.model_dump(mode="json")


def test_snapshot_upload_is_idempotent_and_never_overwrites(tmp_path: Path) -> None:
    """The same bytes are already on the hub: no second upload, the pointer just
    re-pins the head. Different bytes under the same content-addressed path are
    refused — the path is the content, it is never overwritten."""
    _write_local_snapshot(tmp_path)
    api = SnapshotHub()
    cases_ref.snapshot_upload(tmp_path, api=api, source=SRC)

    ref, uploaded = cases_ref.snapshot_upload(tmp_path, api=api, source=SRC)

    assert uploaded is False and len(api.uploads()) == 1
    assert ref.revision == SHA_B  # already there at the head: re-pinned, not re-uploaded

    clash = SnapshotHub({_hub_path(SNAPSHOT): b"someone else's snapshot\n" * 8})
    with pytest.raises(cases_ref.CasesRefError) as exc:
        cases_ref.snapshot_upload(tmp_path, api=clash, source=SRC)
    assert "never overwritten" in str(exc.value)
    assert clash.uploads() == []  # nothing uploaded onto the clash
    assert cases_ref.load_ref(tmp_path) == ref  # the pointer from the good run stands


def test_snapshot_upload_requires_the_local_input(tmp_path: Path) -> None:
    api = SnapshotHub()
    with pytest.raises(cases_ref.CasesRefError, match="write_legacy"):
        cases_ref.snapshot_upload(tmp_path, api=api, source=SRC)
    assert api.calls == []


def test_snapshot_upload_needs_a_source_before_uploading(tmp_path: Path, monkeypatch) -> None:
    """No gh-pages site to name and no --source: refused before anything is
    uploaded (the pointer would otherwise be written from an unnamed run)."""
    monkeypatch.delenv("NDB_SITE_DIR", raising=False)
    _write_local_snapshot(tmp_path)
    api = SnapshotHub()
    with pytest.raises(cases_ref.CasesRefError, match="--source"):
        cases_ref.snapshot_upload(tmp_path, api=api, source=None)
    assert api.calls == []


def test_snapshot_upload_refuses_an_unverifiable_upload(tmp_path: Path) -> None:
    """The upload ran but the plain listing does not show the bytes: no pointer."""
    _write_local_snapshot(tmp_path)
    api = SnapshotHub()
    api.drop_upload = True

    with pytest.raises(cases_ref.CasesRefError, match="legacy_cases"):
        cases_ref.snapshot_upload(tmp_path, api=api, source=SRC)
    assert api.uploads()  # the upload was attempted
    assert not (tmp_path / "results" / "legacy_cases.ref.json").exists()


def test_cli_snapshot_upload_writes_the_pointer(
    _ledger_repo: Path, monkeypatch  # noqa: F811  fixture parameter
) -> None:
    from neurotic_docx_bench.cli import app

    _write_local_snapshot(_ledger_repo)
    api = SnapshotHub()
    monkeypatch.setattr(hub, "default_api", lambda: api)

    result = CliRunner().invoke(
        app, ["cases", "snapshot-upload", "--root", str(_ledger_repo), "--source", SRC]
    )
    assert result.exit_code == 0, result.output
    ref = cases_ref.load_ref(_ledger_repo)
    assert ref is not None and ref.source == SRC and ref.revision == SHA_B


def test_cli_snapshot_upload_exits_1_without_the_input(
    _ledger_repo: Path, monkeypatch  # noqa: F811  fixture parameter
) -> None:
    from neurotic_docx_bench.cli import app

    monkeypatch.setattr(hub, "default_api", lambda: SnapshotHub())
    result = CliRunner().invoke(app, ["cases", "snapshot-upload", "--root", str(_ledger_repo)])
    assert result.exit_code == 1
    assert "write_legacy" in result.output
    assert not (_ledger_repo / "results" / "legacy_cases.ref.json").exists()


# ---- git: the pointer is committed, the snapshot and staging are not --------------------


def test_pointer_is_committed_and_the_snapshot_is_not() -> None:
    for rel, ignored in (
        ("results/legacy_cases.ref.json", False),
        ("results/release/legacy_cases.jsonl", True),
        ("results/.release.hub-aaaaaaaaaaaa/files/inputs/legacy_cases/x.jsonl", True),
    ):
        r = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "check-ignore", "-q", rel],
            capture_output=True,
            check=False,
            timeout=30,
        )
        assert r.returncode == (0 if ignored else 1), f"{rel} ignored={ignored}"


class EntryNotFoundError(Exception):
    """Named like huggingface_hub's: the real hub 404s a tree listing of a missing folder."""


class RemoteEntryNotFoundError(EntryNotFoundError):
    """What huggingface_hub 1.x actually raises (a subclass), seen on the real hub 2026-11-02."""


def test_first_snapshot_upload_when_the_hub_folder_does_not_exist_yet(tmp_path: Path) -> None:
    """The real hub answers 404 (EntryNotFoundError) for a listing of a folder that does
    not exist; the pre-upload check must read that as "nothing there yet" (measured
    2026-11-02: the first real upload failed on it). The post-upload verification still
    refuses a missing folder."""
    _write_local_snapshot(tmp_path)

    class Hub404(SnapshotHub):
        def list_repo_tree(self, repo_id, *, repo_type, path_in_repo=None, recursive=True, expand=True, revision=None):
            prefix = (path_in_repo or "").strip("/")
            if prefix and not any(r.startswith(prefix + "/") for r in self.trees[revision]):
                raise RemoteEntryNotFoundError(f"{prefix} does not exist on {revision}")
            yield from super().list_repo_tree(
                repo_id, repo_type=repo_type, path_in_repo=path_in_repo,
                recursive=recursive, expand=expand, revision=revision,
            )

    api = Hub404()
    ref, uploaded = cases_ref.snapshot_upload(tmp_path, api=api, source=SRC)
    assert uploaded is True and ref.revision == SHA_B

    lost = Hub404()
    lost.drop_upload = True
    with pytest.raises(cases_ref.CasesRefError):
        cases_ref.snapshot_upload(tmp_path, api=lost, source=SRC)
