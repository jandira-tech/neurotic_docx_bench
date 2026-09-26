"""Spec for the redline half of the Word driver pair (``scripts/word_redline.py``).

The pairing, naming, skip and emit rules are pure functions, so they are tested
directly. The Word-facing half is reached through ``osa`` / ``export_pdf``,
both patched, which also pins the argv order the AppleScript is handed.
"""

from __future__ import annotations

import importlib.util
import io
import sys
import zipfile
from pathlib import Path

import pytest

# Every test here stubs Word. The fence turns a missed stub into a failure
# instead of a close-all sent to the Word that is actually running. The
# placeholder fixture is defined below, after `wr` is loaded.
pytestmark = pytest.mark.usefixtures("no_live_word", "placeholders_pass_the_identity_check")

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def _load(name: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS / f"{name}.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


wp = _load("word_pdf")
wr = _load("word_redline")
# Captured before the autouse fixture below stubs it for placeholder tests.
_REAL_REJECT_WRONG_PAIR = wr._reject_wrong_pair


@pytest.fixture
def placeholders_pass_the_identity_check(monkeypatch: pytest.MonkeyPatch) -> None:
    """These tests plant `PK` bytes where Word would have saved a package.

    `matches_pair` fails anything that is not a docx package, which is right for
    a real run and wrong for a placeholder. The check has its own tests
    (`test_redline_identity.py`); the wiring test below restores the real one.
    """
    monkeypatch.setattr(wr, "_reject_wrong_pair", lambda staged, base, revision: "")


def _verified_session(**kw) -> wp.WordSession:
    """A session in the state `preflight()` leaves behind on a clean Word.

    `redline_folders()` refuses an unverified session, because `started_clean`
    defaults to True and is a claim nobody checked. Tests have to present the
    same proof a real caller does, so this is what `preflight()` sets after it
    has asked Word and been told zero.
    """
    session = wp.WordSession(**kw)
    session.preflighted = True
    session.started_clean = True
    return session


def _touch(p: Path, body: bytes = b"x") -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(body)
    return p


def _applescript_code(src: str) -> str:
    """The script with its comments stripped.

    Asserting that a forbidden construct is absent has to look at the code. A
    comment that names `active document` in order to say the script avoids it
    is documentation doing its job, and must not fail the check that the code
    really does avoid it.
    """
    return "\n".join(ln for ln in src.splitlines() if not ln.strip().startswith("--"))


def _folder(root: Path, *names: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    for n in names:
        _touch(root / n)
    return root


# ─── pairing ─────────────────────────────────────────────────────────────────


def test_pair_by_name_matches_counterparts_and_reports_the_rest(tmp_path: Path) -> None:
    a = _folder(tmp_path / "a", "deal.docx", "nda.docx", "only-a.docx")
    b = _folder(tmp_path / "b", "nda.docx", "deal.docx", "only-b.docx")

    pairing = wr.pair_by_name(wp.iter_docx(a), wp.iter_docx(b))

    assert [(x.name, y.name) for x, y in pairing.pairs] == [
        ("deal.docx", "deal.docx"),
        ("nda.docx", "nda.docx"),
    ]
    assert [p.name for p in pairing.only_a] == ["only-a.docx"]
    assert [p.name for p in pairing.only_b] == ["only-b.docx"]


def test_pair_by_name_excludes_word_lock_files_through_iter_docx(tmp_path: Path) -> None:
    a = _folder(tmp_path / "a", "deal.docx", "~$deal.docx")
    b = _folder(tmp_path / "b", "deal.docx", "~$deal.docx")

    pairing = wr.pair_by_name(wp.iter_docx(a), wp.iter_docx(b))
    assert len(pairing.pairs) == 1
    assert not any("~$" in p.name for p, _ in pairing.pairs)


def test_pair_by_name_with_nothing_in_common(tmp_path: Path) -> None:
    a = _folder(tmp_path / "a", "x.docx")
    b = _folder(tmp_path / "b", "y.docx")
    pairing = wr.pair_by_name(wp.iter_docx(a), wp.iter_docx(b))
    assert pairing.pairs == []
    assert len(pairing.only_a) == 1 and len(pairing.only_b) == 1


def test_cross_pairs_is_the_full_product(tmp_path: Path) -> None:
    a = _folder(tmp_path / "a", "one.docx", "two.docx")
    b = _folder(tmp_path / "b", "x.docx", "y.docx", "z.docx")

    pairs = wr.cross_pairs(wp.iter_docx(a), wp.iter_docx(b))
    assert len(pairs) == 6
    assert len({(x, y) for x, y in pairs}) == 6


def test_cross_pairs_drops_self_pairs_when_both_folders_are_one(tmp_path: Path) -> None:
    a = _folder(tmp_path / "a", "one.docx", "two.docx", "three.docx")
    docs = wp.iter_docx(a)

    pairs = wr.cross_pairs(docs, docs)
    assert len(pairs) == 6  # 3x3 minus the three self-comparisons
    assert all(x != y for x, y in pairs)


# ─── naming ──────────────────────────────────────────────────────────────────


def test_redline_stem_names_both_sides_even_when_they_match(tmp_path: Path) -> None:
    """A redline must not be named exactly like either document it came from.

    Same-stem pairs used to collapse to the bare shared name, so comparing
    `before/deal.docx` against `after/deal.docx` produced `deal.docx` — a
    tracked-changes document indistinguishable by name from both its inputs.
    """
    got = wr.redline_stem(tmp_path / "a" / "deal.docx", tmp_path / "b" / "deal.docx")
    assert got == "deal__vs__deal"


def test_redline_stem_names_both_sides_when_they_differ(tmp_path: Path) -> None:
    got = wr.redline_stem(tmp_path / "a" / "v1.docx", tmp_path / "b" / "v2.docx")
    assert got == "v1__vs__v2"


# ─── emit / outputs ──────────────────────────────────────────────────────────


def test_plan_outputs_pdf_only_is_the_default_shape(tmp_path: Path) -> None:
    out = wr.plan_outputs(
        tmp_path / "a" / "deal.docx",
        tmp_path / "b" / "deal.docx",
        tmp_path / "out",
        None,
        wr.Emit.PDF,
    )
    assert out.pdf == tmp_path / "out" / "deal__vs__deal.pdf"
    assert out.docx is None


def test_plan_outputs_docx_only(tmp_path: Path) -> None:
    out = wr.plan_outputs(
        tmp_path / "a" / "deal.docx",
        tmp_path / "b" / "deal.docx",
        tmp_path / "out",
        None,
        wr.Emit.DOCX,
    )
    assert out.docx == tmp_path / "out" / "deal__vs__deal.docx"
    assert out.pdf is None


def test_plan_outputs_both_can_split_the_destinations(tmp_path: Path) -> None:
    out = wr.plan_outputs(
        tmp_path / "a" / "deal.docx",
        tmp_path / "b" / "deal.docx",
        tmp_path / "pdf",
        tmp_path / "docx",
        wr.Emit.BOTH,
    )
    assert out.pdf == tmp_path / "pdf" / "deal__vs__deal.pdf"
    assert out.docx == tmp_path / "docx" / "deal__vs__deal.docx"


def test_plan_outputs_wants_docx_internally_for_every_mode(tmp_path: Path) -> None:
    """Word only ever yields the comparison as an open document."""
    for emit in (wr.Emit.PDF, wr.Emit.DOCX, wr.Emit.BOTH):
        out = wr.plan_outputs(
            tmp_path / "a.docx", tmp_path / "b.docx", tmp_path / "o", None, emit
        )
        assert out.wanted, emit


def test_should_skip_only_when_every_wanted_output_is_present(tmp_path: Path) -> None:
    pdf = _touch(tmp_path / "out" / "deal__vs__deal.pdf", b"%PDF")
    docx = tmp_path / "out" / "deal__vs__deal.docx"

    assert wr.should_skip(wr.Outputs(docx=None, pdf=pdf), force=False) is True
    assert wr.should_skip(wr.Outputs(docx=docx, pdf=pdf), force=False) is False
    assert wr.should_skip(wr.Outputs(docx=None, pdf=pdf), force=True) is False


def test_should_skip_rejects_a_zero_byte_leftover(tmp_path: Path) -> None:
    pdf = _touch(tmp_path / "out" / "deal__vs__deal.pdf", b"")
    assert wr.should_skip(wr.Outputs(docx=None, pdf=pdf), force=False) is False


# ─── revision count ──────────────────────────────────────────────────────────


@pytest.mark.parametrize(("raw", "expected"), [("12", 12), ("0", 0), ("", -1), ("nope", -1)])
def test_parse_revision_count(raw: str, expected: int) -> None:
    assert wr.parse_revision_count(raw) == expected


# ─── compare_pair ────────────────────────────────────────────────────────────


def test_compare_pair_passes_base_revision_out_in_that_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    out = tmp_path / "deal.docx"
    seen: dict[str, object] = {}

    def fake_osa(script, *args, timeout=60.0):
        seen["script"] = script
        seen["args"] = args
        _touch(out, b"PK")
        return 0, "7", ""

    monkeypatch.setattr(wr, "osa", fake_osa)
    ok, revisions, err = wr.compare_pair(tmp_path / "base.docx", tmp_path / "rev.docx", out)

    assert (ok, revisions, err) == (True, 7, "")
    assert seen["script"] is wr._COMPARE
    assert seen["args"] == (
        str(tmp_path / "base.docx"),
        str(tmp_path / "rev.docx"),
        str(out),
    )


def test_compare_pair_fails_when_word_wrote_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(wr, "osa", lambda *a, **k: (0, "3", ""))
    ok, revisions, err = wr.compare_pair(
        tmp_path / "base.docx", tmp_path / "rev.docx", tmp_path / "out.docx"
    )
    assert ok is False and revisions == -1
    assert "no output file" in err


def test_compare_pair_surfaces_the_applescript_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        wr, "osa", lambda *a, **k: (1, "", "compare produced no result document\n")
    )
    ok, _, err = wr.compare_pair(
        tmp_path / "base.docx", tmp_path / "rev.docx", tmp_path / "out.docx"
    )
    assert ok is False
    assert err == "compare produced no result document"


def test_compare_applescript_identifies_the_result_by_exclusion() -> None:
    """`compare` returns a NEW document; name the one you mean, never the active one.

    The earlier docstring here claimed `active document` stays on the BASE when
    a compare silently produces nothing. That premise is wrong (§5.11): the
    result arrives as a new, unsaved document. Identifying it by exclusion is
    still right, because a script should name the document it means.
    """
    src = wr._COMPARE
    assert "active document" not in _applescript_code(src)
    # It is named in a comment, as the thing being avoided.
    assert "active document" in src
    assert "repeat with i from 1 to docCount" in src
    assert "detect format changes true" in src
    # Health is evaluated before anything is saved.
    assert src.index("count of paragraphs") < src.index("compare baseDoc")


# ─── redline_folders ─────────────────────────────────────────────────────────


@pytest.fixture
def stub_word(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """A Word that always compares successfully and always exports a PDF."""
    monkeypatch.setattr(wp, "CONTAINER_TMP", tmp_path / "container")

    compared: list[dict[str, object]] = []
    exported: list[Path] = []

    def fake_compare(base, rev, out, *, timeout=300.0):
        # Capture the staged CONTENTS here: redline_folders deletes the staged
        # inputs as soon as the pair finishes, so the paths are gone by the time
        # a test asserts on them.
        compared.append(
            {
                "base": base,
                "rev": rev,
                "out": out,
                "base_bytes": base.read_bytes(),
                "rev_bytes": rev.read_bytes(),
            }
        )
        _touch(out, b"PK-redline")
        return True, 4, ""

    def fake_export(src, dst, *, timeout=180.0):
        exported.append(src)
        _touch(dst, b"%PDF-1.7")
        return True, ""

    monkeypatch.setattr(wr, "compare_pair", fake_compare)
    monkeypatch.setattr(wr, "export_pdf", fake_export)
    session = _verified_session()
    monkeypatch.setattr(session, "warm", lambda: True)
    monkeypatch.setattr(session, "recycle", lambda *f: True)
    monkeypatch.setattr(session, "quit_if_ours", lambda: None)
    return session, compared, exported


def test_redline_folders_default_writes_pdf_only(tmp_path: Path, stub_word) -> None:
    session, compared, exported = stub_word
    a = _folder(tmp_path / "a", "deal.docx")
    b = _folder(tmp_path / "b", "deal.docx")
    out = tmp_path / "out"

    results = wr.redline_folders(a, b, out, session=session, one_osascript=False)

    assert len(results) == 1 and results[0].ok
    assert (out / "deal__vs__deal.pdf").exists()
    assert not (out / "deal__vs__deal.docx").exists()
    assert len(compared) == 1 and len(exported) == 1


def test_redline_folders_both_keeps_the_tracked_changes_docx(
    tmp_path: Path, stub_word
) -> None:
    session, _, _ = stub_word
    a = _folder(tmp_path / "a", "deal.docx")
    b = _folder(tmp_path / "b", "deal.docx")
    out = tmp_path / "out"

    wr.redline_folders(a, b, out, emit=wr.Emit.BOTH, session=session, one_osascript=False)

    assert (out / "deal__vs__deal.pdf").exists()
    assert (out / "deal__vs__deal.docx").read_bytes() == b"PK-redline"


def test_redline_folders_docx_only_never_calls_the_pdf_exporter(
    tmp_path: Path, stub_word
) -> None:
    session, _, exported = stub_word
    a = _folder(tmp_path / "a", "deal.docx")
    b = _folder(tmp_path / "b", "deal.docx")
    out = tmp_path / "out"

    wr.redline_folders(a, b, out, emit=wr.Emit.DOCX, session=session, one_osascript=False)

    assert exported == []
    assert (out / "deal__vs__deal.docx").exists()
    assert not (out / "deal__vs__deal.pdf").exists()


def _tracked_changes_docx() -> bytes:
    """A minimal Word-shaped package whose body carries one insertion and one deletion.

    Synthesised rather than committed: a binary fixture has to be trusted on
    sight, and the only thing this test needs from it is that both markup
    families survive the trip to the delivered file.
    """
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body><w:p>"
        '<w:ins w:id="1" w:author="Microsoft Word" w:date="2026-09-21T00:00:00Z">'
        "<w:r><w:t>added</w:t></w:r></w:ins>"
        '<w:del w:id="2" w:author="Microsoft Word" w:date="2026-09-21T00:00:00Z">'
        "<w:r><w:delText>removed</w:delText></w:r></w:del>"
        "</w:p></w:body></w:document>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" ContentType="application/vnd.'
        'openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>'
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("word/document.xml", document)
    return buf.getvalue()


def test_delivered_redline_docx_carries_tracked_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """What is handed over must be the comparison, not a copy of an input.

    `stub_word` already proves delivery is byte-faithful, but it proves it with
    a sentinel that is not a document, so nothing pins the output *contract*:
    a redline is a .docx carrying tracked changes. This drives the same path
    with a real package and reads the markup back out of the delivered file, so
    a regression that delivered the base instead of the comparison fails here.
    Deterministic, and independent of Microsoft Word.
    """
    monkeypatch.setattr(wp, "CONTAINER_TMP", tmp_path / "container")

    def fake_compare(base, rev, out, *, timeout=300.0):
        out.write_bytes(_tracked_changes_docx())
        return True, 2, ""

    monkeypatch.setattr(wr, "compare_pair", fake_compare)
    session = _verified_session()
    monkeypatch.setattr(session, "warm", lambda: True)
    monkeypatch.setattr(session, "recycle", lambda *f: True)
    monkeypatch.setattr(session, "quit_if_ours", lambda: None)

    a = _folder(tmp_path / "a", "deal.docx")
    b = _folder(tmp_path / "b", "deal.docx")
    out = tmp_path / "out"

    results = wr.redline_folders(a, b, out, emit=wr.Emit.DOCX, session=session, one_osascript=False)

    assert len(results) == 1 and results[0].ok
    with zipfile.ZipFile(out / "deal__vs__deal.docx") as z:
        body = z.read("word/document.xml").decode("utf-8")
    assert "<w:ins " in body
    assert "<w:del " in body
    assert "<w:delText>" in body


def test_redline_folders_stages_same_named_sides_apart(tmp_path: Path, stub_word) -> None:
    session, compared, _ = stub_word
    a = _folder(tmp_path / "a", "deal.docx")
    b = _folder(tmp_path / "b", "deal.docx")

    wr.redline_folders(a, b, tmp_path / "out", session=session, one_osascript=False)

    call = compared[0]
    assert call["base"] != call["rev"]
    assert call["base_bytes"] == (a / "deal.docx").read_bytes()
    assert call["base"].parent == call["rev"].parent  # one container inbox


def test_redline_folders_swap_reverses_which_side_is_the_original(
    tmp_path: Path, stub_word
) -> None:
    session, compared, _ = stub_word
    a = _folder(tmp_path / "a", "deal.docx")
    _touch(a / "deal.docx", b"AAA")
    b = _folder(tmp_path / "b", "deal.docx")
    _touch(b / "deal.docx", b"BBB")

    wr.redline_folders(a, b, tmp_path / "out", swap=True, session=session, one_osascript=False)

    call = compared[0]
    assert call["base_bytes"] == b"BBB"
    assert call["rev_bytes"] == b"AAA"


def test_redline_folders_skips_existing_unless_forced(tmp_path: Path, stub_word) -> None:
    session, compared, _ = stub_word
    a = _folder(tmp_path / "a", "deal.docx")
    b = _folder(tmp_path / "b", "deal.docx")
    out = tmp_path / "out"
    _touch(out / "deal__vs__deal.pdf", b"%PDF")

    results = wr.redline_folders(a, b, out, session=session, one_osascript=False)
    assert results[0].skipped and results[0].ok and compared == []

    wr.redline_folders(a, b, out, force=True, session=session, one_osascript=False)
    assert len(compared) == 1


def test_redline_folders_recycles_word_after_a_failed_pair(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(wp, "CONTAINER_TMP", tmp_path / "container")
    a = _folder(tmp_path / "a", "bad.docx", "good.docx")
    b = _folder(tmp_path / "b", "bad.docx", "good.docx")

    def fake_compare(base, rev, out, *, timeout=300.0):
        if "bad" in out.name:
            return False, -1, "compare produced no result document"
        _touch(out, b"PK")
        return True, 2, ""

    monkeypatch.setattr(wr, "compare_pair", fake_compare)
    monkeypatch.setattr(
        wr, "export_pdf", lambda s, d, timeout=180.0: (True, _touch(d, b"%PDF") and "")
    )
    session = _verified_session()
    monkeypatch.setattr(session, "warm", lambda: True)
    monkeypatch.setattr(session, "quit_if_ours", lambda: None)
    # Word answers the cleanup but keeps a document open: the escalation case.
    monkeypatch.setattr(wp, "osa", lambda *a, **k: (0, "", ""))
    monkeypatch.setattr(session, "open_document_count", lambda: 1)
    recycled: list[tuple] = []
    monkeypatch.setattr(session, "recycle", lambda *f: recycled.append(f) or True)

    results = wr.redline_folders(a, b, tmp_path / "out", session=session, one_osascript=False)

    assert [r.ok for r in results] == [False, True]
    assert len(recycled) == 1


def test_redline_folders_records_a_change_free_comparison_without_failing_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Identical inputs legitimately compare to zero revisions; that is not an error."""
    monkeypatch.setattr(wp, "CONTAINER_TMP", tmp_path / "container")
    a = _folder(tmp_path / "a", "deal.docx")
    b = _folder(tmp_path / "b", "deal.docx")

    monkeypatch.setattr(
        wr, "compare_pair", lambda base, rev, out, timeout=300.0: (True, 0, _touch(out, b"PK") and "")
    )
    monkeypatch.setattr(
        wr, "export_pdf", lambda s, d, timeout=180.0: (True, _touch(d, b"%PDF") and "")
    )
    session = _verified_session()
    monkeypatch.setattr(session, "warm", lambda: True)
    monkeypatch.setattr(session, "quit_if_ours", lambda: None)

    results = wr.redline_folders(a, b, tmp_path / "out", session=session, one_osascript=False)
    assert results[0].ok is True
    assert results[0].revisions == 0


def test_redline_folders_cross_mode_runs_every_combination(tmp_path: Path, stub_word) -> None:
    session, compared, _ = stub_word
    a = _folder(tmp_path / "a", "one.docx", "two.docx")
    b = _folder(tmp_path / "b", "x.docx")

    results = wr.redline_folders(a, b, tmp_path / "out", cross=True, session=session, one_osascript=False)

    assert len(results) == 2
    assert len(compared) == 2
    assert (tmp_path / "out" / "one__vs__x.pdf").exists()
    assert (tmp_path / "out" / "two__vs__x.pdf").exists()


def test_redline_folders_with_no_pairs_returns_empty(tmp_path: Path, stub_word) -> None:
    session, _, _ = stub_word
    a = _folder(tmp_path / "a", "x.docx")
    b = _folder(tmp_path / "b", "y.docx")
    assert wr.redline_folders(a, b, tmp_path / "out", session=session) == []


# ─── reporting ───────────────────────────────────────────────────────────────


def test_report_pairs_exit_code(tmp_path: Path) -> None:
    ok = wr.PairResult(base=tmp_path / "a.docx", revision=tmp_path / "b.docx", ok=True, revisions=3)
    bad = wr.PairResult(base=tmp_path / "c.docx", revision=tmp_path / "d.docx", error="boom")

    assert wr.report_pairs([ok]) == 0
    assert wr.report_pairs([ok, bad]) == 1
    assert wr.report_pairs([]) == 0


# ─── CLI smoke ───────────────────────────────────────────────────────────────


def test_cli_help_exits_cleanly() -> None:
    from typer.testing import CliRunner

    result = CliRunner().invoke(wr.app, ["--help"])
    assert result.exit_code == 0
    for flag in ("--a", "--b", "--emit", "--cross", "--swap", "--docx-out"):
        assert flag in result.output


@pytest.mark.parametrize("missing", ["--a", "--b"])
def test_cli_rejects_a_folder_that_does_not_exist(
    tmp_path: Path, missing: str
) -> None:
    from typer.testing import CliRunner

    real = tmp_path / "real"
    real.mkdir()
    args = {"--a": str(real), "--b": str(real)}
    args[missing] = str(tmp_path / "nope")
    result = CliRunner().invoke(
        wr.app, ["--a", args["--a"], "--b", args["--b"], "--no-check-preset"]
    )
    assert result.exit_code == 2


def test_cli_warns_that_pdf_only_discards_the_redline_docx(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from typer.testing import CliRunner

    a = _folder(tmp_path / "a", "deal.docx")
    b = _folder(tmp_path / "b", "deal.docx")
    monkeypatch.setattr(
        wr,
        "preflight",
        lambda s, *, allow_open_docs, close_documents=True: "Word is busy",
    )

    result = CliRunner().invoke(wr.app, ["--a", str(a), "--b", str(b)])
    assert result.exit_code == 2
    assert "--emit both" in result.output
    assert "Best for printing" in result.output
    assert "Markup display" in result.output


def test_cli_docx_only_skips_the_pdf_reminders(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from typer.testing import CliRunner

    a = _folder(tmp_path / "a", "deal.docx")
    b = _folder(tmp_path / "b", "deal.docx")
    monkeypatch.setattr(
        wr,
        "preflight",
        lambda s, *, allow_open_docs, close_documents=True: "Word is busy",
    )

    result = CliRunner().invoke(wr.app, ["--a", str(a), "--b", str(b), "--emit", "docx"])
    assert "Best for printing" not in result.output


def test_cli_runs_the_batch_and_returns_the_report_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from typer.testing import CliRunner

    a = _folder(tmp_path / "a", "deal.docx")
    b = _folder(tmp_path / "b", "deal.docx")
    seen: dict[str, object] = {}

    monkeypatch.setattr(
        wr, "preflight", lambda s, *, allow_open_docs, close_documents=True: ""
    )
    monkeypatch.setattr(wr.Watchdogs, "start", lambda self: None)
    monkeypatch.setattr(wr.Watchdogs, "stop", lambda self: None)
    monkeypatch.setattr(wr.WordSession, "quit_if_ours", lambda self: None)

    def fake_redline(fa, fb, out, **kw):
        seen.update(kw)
        seen["out"] = out
        return [wr.PairResult(base=fa / "deal.docx", revision=fb / "deal.docx", error="boom")]

    monkeypatch.setattr(wr, "redline_folders", fake_redline)

    result = CliRunner().invoke(
        wr.app,
        [
            "--a", str(a),
            "--b", str(b),
            "--out", str(tmp_path / "out"),
            "--emit", "both",
            "--cross",
            "--swap",
            "--force",
            "--no-check-preset",
        ],
    )

    assert result.exit_code == 1
    assert seen["emit"] is wr.Emit.BOTH
    assert seen["cross"] is True and seen["swap"] is True and seen["force"] is True
    assert seen["out"] == tmp_path / "out"


# ─── malformed documents ─────────────────────────────────────────────────────


def test_serial_failure_recovers_without_restarting_word(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(wp, "CONTAINER_TMP", tmp_path / "container")
    a = _folder(tmp_path / "a", "bad.docx", "good.docx")
    b = _folder(tmp_path / "b", "bad.docx", "good.docx")

    monkeypatch.setattr(
        wr,
        "compare_pair",
        lambda base, rev, out, timeout=300.0: (
            (False, -1, "base loaded empty (Word could not read it)")
            if "bad" in out.name
            else (True, 2, _touch(out, b"PK") and "")
        ),
    )
    monkeypatch.setattr(
        wr, "export_pdf", lambda s, d, timeout=180.0: (True, _touch(d, b"%PDF") and "")
    )
    recovered: list[object] = []
    recycled: list[object] = []
    monkeypatch.setattr(wr, "recover_after_failure", lambda s, *f: recovered.append(f) or True)
    session = _verified_session()
    monkeypatch.setattr(session, "warm", lambda: True)
    monkeypatch.setattr(session, "quit_if_ours", lambda: None)
    monkeypatch.setattr(session, "recycle", lambda *f: recycled.append(f) or True)

    results = wr.redline_folders(a, b, tmp_path / "out", session=session, one_osascript=False)

    assert [r.ok for r in results] == [False, True]
    assert len(recovered) == 1
    assert recycled == []


def test_serial_recycles_after_a_streak_of_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(wp, "CONTAINER_TMP", tmp_path / "container")
    names = ("a.docx", "b.docx", "c.docx")
    a = _folder(tmp_path / "a", *names)
    b = _folder(tmp_path / "b", *names)

    monkeypatch.setattr(
        wr, "compare_pair", lambda base, rev, out, timeout=300.0: (False, -1, "empty")
    )
    monkeypatch.setattr(wr, "recover_after_failure", lambda s, *f: True)
    session = _verified_session()
    monkeypatch.setattr(session, "warm", lambda: True)
    monkeypatch.setattr(session, "quit_if_ours", lambda: None)
    recycled: list[object] = []
    monkeypatch.setattr(session, "recycle", lambda *f: recycled.append(f) or True)

    wr.redline_folders(a, b, tmp_path / "out", session=session, one_osascript=False, poison_streak=3)
    assert len(recycled) == 1


# ─── two-osascript batch mode ────────────────────────────────────────────────


def test_one_redline_osascript_is_the_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A folder-sized redline runs as the monolithic pair unless told otherwise."""
    import inspect

    assert inspect.signature(wr.redline_folders).parameters["one_osascript"].default is True
    assert inspect.signature(wr.main).parameters["one_osascript"].default is True

    # And driving it without the argument really does take the batch path.
    monkeypatch.setattr(wp, "CONTAINER_TMP", tmp_path / "container")
    a = _folder(tmp_path / "a", "deal.docx")
    b = _folder(tmp_path / "b", "deal.docx")
    scripts: list[str] = []

    def fake_osa(script, *args, timeout=60.0):
        scripts.append(script)
        manifest, log = Path(args[0]), Path(args[1])
        rows = [ln.split("\t") for ln in manifest.read_text().splitlines() if ln]
        lines = []
        for row in rows:
            Path(row[-1]).write_bytes(b"PK")
            lines.append(f"[ok]\t{row[0]}\t3" if script is wr._COMPARE_BATCH else f"[ok]\t{row[0]}")
        log.write_text("\n".join(lines) + "\n")
        return 0, "ok", ""

    # The batch runner is `word_pdf.run_batch_with_resume`, so it is word_pdf's
    # `osa` that gets called, not word_redline's.
    monkeypatch.setattr(wp, "osa", fake_osa)
    session = _verified_session()
    monkeypatch.setattr(session, "warm", lambda: True)
    monkeypatch.setattr(session, "quit_if_ours", lambda: None)
    wr.redline_folders(a, b, tmp_path / "out", session=session)
    assert wr._COMPARE_BATCH in scripts


def test_compare_batch_script_keeps_every_per_pair_rule() -> None:
    src = wr._COMPARE_BATCH
    assert "active document" not in _applescript_code(src)
    assert "repeat with i from 1 to docCount" in src
    assert "cmpCount is not 1" in src
    assert "seenBeforeCompare does not contain nm" in src
    assert "refusing to guess" in src
    assert "close every document" not in wr._COMPARE_BATCH_KEEP_OPEN
    assert "detect format changes true" in src
    assert src.index("count of paragraphs") < src.index("compare baseDoc")
    # One bad pair closes and continues rather than stopping the run.
    assert "on error errMsg" in src
    assert src.count("close every document saving no") >= 4
    # A timeout, or a streak of empty bases, poisons every later compare (§5.20).
    # The timed-out pair is a final [fail] and the batch stops. Empty-load streaks
    # are [retry], which the log parser ignores, so they are retried after a recycle.
    assert "set emptyStreak to 0" in src
    assert '"[retry]" & tab & itemId' in src
    assert 'errMsg contains "loaded empty"' in src
    assert 'if errMsg contains "timed out" then' in src
    assert "exit repeat" in src
    assert "emptyStreak ≥ 3" in src
    # The revision count rides out on the [ok] line.
    assert '"[ok]" & tab & itemId & tab & revisionCount' in src
    assert "set displayAlerts to false" in src


def test_redline_batched_runs_compare_then_pdf_as_two_scripts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(wp, "CONTAINER_TMP", tmp_path / "container")
    a = _folder(tmp_path / "a", "deal.docx", "nda.docx")
    b = _folder(tmp_path / "b", "deal.docx", "nda.docx")
    scripts: list[str] = []

    def fake_osa(script, *args, timeout=60.0):
        scripts.append(script)
        manifest, log = Path(args[0]), Path(args[1])
        rows = [ln.split("\t") for ln in manifest.read_text().splitlines() if ln]
        lines = []
        for row in rows:
            out = Path(row[-1])
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(b"PK" if out.suffix == ".docx" else b"%PDF")
            lines.append(f"[ok]\t{row[0]}" + ("\t5" if script is wr._COMPARE_BATCH else ""))
        lines.append(f"[done]\t{len(rows)}\t0")
        log.write_text("\n".join(lines) + "\n")
        return 0, "", ""

    monkeypatch.setattr(wp, "osa", fake_osa)
    session = _verified_session()
    monkeypatch.setattr(session, "warm", lambda: True)
    monkeypatch.setattr(session, "quit_if_ours", lambda: None)

    results = wr.redline_folders(a, b, tmp_path / "out", session=session, one_osascript=True)

    assert scripts == [wr._COMPARE_BATCH, wr._EXPORT_BATCH]  # exactly two, in order
    assert all(r.ok for r in results)
    assert all(r.revisions == 5 for r in results)  # read off the [ok] line
    assert all(r.timing_exact is False for r in results)
    assert (tmp_path / "out" / "deal__vs__deal.pdf").exists()
    assert (tmp_path / "out" / "nda__vs__nda.pdf").exists()
    assert not (tmp_path / "out" / "deal__vs__deal.docx").exists()  # --emit pdf discards it


def test_redline_batched_docx_only_runs_one_script(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(wp, "CONTAINER_TMP", tmp_path / "container")
    a = _folder(tmp_path / "a", "deal.docx")
    b = _folder(tmp_path / "b", "deal.docx")
    scripts: list[str] = []

    def fake_osa(script, *args, timeout=60.0):
        scripts.append(script)
        manifest, log = Path(args[0]), Path(args[1])
        rows = [ln.split("\t") for ln in manifest.read_text().splitlines() if ln]
        lines = []
        for row in rows:
            Path(row[-1]).write_bytes(b"PK")
            lines.append(f"[ok]\t{row[0]}\t3")
        lines.append(f"[done]\t{len(rows)}\t0")
        log.write_text("\n".join(lines) + "\n")
        return 0, "", ""

    monkeypatch.setattr(wp, "osa", fake_osa)
    session = _verified_session()
    monkeypatch.setattr(session, "warm", lambda: True)
    monkeypatch.setattr(session, "quit_if_ours", lambda: None)

    results = wr.redline_folders(
        a, b, tmp_path / "out", emit=wr.Emit.DOCX, session=session, one_osascript=True
    )

    assert scripts == [wr._COMPARE_BATCH]  # no PDF pass when none was asked for
    assert results[0].ok and results[0].revisions == 3
    assert (tmp_path / "out" / "deal__vs__deal.docx").read_bytes() == b"PK"


def test_redline_batched_records_a_failed_pair_and_finishes_the_rest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(wp, "CONTAINER_TMP", tmp_path / "container")
    a = _folder(tmp_path / "a", "bad.docx", "good.docx")
    b = _folder(tmp_path / "b", "bad.docx", "good.docx")

    def fake_osa(script, *args, timeout=60.0):
        manifest, log = Path(args[0]), Path(args[1])
        rows = [ln.split("\t") for ln in manifest.read_text().splitlines() if ln]
        lines = []
        for row in rows:
            out = Path(row[-1])
            if "bad" in out.name:
                lines.append(f"[fail]\t{row[0]}\tbase loaded empty (Word could not read it)")
                continue
            out.write_bytes(b"PK" if out.suffix == ".docx" else b"%PDF")
            lines.append(f"[ok]\t{row[0]}" + ("\t1" if script is wr._COMPARE_BATCH else ""))
        lines.append(f"[done]\t{len(rows)}\t0")
        log.write_text("\n".join(lines) + "\n")
        return 0, "", ""

    monkeypatch.setattr(wp, "osa", fake_osa)
    session = _verified_session()
    monkeypatch.setattr(session, "warm", lambda: True)
    monkeypatch.setattr(session, "quit_if_ours", lambda: None)

    results = wr.redline_folders(a, b, tmp_path / "out", session=session, one_osascript=True)

    assert [(r.base.name, r.ok) for r in results] == [("bad.docx", False), ("good.docx", True)]
    assert "could not read" in results[0].error
    assert (tmp_path / "out" / "good__vs__good.pdf").exists()
    assert not (tmp_path / "out" / "bad__vs__bad.pdf").exists()


def test_redline_batched_skips_existing_and_stages_the_rest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(wp, "CONTAINER_TMP", tmp_path / "container")
    a = _folder(tmp_path / "a", "deal.docx", "nda.docx")
    b = _folder(tmp_path / "b", "deal.docx", "nda.docx")
    _touch(tmp_path / "out" / "deal__vs__deal.pdf", b"%PDF")
    manifests: list[int] = []

    def fake_osa(script, *args, timeout=60.0):
        manifest, log = Path(args[0]), Path(args[1])
        rows = [ln.split("\t") for ln in manifest.read_text().splitlines() if ln]
        manifests.append(len(rows))
        lines = []
        for row in rows:
            out = Path(row[-1])
            out.write_bytes(b"PK" if out.suffix == ".docx" else b"%PDF")
            lines.append(f"[ok]\t{row[0]}" + ("\t2" if script is wr._COMPARE_BATCH else ""))
        lines.append(f"[done]\t{len(rows)}\t0")
        log.write_text("\n".join(lines) + "\n")
        return 0, "", ""

    monkeypatch.setattr(wp, "osa", fake_osa)
    session = _verified_session()
    monkeypatch.setattr(session, "warm", lambda: True)
    monkeypatch.setattr(session, "quit_if_ours", lambda: None)

    results = wr.redline_folders(a, b, tmp_path / "out", session=session, one_osascript=True)

    assert results[0].skipped and results[1].ok
    assert manifests == [1, 1]  # only nda went into either script


def test_redline_batched_resumes_the_compare_pass_after_a_wedge(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(wp, "CONTAINER_TMP", tmp_path / "container")
    names = ("one.docx", "two.docx")
    a = _folder(tmp_path / "a", *names)
    b = _folder(tmp_path / "b", *names)
    calls = {"n": 0}

    def fake_osa(script, *args, timeout=60.0):
        calls["n"] += 1
        manifest, log = Path(args[0]), Path(args[1])
        rows = [ln.split("\t") for ln in manifest.read_text().splitlines() if ln]
        wedge = calls["n"] == 1
        lines = []
        for row in rows[: 1 if wedge else len(rows)]:
            out = Path(row[-1])
            out.write_bytes(b"PK" if out.suffix == ".docx" else b"%PDF")
            lines.append(f"[ok]\t{row[0]}" + ("\t4" if script is wr._COMPARE_BATCH else ""))
        if not wedge:
            lines.append(f"[done]\t{len(rows)}\t0")
        log.write_text("\n".join(lines) + "\n")
        return (None if wedge else 0), "", ""

    monkeypatch.setattr(wp, "osa", fake_osa)
    session = _verified_session()
    monkeypatch.setattr(session, "warm", lambda: True)
    monkeypatch.setattr(session, "quit_if_ours", lambda: None)
    recycled: list[object] = []
    monkeypatch.setattr(session, "recycle", lambda *f: recycled.append(f) or True)

    results = wr.redline_folders(a, b, tmp_path / "out", session=session, one_osascript=True)

    assert all(r.ok for r in results)
    assert len(recycled) == 1  # recycled between compare passes
    assert calls["n"] == 3  # compare, compare-resume, pdf


def test_redline_batched_stages_same_named_sides_apart(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(wp, "CONTAINER_TMP", tmp_path / "container")
    a = _folder(tmp_path / "a", "deal.docx")
    _touch(a / "deal.docx", b"AAA")
    b = _folder(tmp_path / "b", "deal.docx")
    _touch(b / "deal.docx", b"BBB")
    seen: dict[str, bytes] = {}

    def fake_osa(script, *args, timeout=60.0):
        manifest, log = Path(args[0]), Path(args[1])
        rows = [ln.split("\t") for ln in manifest.read_text().splitlines() if ln]
        lines = []
        for row in rows:
            if script is wr._COMPARE_BATCH:
                seen["base"] = Path(row[1]).read_bytes()
                seen["rev"] = Path(row[2]).read_bytes()
            out = Path(row[-1])
            out.write_bytes(b"PK" if out.suffix == ".docx" else b"%PDF")
            lines.append(f"[ok]\t{row[0]}" + ("\t1" if script is wr._COMPARE_BATCH else ""))
        lines.append(f"[done]\t{len(rows)}\t0")
        log.write_text("\n".join(lines) + "\n")
        return 0, "", ""

    monkeypatch.setattr(wp, "osa", fake_osa)
    session = _verified_session()
    monkeypatch.setattr(session, "warm", lambda: True)
    monkeypatch.setattr(session, "quit_if_ours", lambda: None)

    wr.redline_folders(a, b, tmp_path / "out", session=session, one_osascript=True)
    assert seen == {"base": b"AAA", "rev": b"BBB"}


def test_cli_wires_the_two_script_flag_through(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from typer.testing import CliRunner

    a = _folder(tmp_path / "a", "deal.docx")
    b = _folder(tmp_path / "b", "deal.docx")
    seen: dict[str, object] = {}

    monkeypatch.setattr(
        wr, "preflight", lambda s, *, allow_open_docs, close_documents=True: ""
    )
    monkeypatch.setattr(wr.Watchdogs, "start", lambda self: None)
    monkeypatch.setattr(wr.Watchdogs, "stop", lambda self: None)
    monkeypatch.setattr(wr.WordSession, "quit_if_ours", lambda self: None)
    monkeypatch.setattr(wr, "redline_folders", lambda fa, fb, out, **kw: seen.update(kw) or [])

    result = CliRunner().invoke(
        wr.app,
        ["--a", str(a), "--b", str(b), "--one-redline-osascript", "--no-check-preset"],
    )
    assert result.exit_code == 0
    assert seen["one_osascript"] is True


def test_report_pairs_does_not_call_a_batch_average_a_median(tmp_path: Path) -> None:
    batched = wr.PairResult(
        base=tmp_path / "a.docx", revision=tmp_path / "b.docx", ok=True,
        revisions=3, seconds=4.0, timing_exact=False,
    )
    assert wr.report_pairs([batched]) == 0


def test_batched_redline_never_hands_the_user_s_folders_to_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Both batch passes sweep only the staging directories this run created.

    The serial path was fixed first and this one was missed: `recycle_paths`
    still carried `folder_a` and `folder_b`, which are `--a` and `--b`. Word
    opens the staged copy, never the original, so a `~$` file in either of those
    is another Word's owner file and removing it unlocks a stranger's document.
    """
    monkeypatch.setattr(wp, "CONTAINER_TMP", tmp_path / "container")
    a = _folder(tmp_path / "a", "deal.docx")
    b = _folder(tmp_path / "b", "deal.docx")
    seen: list[tuple[Path, ...]] = []

    def fake_resume(script, rows, root, **kw):
        seen.append(tuple(kw["recycle_paths"]))
        for row in rows:
            out = Path(row[-1])
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(b"PK" if out.suffix == ".docx" else b"%PDF")
        return {row[0]: (True, "5" if script is wr._COMPARE_BATCH else "") for row in rows}

    monkeypatch.setattr(wr, "run_batch_with_resume", fake_resume)
    session = _verified_session()
    monkeypatch.setattr(session, "warm", lambda: True)
    monkeypatch.setattr(session, "quit_if_ours", lambda: None)

    wr.redline_folders(a, b, tmp_path / "out", session=session, one_osascript=True)

    assert len(seen) == 2, "compare pass and pdf pass both report their cleanup scope"
    for paths in seen:
        assert a not in paths, f"folder A was handed to cleanup: {paths}"
        assert b not in paths, f"folder B was handed to cleanup: {paths}"


def test_redline_refuses_to_run_with_documents_already_open(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Redlining requires Word to hold only our documents, and the flag cannot waive it.

    The compare identifies its result by exclusion: it walks `document i` and
    takes the one whose name is not the base's (§14.1's fix). That is sound
    exactly when every open document is ours. With a human's document open, the
    walk can select *their* document and save it as the redline — a wrong
    output, not merely a lost one. `--allow-open-docs` relaxes a precondition
    this script's correctness depends on, so it is refused here rather than
    honoured.
    """
    session = _verified_session()
    monkeypatch.setattr(wp.WordSession, "available", staticmethod(lambda: True))
    monkeypatch.setattr(session, "warm", lambda: True)
    monkeypatch.setattr(session, "open_document_count", lambda: 2)

    # Default closes every document and leaves Word running, so this is not a refusal.
    assert wr.redline_preflight(session, allow_open_docs=True) == ""
    reason = wr.redline_preflight(session, allow_open_docs=True, close_documents=False)
    assert reason, "--do-not-close must still refuse while a foreign document is open"
    assert "compare" in reason.lower() or "identif" in reason.lower()
    assert session.started_clean is False


def test_redline_serial_replays_the_failure_streak_after_recycling(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Same gap as the PDF path: a recycle invalidates the failures that caused it."""
    monkeypatch.setattr(wp, "CONTAINER_TMP", tmp_path / "container")
    a = _folder(tmp_path / "a", "poison.docx", "healthy-a.docx", "healthy-b.docx")
    b = _folder(tmp_path / "b", "poison.docx", "healthy-a.docx", "healthy-b.docx")

    seen: list[str] = []

    def fake_one(base, revision, outputs, **kw):
        seen.append(base.name)
        bad = "poison" in base.name or seen.count(base.name) == 1
        if bad:
            return wr.PairResult(base=base, revision=revision, error="base loaded empty")
        outputs.pdf.parent.mkdir(parents=True, exist_ok=True)
        outputs.pdf.write_bytes(b"%PDF")
        return wr.PairResult(base=base, revision=revision, pdf=outputs.pdf, ok=True)

    monkeypatch.setattr(wr, "_redline_one", fake_one)
    monkeypatch.setattr(wr, "recover_after_failure", lambda s, *f, **kw: True)
    session = _verified_session()
    monkeypatch.setattr(session, "warm", lambda: True)
    monkeypatch.setattr(session, "quit_if_ours", lambda: None)
    monkeypatch.setattr(session, "recycle", lambda *f: True)

    results = wr.redline_folders(a, b, tmp_path / "out", session=session, one_osascript=False)
    by_name = {r.base.name: r for r in results}

    assert by_name["healthy-a.docx"].ok
    assert by_name["healthy-b.docx"].ok
    assert not by_name["poison.docx"].ok


# ─── the API path must carry the precondition, not just the CLI ──────────────


def test_redline_folders_refuses_a_session_never_checked_against_word(
    tmp_path: Path, monkeypatch
) -> None:
    """`redline_preflight` guarded `main()`, and nothing else.

    `WordSession.started_clean` defaults to **True**, so a fresh session claims
    a clean Word without ever having asked it. `redline_folders()` took that
    claim at face value and went straight to `_COMPARE` / `_COMPARE_BATCH`,
    both of which run `close every document saving no` and identify the result
    by exclusion. Importing the module and calling the function was therefore
    enough to close a person's documents and save theirs as the redline --
    exactly the failure `redline_preflight`'s own docstring says this pair
    exists to prevent.
    """
    a, b = tmp_path / "a", tmp_path / "b"
    _touch(a / "deal.docx")
    _touch(b / "deal.docx")
    monkeypatch.setattr(wp, "CONTAINER_TMP", tmp_path / "container")

    ran: list[str] = []
    monkeypatch.setattr(wr, "osa", lambda *args, **kw: ran.append("osa") or (0, "", ""))
    monkeypatch.setattr(
        wr, "compare_pair", lambda *a, **k: ran.append("compare") or (0, "")
    )

    session = wr.WordSession()  # never preflighted
    results = wr.redline_folders(a, b, tmp_path / "out", session=session)

    assert ran == [], f"reached Word without a verified session: {ran}"
    assert results and all(r.error for r in results)
    assert any("preflight" in (r.error or "").lower() for r in results), results


def test_redline_folders_refuses_when_word_holds_foreign_documents(
    tmp_path: Path, monkeypatch
) -> None:
    """The same guard, reached through a session that was checked and failed."""
    a, b = tmp_path / "a", tmp_path / "b"
    _touch(a / "deal.docx")
    _touch(b / "deal.docx")
    monkeypatch.setattr(wp, "CONTAINER_TMP", tmp_path / "container")

    ran: list[str] = []
    monkeypatch.setattr(wr, "osa", lambda *args, **kw: ran.append("osa") or (0, "", ""))

    session = wr.WordSession()
    session.preflighted = True
    session.started_clean = False  # Word holds someone else's document

    # Default closes those documents. --do-not-close is what still refuses.
    results = wr.redline_folders(
        a, b, tmp_path / "out", session=session, close_documents=False
    )
    assert ran == [], f"reached Word with foreign documents open: {ran}"
    assert results and all(r.error for r in results)


def test_compare_batch_restores_word_alert_state(tmp_path: Path) -> None:
    """`set displayAlerts to false` was never undone.

    `word_pdf`'s module contract promises an already-running Word is left
    exactly as found. Both batch scripts set `displayAlerts` false for the whole
    run and neither read the prior value or put it back, so a run silently
    disarmed Word's prompts for whatever the person did next.
    """
    src = _applescript_code(wr._COMPARE_BATCH)
    assert "set displayAlerts to false" in src
    assert "set priorAlerts to displayAlerts" in src, "prior value never captured"
    # AppleScript has no `finally`, so the restore is a handler called from both
    # the normal exit and the wrapper that catches anything the loop throws.
    assert "on restoreAlerts(priorAlerts)" in src
    assert src.count("my restoreAlerts(priorAlerts)") >= 2, (
        "must restore on the normal path and on the error path"
    )


def test_redline_folders_preflights_the_session_it_creates(
    tmp_path: Path, monkeypatch
) -> None:
    """`session=None` is the convenience path, not a way around the check."""
    a, b = tmp_path / "a", tmp_path / "b"
    _touch(a / "deal.docx")
    _touch(b / "deal.docx")
    monkeypatch.setattr(wp, "CONTAINER_TMP", tmp_path / "container")

    asked: list[bool] = []

    def fake_preflight(session, *, allow_open_docs, close_documents=True):
        asked.append(allow_open_docs)
        return "Word has documents open."

    monkeypatch.setattr(wr, "redline_preflight", fake_preflight)
    ran: list[str] = []
    monkeypatch.setattr(wr, "osa", lambda *a, **k: ran.append("osa") or (0, "", ""))

    results = wr.redline_folders(a, b, tmp_path / "out")
    assert asked == [False], "must preflight, and must not waive --allow-open-docs"
    assert ran == []
    assert results and all("documents open" in (r.error or "") for r in results)


# ─── identity gate ───────────────────────────────────────────────────────────

_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _package(path: Path, *, text: str = "", deleted: str = "", inserted: str = "") -> Path:
    body = ""
    if text:
        body += f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>"
    if deleted:
        body += f"<w:p><w:del><w:r><w:delText>{deleted}</w:delText></w:r></w:del></w:p>"
    if inserted:
        body += f"<w:p><w:ins><w:r><w:t>{inserted}</w:t></w:r></w:ins></w:p>"
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as package:
        package.writestr(
            "word/document.xml",
            f'<w:document xmlns:w="{_W}"><w:body>{body}</w:body></w:document>',
        )
    return path


_BASE_TEXT = "alpha sentence that only the base document carries"
_REV_TEXT = "beta sentence that only the revision document carries"
_FOREIGN = "gamma sentence from a document nobody asked to compare"


@pytest.mark.parametrize("one_osascript", [False, True])
def test_a_redline_saved_from_the_wrong_document_is_not_delivered(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, one_osascript: bool
) -> None:
    """The leftover-document failure: Word saves some other file under this name.

    Both driver paths run the real identity check on what Word saved, drop a
    foreign document, and still deliver the pair that is right.
    """
    monkeypatch.setattr(wr, "_reject_wrong_pair", _REAL_REJECT_WRONG_PAIR)
    monkeypatch.setattr(wp, "CONTAINER_TMP", tmp_path / "container")
    a, b = tmp_path / "a", tmp_path / "b"
    for folder, text in ((a, _BASE_TEXT), (b, _REV_TEXT)):
        _package(folder / "right.docx", text=text)
        _package(folder / "wrong.docx", text=text)

    def save_redline(out: Path) -> None:
        if "wrong" in out.name:
            _package(out, text=_FOREIGN)
        else:
            _package(out, deleted=_BASE_TEXT, inserted=_REV_TEXT)

    def fake_compare(base, rev, out, *, timeout=300.0):
        save_redline(out)
        return True, 2, ""

    def fake_osa(script, *args, timeout=60.0):
        if "manifestPath" not in script:  # serial failure cleanup, not a batch
            return 0, "", ""
        manifest, log = Path(args[0]), Path(args[1])
        rows = [ln.split("\t") for ln in manifest.read_text().splitlines() if ln]
        lines = []
        for row in rows:
            save_redline(Path(row[-1]))
            lines.append(f"[ok]\t{row[0]}\t2")
        lines.append(f"[done]\t{len(rows)}\t0")
        log.write_text("\n".join(lines) + "\n")
        return 0, "", ""

    monkeypatch.setattr(wr, "compare_pair", fake_compare)
    monkeypatch.setattr(wp, "osa", fake_osa)
    session = _verified_session()
    monkeypatch.setattr(session, "warm", lambda: True)
    monkeypatch.setattr(session, "recycle", lambda *f: True)
    monkeypatch.setattr(session, "open_document_count", lambda: 0)
    monkeypatch.setattr(session, "quit_if_ours", lambda: None)
    out = tmp_path / "out"

    results = wr.redline_folders(
        a, b, out, emit="docx", session=session, one_osascript=one_osascript
    )

    verdicts = {r.base.name: r for r in results}
    assert verdicts["right.docx"].ok, verdicts["right.docx"].error
    assert not verdicts["wrong.docx"].ok
    assert "missing" in verdicts["wrong.docx"].error
    assert (out / "right__vs__right.docx").exists()
    assert not (out / "wrong__vs__wrong.docx").exists()
