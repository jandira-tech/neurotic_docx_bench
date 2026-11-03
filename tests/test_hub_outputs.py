"""The results dataset's ``outputs/`` tree: one staging and upload path (plan 7, #143).

The release's own jubarte lane is published under the layout the vendor lanes
use, and the commit it landed on is recorded in the release evidence, so the
release shards' file links resolve against a pinned revision (never a moving
branch).

Every hub call goes through an injected fake: nothing here touches the network.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from neurotic_docx_bench import hub, hub_outputs

CONVERT_A = "clean__alpha"
CONVERT_B = "clean__beta"
REDLINE_A = "alpha__vs__beta_redline_aaaaaaaa"
LANE = "jubarte-1.2.3"


class FakeOutputsHub:
    """The results dataset: it stores what was uploaded and serves the tree back."""

    def __init__(self) -> None:
        self.stored: dict[str, bytes] = {}
        self.head = "a" * 40
        self.commits: list[tuple[str, str]] = [(self.head, "initial commit")]
        self.uploads: list[dict[str, object]] = []

    # -- the api slice hub.py uses ------------------------------------------

    def repo_info(self, repo_id: str, *, repo_type: str, revision: str | None = None):
        return SimpleNamespace(sha=self.head)

    def list_repo_commits(self, repo_id: str, *, repo_type: str, revision: str | None = None):
        ids = [sha for sha, _ in self.commits]
        end = ids.index(revision) + 1 if revision in ids else len(ids)
        return [
            SimpleNamespace(commit_id=sha, title=title)
            for sha, title in reversed(self.commits[:end])
        ]

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
    ):
        self.uploads.append(
            {
                "path_in_repo": path_in_repo,
                "commit_message": commit_message,
                "parent_commit": parent_commit,
            }
        )
        prefix = (path_in_repo or "").strip("/")
        root = Path(folder_path)
        files = {
            f"{prefix}/{p.relative_to(root).as_posix()}": p.read_bytes()
            for p in root.rglob("*")
            if p.is_file()
        }
        if files and all(self.stored.get(key) == data for key, data in files.items()):
            # huggingface_hub makes no commit when nothing changed: it returns the head.
            return SimpleNamespace(oid=self.head)
        if parent_commit is not None and parent_commit != self.head:
            raise RuntimeError("412 parent commit is not the head of main")
        self.stored.update(files)
        self.head = f"{len(self.commits):040x}"
        self.commits.append((self.head, commit_message or ""))
        return SimpleNamespace(oid=self.head)

    def list_repo_tree(
        self,
        repo_id: str,
        *,
        repo_type: str,
        path_in_repo: str | None = None,
        recursive: bool = True,
        expand: bool = True,
        revision: str | None = None,
    ):
        prefix = (path_in_repo or "").strip("/")
        for rel, data in sorted(self.stored.items()):
            if prefix and not rel.startswith(prefix + "/"):
                continue
            yield SimpleNamespace(
                path=rel,
                lfs={"sha256": hashlib.sha256(data).hexdigest(), "size": len(data)},
                blob_id=None,
                size=len(data),
            )


@pytest.fixture
def release_root(tmp_path: Path) -> Path:
    """A bench root holding one release's own jubarte outputs."""
    root = tmp_path / "repo"
    ev = root / "results" / "release_1.2.3_evidence"
    candidate = ev / "convert_work" / "jubarte" / "candidate"
    candidate.mkdir(parents=True)
    (candidate / f"{CONVERT_A}.pdf").write_bytes(b"%PDF-1 alpha")
    (candidate / f"{CONVERT_B}.pdf").write_bytes(b"%PDF-1 beta")
    (ev / "docx_to_pdf_jubarte_1.2.3_sample.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-11-03T00:00:00+00:00",
                "n": 2,
                "oracle": "microsoft_word",
                "stems": [CONVERT_A, CONVERT_B],
                "tools": {
                    "jubarte": {
                        "tool": "jubarte",
                        "version": "jubarte 1.2.3",
                        "n_scored": 2,
                        "per_doc": {CONVERT_A: 80.0, CONVERT_B: 70.0},
                        "generate_failures": [],
                        "failures": 0,
                    }
                },
                "track": "corpus/word:list",
                "warnings": [],
            },
            indent=2,
        )
        + "\n"
    )
    lane = root / "results" / "redlines_0929_full" / LANE
    (lane / "docx").mkdir(parents=True)
    (lane / "pdf_by_word").mkdir(parents=True)
    (lane / "docx" / f"{REDLINE_A}_{LANE}.docx").write_bytes(b"redline")
    (lane / "pdf_by_word" / f"{REDLINE_A}_{LANE}_byword.pdf").write_bytes(b"%PDF-1 redline")
    (lane / "generate_failures.json").write_text("[]\n")
    return root


def test_the_conversion_lane_is_staged_with_its_pdfs_the_report_and_a_manifest(
    release_root: Path, tmp_path: Path
) -> None:
    ev = release_root / "results" / "release_1.2.3_evidence"
    staging = tmp_path / "staging"
    staged = hub_outputs.stage_convert_lane(
        staging,
        pdf_dir=ev / "convert_work" / "jubarte" / "candidate",
        report=ev / "docx_to_pdf_jubarte_1.2.3_sample.json",
    )
    assert sorted(staged) == sorted(
        [
            "MANIFEST.sha256.json",
            "docx_to_pdf_jubarte_1.2.3_sample.json",
            f"pdf/{CONVERT_A}.pdf",
            f"pdf/{CONVERT_B}.pdf",
        ]
    )
    manifest = hub.read_manifest(staging / hub.MANIFEST_NAME)
    assert manifest[f"pdf/{CONVERT_A}.pdf"] == hashlib.sha256(
        (staging / "pdf" / f"{CONVERT_A}.pdf").read_bytes()
    ).hexdigest()
    assert hub.MANIFEST_NAME not in manifest
    assert hub_outputs.convert_case_files(staging) == {
        f"pdf/{CONVERT_A}.pdf",
        f"pdf/{CONVERT_B}.pdf",
    }


def test_a_lane_that_wrote_more_pdfs_than_the_report_scored_is_refused(
    release_root: Path, tmp_path: Path
) -> None:
    ev = release_root / "results" / "release_1.2.3_evidence"
    candidate = ev / "convert_work" / "jubarte" / "candidate"
    (candidate / "clean__gamma.pdf").write_bytes(b"%PDF-1 gamma")
    with pytest.raises(hub_outputs.LaneError, match="PDFs, the report scored"):
        hub_outputs.stage_convert_lane(
            tmp_path / "staging",
            pdf_dir=candidate,
            report=ev / "docx_to_pdf_jubarte_1.2.3_sample.json",
        )


def test_the_redline_lane_is_staged_as_docx_pdf_by_word_and_meta(
    release_root: Path, tmp_path: Path
) -> None:
    staging = tmp_path / "staging"
    staged = hub_outputs.stage_redline_lane(
        staging,
        lane=LANE,
        lane_dir=release_root / "results" / "redlines_0929_full" / LANE,
    )
    assert sorted(staged) == sorted(
        [
            f"{LANE}/docx/{REDLINE_A}_{LANE}.docx",
            f"{LANE}/pdf_by_word/{REDLINE_A}_{LANE}_byword.pdf",
            f"{LANE}/meta/generate_failures.json",
        ]
    )
    assert hub_outputs.redline_case_files(staging) == {
        f"{LANE}/pdf_by_word/{REDLINE_A}_{LANE}_byword.pdf"
    }


def test_publish_release_uploads_both_lanes_and_records_the_revision(
    release_root: Path, tmp_path: Path
) -> None:
    api = FakeOutputsHub()
    evidence = hub_outputs.publish_release(
        release_root, "1.2.3", api=api, staging=tmp_path / "staging"
    )

    assert evidence["verified"] is True
    assert evidence["revision"] == api.head
    assert evidence["paths"] == [
        "outputs/convert_860/jubarte_1.2.3",
        f"outputs/redlines_0929_full/{LANE}/docx",
        f"outputs/redlines_0929_full/{LANE}/pdf_by_word",
        f"outputs/redlines_0929_full/{LANE}/meta",
    ]
    assert f"outputs/convert_860/jubarte_1.2.3/pdf/{CONVERT_A}.pdf" in api.stored
    assert (
        "outputs/convert_860/jubarte_1.2.3/docx_to_pdf_jubarte_1.2.3_sample.json"
        in api.stored
    )
    assert f"outputs/redlines_0929_full/{LANE}/pdf_by_word/{REDLINE_A}_{LANE}_byword.pdf" in api.stored
    assert f"outputs/redlines_0929_full/{LANE}/meta/generate_failures.json" in api.stored

    # The evidence is the record the release shards' links resolve against.
    written = json.loads(
        (release_root / "results" / "release_1.2.3_evidence" / "release_info" / "hub_outputs.json").read_text()
    )
    assert written["revision"] == api.head
    assert written["verified"] is True
    assert written["paths"] == evidence["paths"]


def test_publish_release_refuses_when_the_hub_does_not_hold_a_file(
    release_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    api = FakeOutputsHub()
    monkeypatch.setattr(hub, "verify_uploaded", lambda *a, **k: ("pdf/clean__alpha.pdf",))
    with pytest.raises(hub_outputs.LaneError, match="missing or different on the hub"):
        hub_outputs.publish_release(
            release_root, "1.2.3", api=api, staging=tmp_path / "staging"
        )
    assert not hub_outputs.evidence_path(release_root, "1.2.3").is_file()


def test_a_render_the_release_own_set_does_not_name_is_refused(
    release_root: Path, tmp_path: Path
) -> None:
    """A stale render would be published and linked by nobody."""
    ev = release_root / "results" / "release_1.2.3_evidence"
    (ev / "sample_conversion_1.2.3.csv").write_text(
        "state,stem,docx,docx_sha256,word_pdf,word_pdf_sha256\n"
        f"clean,{CONVERT_A},corpus/word/clean/docx/{CONVERT_A}.docx,0,corpus/word/clean/pdf/{CONVERT_A}.pdf,1\n"
    )
    candidate = ev / "convert_work" / "jubarte" / "candidate"
    (candidate / "clean__gamma.pdf").write_bytes(b"%PDF-1 gamma")
    # the report scored the stray render too: it is the set that does not name it
    report = ev / "docx_to_pdf_jubarte_1.2.3_sample.json"
    data = json.loads(report.read_text())
    data["tools"]["jubarte"]["n_scored"] = 3
    report.write_text(json.dumps(data))
    api = FakeOutputsHub()
    with pytest.raises(hub_outputs.LaneError, match="not in the release's own set"):
        hub_outputs.publish_release(
            release_root, "1.2.3", api=api, staging=tmp_path / "staging"
        )


def test_the_files_base_is_the_pinned_revision_and_never_a_branch(
    release_root: Path, tmp_path: Path
) -> None:
    api = FakeOutputsHub()
    hub_outputs.publish_release(release_root, "1.2.3", api=api, staging=tmp_path / "staging")
    base = hub_outputs.files_base(release_root, "1.2.3")
    assert base == (
        "https://huggingface.co/datasets/arthrod/neurotic_docx_bench/resolve/"
        f"{api.head}/"
    )
    assert "/main/" not in base


def test_without_a_pinned_revision_the_files_base_is_a_clear_error(
    release_root: Path,
) -> None:
    with pytest.raises(hub_outputs.PinnedRevisionMissing) as excinfo:
        hub_outputs.files_base(release_root, "1.2.3")
    message = str(excinfo.value)
    assert "1.2.3" in message
    assert "hub_outputs.json" in message
    assert "main" not in message
