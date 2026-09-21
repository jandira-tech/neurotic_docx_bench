"""Spec for the redline half of the Word driver pair (``scripts/word_redline.py``).

The pairing, naming, skip and emit rules are pure functions, so they are tested
directly. The Word-facing half is reached through ``osa`` / ``export_pdf``,
both patched, which also pins the argv order the AppleScript is handed.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

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


def _touch(p: Path, body: bytes = b"x") -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(body)
    return p


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


def test_redline_stem_uses_the_shared_name_when_the_pair_shares_one(tmp_path: Path) -> None:
    assert wr.redline_stem(tmp_path / "a" / "deal.docx", tmp_path / "b" / "deal.docx") == "deal"


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
    assert out.pdf == tmp_path / "out" / "deal.pdf"
    assert out.docx is None


def test_plan_outputs_docx_only(tmp_path: Path) -> None:
    out = wr.plan_outputs(
        tmp_path / "a" / "deal.docx",
        tmp_path / "b" / "deal.docx",
        tmp_path / "out",
        None,
        wr.Emit.DOCX,
    )
    assert out.docx == tmp_path / "out" / "deal.docx"
    assert out.pdf is None


def test_plan_outputs_both_can_split_the_destinations(tmp_path: Path) -> None:
    out = wr.plan_outputs(
        tmp_path / "a" / "deal.docx",
        tmp_path / "b" / "deal.docx",
        tmp_path / "pdf",
        tmp_path / "docx",
        wr.Emit.BOTH,
    )
    assert out.pdf == tmp_path / "pdf" / "deal.pdf"
    assert out.docx == tmp_path / "docx" / "deal.docx"


def test_plan_outputs_wants_docx_internally_for_every_mode(tmp_path: Path) -> None:
    """Word only ever yields the comparison as an open document."""
    for emit in (wr.Emit.PDF, wr.Emit.DOCX, wr.Emit.BOTH):
        out = wr.plan_outputs(
            tmp_path / "a.docx", tmp_path / "b.docx", tmp_path / "o", None, emit
        )
        assert out.wanted, emit


def test_should_skip_only_when_every_wanted_output_is_present(tmp_path: Path) -> None:
    pdf = _touch(tmp_path / "out" / "deal.pdf", b"%PDF")
    docx = tmp_path / "out" / "deal.docx"

    assert wr.should_skip(wr.Outputs(docx=None, pdf=pdf), force=False) is True
    assert wr.should_skip(wr.Outputs(docx=docx, pdf=pdf), force=False) is False
    assert wr.should_skip(wr.Outputs(docx=None, pdf=pdf), force=True) is False


def test_should_skip_rejects_a_zero_byte_leftover(tmp_path: Path) -> None:
    pdf = _touch(tmp_path / "out" / "deal.pdf", b"")
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
    """`active document` is still the BASE when compare silently produced nothing."""
    src = wr._COMPARE
    assert "active document" not in src
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
    session = wp.WordSession()
    monkeypatch.setattr(session, "warm", lambda: True)
    monkeypatch.setattr(session, "recycle", lambda *f: True)
    monkeypatch.setattr(session, "quit_if_ours", lambda: None)
    return session, compared, exported


def test_redline_folders_default_writes_pdf_only(tmp_path: Path, stub_word) -> None:
    session, compared, exported = stub_word
    a = _folder(tmp_path / "a", "deal.docx")
    b = _folder(tmp_path / "b", "deal.docx")
    out = tmp_path / "out"

    results = wr.redline_folders(a, b, out, session=session)

    assert len(results) == 1 and results[0].ok
    assert (out / "deal.pdf").exists()
    assert not (out / "deal.docx").exists()
    assert len(compared) == 1 and len(exported) == 1


def test_redline_folders_both_keeps_the_tracked_changes_docx(
    tmp_path: Path, stub_word
) -> None:
    session, _, _ = stub_word
    a = _folder(tmp_path / "a", "deal.docx")
    b = _folder(tmp_path / "b", "deal.docx")
    out = tmp_path / "out"

    wr.redline_folders(a, b, out, emit=wr.Emit.BOTH, session=session)

    assert (out / "deal.pdf").exists()
    assert (out / "deal.docx").read_bytes() == b"PK-redline"


def test_redline_folders_docx_only_never_calls_the_pdf_exporter(
    tmp_path: Path, stub_word
) -> None:
    session, _, exported = stub_word
    a = _folder(tmp_path / "a", "deal.docx")
    b = _folder(tmp_path / "b", "deal.docx")
    out = tmp_path / "out"

    wr.redline_folders(a, b, out, emit=wr.Emit.DOCX, session=session)

    assert exported == []
    assert (out / "deal.docx").exists()
    assert not (out / "deal.pdf").exists()


def test_redline_folders_stages_same_named_sides_apart(tmp_path: Path, stub_word) -> None:
    session, compared, _ = stub_word
    a = _folder(tmp_path / "a", "deal.docx")
    b = _folder(tmp_path / "b", "deal.docx")

    wr.redline_folders(a, b, tmp_path / "out", session=session)

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

    wr.redline_folders(a, b, tmp_path / "out", swap=True, session=session)

    call = compared[0]
    assert call["base_bytes"] == b"BBB"
    assert call["rev_bytes"] == b"AAA"


def test_redline_folders_skips_existing_unless_forced(tmp_path: Path, stub_word) -> None:
    session, compared, _ = stub_word
    a = _folder(tmp_path / "a", "deal.docx")
    b = _folder(tmp_path / "b", "deal.docx")
    out = tmp_path / "out"
    _touch(out / "deal.pdf", b"%PDF")

    results = wr.redline_folders(a, b, out, session=session)
    assert results[0].skipped and results[0].ok and compared == []

    wr.redline_folders(a, b, out, force=True, session=session)
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
    session = wp.WordSession()
    monkeypatch.setattr(session, "warm", lambda: True)
    monkeypatch.setattr(session, "quit_if_ours", lambda: None)
    recycled: list[tuple] = []
    monkeypatch.setattr(session, "recycle", lambda *f: recycled.append(f) or True)

    results = wr.redline_folders(a, b, tmp_path / "out", session=session)

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
    session = wp.WordSession()
    monkeypatch.setattr(session, "warm", lambda: True)
    monkeypatch.setattr(session, "quit_if_ours", lambda: None)

    results = wr.redline_folders(a, b, tmp_path / "out", session=session)
    assert results[0].ok is True
    assert results[0].revisions == 0


def test_redline_folders_cross_mode_runs_every_combination(tmp_path: Path, stub_word) -> None:
    session, compared, _ = stub_word
    a = _folder(tmp_path / "a", "one.docx", "two.docx")
    b = _folder(tmp_path / "b", "x.docx")

    results = wr.redline_folders(a, b, tmp_path / "out", cross=True, session=session)

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
    monkeypatch.setattr(wr, "preflight", lambda s, *, allow_open_docs: "Word is busy")

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
    monkeypatch.setattr(wr, "preflight", lambda s, *, allow_open_docs: "Word is busy")

    result = CliRunner().invoke(wr.app, ["--a", str(a), "--b", str(b), "--emit", "docx"])
    assert "Best for printing" not in result.output


def test_cli_runs_the_batch_and_returns_the_report_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from typer.testing import CliRunner

    a = _folder(tmp_path / "a", "deal.docx")
    b = _folder(tmp_path / "b", "deal.docx")
    seen: dict[str, object] = {}

    monkeypatch.setattr(wr, "preflight", lambda s, *, allow_open_docs: "")
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
