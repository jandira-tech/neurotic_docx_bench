"""Spec for ``scripts/grok_run_dedupe.py``: find byte-identical files under a tree and
fold the extra copies into symlinks, moving the bytes aside instead of deleting them."""

from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "grok_run_dedupe.py"


def _load():
    spec = importlib.util.spec_from_file_location("grok_run_dedupe", _SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["grok_run_dedupe"] = mod
    spec.loader.exec_module(mod)
    return mod


dd = _load()


def _tree(tmp_path: Path) -> Path:
    root = tmp_path / "grok_run"
    files = {
        "origin/a.docx": b"same bytes",
        "runs/x/a.docx": b"same bytes",
        "runs/y/a_copy.docx": b"same bytes",
        "runs/y/unique.docx": b"only here",
        "origin/p.pdf": b"pdf twin",
        "origin/sub/p.pdf": b"pdf twin",
        "runs/b.txt": b"loose twin",
        "runs/c/b.txt": b"loose twin",
        "runs/empty1": b"",
        "runs/empty2": b"",
        "runs/.DS_Store": b"finder",
        "other/.DS_Store": b"finder",
    }
    for rel, data in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    (root / "runs" / "link.docx").symlink_to(root / "origin" / "a.docx")
    return root


def test_groups_hold_only_nonempty_regular_files_with_equal_bytes(tmp_path):
    root = _tree(tmp_path)
    groups = dd.duplicate_groups(root)
    got = sorted(sorted(g) for g in groups.values())
    assert got == [
        ["origin/a.docx", "runs/x/a.docx", "runs/y/a_copy.docx"],
        ["origin/p.pdf", "origin/sub/p.pdf"],
        ["runs/b.txt", "runs/c/b.txt"],
    ]


def test_plan_keeps_the_protected_copy_and_never_moves_a_protected_file(tmp_path):
    root = _tree(tmp_path)
    plan = dd.plan(dd.duplicate_groups(root), protected=("origin",))
    moves = {m.path: m.keeper for m in plan.moves}
    assert moves == {
        "runs/x/a.docx": "origin/a.docx",
        "runs/y/a_copy.docx": "origin/a.docx",
        "runs/c/b.txt": "runs/b.txt",
    }
    # both copies of the pdf sit in an origin: reported, left alone
    assert [sorted(g) for g in plan.protected_groups] == [["origin/p.pdf", "origin/sub/p.pdf"]]


def test_protection_matches_whole_path_segments_only():
    assert dd.is_protected("origin/a.docx", ("origin",))
    assert dd.is_protected("origin", ("origin",))
    assert not dd.is_protected("origin_pdf/a.docx", ("origin",))


def test_apply_moves_bytes_to_the_attic_and_leaves_a_relative_symlink(tmp_path):
    root = _tree(tmp_path)
    attic = tmp_path / "attic"
    plan = dd.plan(dd.duplicate_groups(root), protected=("origin",))
    dd.apply(plan, root, attic)
    moved = root / "runs" / "x" / "a.docx"
    assert moved.is_symlink()
    assert not Path(moved.readlink()).is_absolute()
    assert moved.read_bytes() == b"same bytes"
    assert (attic / "runs" / "x" / "a.docx").read_bytes() == b"same bytes"
    rows = list(csv.DictReader(open(attic / "moved.csv")))
    assert {r["path"] for r in rows} == {"runs/x/a.docx", "runs/y/a_copy.docx", "runs/c/b.txt"}
    assert all(r["sha256"] and int(r["bytes"]) > 0 for r in rows)
    # a second scan finds only the protected pair
    again = dd.plan(dd.duplicate_groups(root), protected=("origin",))
    assert again.moves == [] and len(again.protected_groups) == 1


def test_apply_refuses_to_overwrite_an_attic_file(tmp_path):
    root = _tree(tmp_path)
    attic = tmp_path / "attic"
    (attic / "runs" / "x").mkdir(parents=True)
    (attic / "runs" / "x" / "a.docx").write_bytes(b"something else")
    plan = dd.plan(dd.duplicate_groups(root), protected=("origin",))
    try:
        dd.apply(plan, root, attic)
    except dd.DedupeError as exc:
        assert "runs/x/a.docx" in str(exc)
    else:
        raise AssertionError("expected DedupeError")
    assert not (root / "runs" / "x" / "a.docx").is_symlink()


def test_corpus_protection_covers_grok_run_and_the_fixtures_origins(tmp_path):
    protected = dd._corpus_protected(tmp_path / "grok_run")
    assert "wr0928/accepted_tracking/docx" in protected
    assert "_fixtures/word_redlined_fixtures" in protected
    assert not any(p.startswith("grok_run/") or p.startswith("corpus/") for p in protected)
