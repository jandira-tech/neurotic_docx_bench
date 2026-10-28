"""The v1 fixture set: every hub file whose oracle Microsoft Word made, for every test (#84).

The wheel ships the set's manifest and the hub commit it is pinned to, never the
documents; ``fixture_sets.get`` fetches exactly the manifest's files at that commit
and checks each one against the manifest's sha256.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import pytest
from typer.testing import CliRunner

from neurotic_docx_bench import fixture_sets as fs
from neurotic_docx_bench import hub, hub_get

from tests.test_hub_get import PinnedHub, blob_id

ROOT = Path(__file__).resolve().parents[1]
WORD = ROOT / "corpus" / "word"


@pytest.fixture(scope="module")
def v1() -> fs.FixtureSet:
    return fs.load("v1")


@pytest.fixture(scope="module")
def rows(v1: fs.FixtureSet) -> list[fs.Row]:
    return fs.rows("v1")


def test_v1_is_pinned_to_one_commit_of_the_fixtures_dataset(v1: fs.FixtureSet) -> None:
    assert v1.name == "v1"
    assert v1.repo_id == hub.FIXTURES_REPO
    assert re.fullmatch(r"[0-9a-f]{40}", v1.revision)
    assert v1.path == hub.WORD_CORPUS
    assert v1.tests == fs.TESTS == ("docx_to_pdf", "redline", "accept_all", "reject_all")


def test_v1_holds_every_word_measured_case_of_every_test(rows: list[fs.Row], v1: fs.FixtureSet) -> None:
    cases = Counter(test for test, _ in {(r.test, r.case) for r in rows if r.test != fs.SUPPORT})
    assert cases == {"docx_to_pdf": 2925, "redline": 3502, "accept_all": 400, "reject_all": 400}
    assert v1.cases == dict(cases)
    roles = {t: Counter(r.role for r in rows if r.test == t) for t in fs.TESTS}
    assert roles["docx_to_pdf"] == {"input_docx": 2925, "word_pdf": 2925}
    assert roles["redline"] == {"base_docx": 3502, "next_docx": 3502, "word_docx": 3502, "word_pdf": 3502}
    assert roles["accept_all"] == roles["reject_all"] == {"input_docx": 400, "word_docx": 400, "word_pdf": 400}


def test_every_row_matches_the_corpus_manifest_and_names_no_other_producer(rows: list[fs.Row]) -> None:
    manifest = json.loads((WORD / "MANIFEST.sha256.json").read_text())["files"]
    assert all(manifest[r.path] == r.sha256 for r in rows if r.test != fs.SUPPORT)
    assert not [r.path for r in rows if "pdf_prior" in r.path or r.path.startswith("libreoffice")]
    with (WORD / "comparisons.csv").open() as fh:
        compares = {row["id"]: row for row in csv.DictReader(fh)}
    redlines = {r.case for r in rows if r.test == "redline"}
    assert all(compares[c]["pdf"] and compares[c]["producer"] for c in redlines)
    assert {c for c, row in compares.items() if not row["pdf"]}.isdisjoint(redlines)


def test_the_shipped_manifest_is_what_the_tables_build(rows: list[fs.Row]) -> None:
    listing = {r.path: (r.size, r.blob_id, None if r.blob_id else r.sha256) for r in rows}
    assert fs.build(WORD, listing) == rows


def test_the_set_ships_the_corpus_tables_and_every_test_gets_them(rows: list[fs.Row]) -> None:
    support = {r.path for r in rows if r.test == fs.SUPPORT}
    assert {"documents.csv", "comparisons.csv", "MANIFEST.sha256.json", "pools/accept_all.csv"} <= support
    assert not [p for p in support if p.endswith((".docx", ".pdf"))]
    assert support <= set(fs.files("v1", tests=("accept_all",)))
    assert all(r.sha256 == hashlib.sha256((WORD / r.path).read_bytes()).hexdigest() for r in rows
               if r.test == fs.SUPPORT)


def test_a_local_table_that_is_not_the_hubs_is_refused(tmp_path: Path) -> None:
    (tmp_path / "pools").mkdir()
    for name in ("documents.csv", "comparisons.csv"):
        (tmp_path / name).write_text((WORD / name).read_text().splitlines()[0] + "\n")
    for name in ("accept_all.csv", "reject_all.csv"):
        (tmp_path / "pools" / name).write_text((WORD / "pools" / name).read_text().splitlines()[0] + "\n")
    (tmp_path / "MANIFEST.sha256.json").write_text('{"files": {}}')
    (tmp_path / "README.md").write_text("local edit\n")
    with pytest.raises(fs.FixtureSetError, match="README.md"):
        fs.build(tmp_path, {"README.md": (len(b"hub copy\n"), blob_id(b"hub copy\n"), None)})


def test_the_manifest_is_package_data_not_a_checkout_path() -> None:
    assert fs.manifest_resource("v1").name == "v1.csv.gz"
    assert "corpus" not in str(fs.manifest_resource("v1"))


# --- download ---------------------------------------------------------------


def _small_set(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, files: dict[str, bytes]) -> fs.FixtureSet:
    """A two-case set over ``files`` (paths under word/), pinned to PinnedHub's commit."""
    rows = []
    for i, (rel, data) in enumerate(sorted(files.items())):
        rows.append(fs.Row(test="docx_to_pdf", case=f"c{i // 2}", state="clean",
                           role="input_docx" if rel.endswith(".docx") else "word_pdf", path=rel,
                           sha256=hashlib.sha256(data).hexdigest(), size=len(data), blob_id=blob_id(data)))
    meta = fs.FixtureSet(name="t1", repo_id=hub.FIXTURES_REPO, revision="a" * 40, path="word",
                         tests=fs.TESTS, cases={"docx_to_pdf": 1})
    monkeypatch.setattr(fs, "load", lambda name="v1": meta)
    monkeypatch.setattr(fs, "rows", lambda name="v1", tests=(): [r for r in rows if not tests or r.test in tests])
    return meta


FILES = {"clean/docx/a.docx": b"PK" + b"a" * 100, "clean/pdf/a.pdf": b"%PDF" + b"a" * 100}


def test_get_fetches_exactly_the_set_at_its_pinned_commit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _small_set(tmp_path, monkeypatch, FILES)
    # main has moved on; the set reads its own commit, and nothing beyond its files
    api = PinnedHub({f"word/{k}": v for k, v in FILES.items()} | {"word/clean/docx/extra.docx": b"PK-no",
                                                                    "word/documents.csv": b"id\n"},
                    commits={"main": "c" * 40})
    report = fs.get("t1", api=api, dest=tmp_path / "word")
    assert report.revision == "a" * 40
    assert sorted(p.relative_to(tmp_path / "word").as_posix() for p in (tmp_path / "word").rglob("*")
                  if p.is_file()) == sorted(FILES)
    assert all(c["revision"] == "a" * 40 for name, c in api.calls if name != "repo_info")


def test_get_refuses_a_hub_file_whose_bytes_are_not_the_manifests(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _small_set(tmp_path, monkeypatch, FILES)
    tampered = {f"word/{k}": v for k, v in FILES.items()} | {"word/clean/pdf/a.pdf": b"%PDF" + b"b" * 100}
    api = PinnedHub(tampered)
    with pytest.raises(fs.FixtureSetError, match="clean/pdf/a.pdf"):
        fs.get("t1", api=api, dest=tmp_path / "word")
    assert not (tmp_path / "word" / "clean").exists()


def test_get_refuses_a_set_file_missing_from_the_pinned_commit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _small_set(tmp_path, monkeypatch, FILES)
    api = PinnedHub({"word/clean/docx/a.docx": FILES["clean/docx/a.docx"]})
    with pytest.raises(fs.FixtureSetError, match="1 file.*clean/pdf/a.pdf"):
        fs.get("t1", api=api, dest=tmp_path / "word")


def test_get_takes_one_test(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _small_set(tmp_path, monkeypatch, FILES)
    api = PinnedHub({f"word/{k}": v for k, v in FILES.items()})
    report = fs.get("t1", api=api, dest=tmp_path / "word", tests=("redline",), dry_run=True)
    assert report.n_files == 0


def test_include_of_exact_paths_does_not_glob(tmp_path: Path) -> None:
    """A set's paths go to hub_get as exact names; thousands of them must not cost a glob each."""
    api = PinnedHub({"outputs/run/a[1].docx": b"x", "outputs/run/a1.docx": b"y"})
    got = hub_get.remote_files(api, hub.RESULTS_REPO, "a" * 40, "outputs/run", include=["a[1].docx"])
    assert [f.rel for f in got] == ["a1.docx"]  # a glob: [1] is a character class, as before
    exact = hub_get.remote_files(api, hub.RESULTS_REPO, "a" * 40, "outputs/run", include=[], exact=["a[1].docx"])
    assert [f.rel for f in exact] == ["a[1].docx"]


# --- CLI ----------------------------------------------------------------------


def test_cli_lists_the_set_with_its_pin_and_counts() -> None:
    from neurotic_docx_bench.cli import app

    out = CliRunner().invoke(app, ["fixtures", "list", "v1"])
    assert out.exit_code == 0, out.output
    v1 = fs.load("v1")
    assert v1.revision in out.output
    for test, n in v1.cases.items():
        assert test in out.output and str(n) in out.output


def test_bytes_that_differ_from_the_manifest_never_reach_the_destination(tmp_path: Path,
                                                                          monkeypatch: pytest.MonkeyPatch) -> None:
    """#86 item 5: the listing matches the manifest, the download does not; nothing is placed.

    ``_check_remote`` ties the hub's recorded hash to the manifest's and ``hub_get`` checks the
    staged bytes against that record before any move, so the manifest is enforced pre-placement.
    """
    _small_set(tmp_path, monkeypatch, FILES)
    api = PinnedHub({f"word/{k}": v for k, v in FILES.items()})
    api.served["word/clean/pdf/a.pdf"] = b"%PDF" + b"z" * 100
    with pytest.raises(hub_get.GetError):
        fs.get("t1", api=api, dest=tmp_path / "word")
    assert not [p for p in (tmp_path / "word").rglob("*") if p.is_file()] if (tmp_path / "word").exists() else True


def test_a_kept_local_file_is_reported_as_not_the_sets(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """#86 item 6: --keep-local leaves bytes that are not the set's; the report must not call them verified."""
    _small_set(tmp_path, monkeypatch, FILES)
    api = PinnedHub({f"word/{k}": v for k, v in FILES.items()})
    local = tmp_path / "word" / "clean" / "pdf" / "a.pdf"
    local.parent.mkdir(parents=True)
    local.write_bytes(b"%PDF local edit")
    report = fs.get("t1", api=api, dest=tmp_path / "word", on_conflict="keep-local")
    assert report.kept_local == ("clean/pdf/a.pdf",)
    text = report.describe()
    assert "every file verified" not in text
    assert "1 kept local file(s) are not the hub's" in text and "clean/pdf/a.pdf" in text
