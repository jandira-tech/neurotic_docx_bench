"""Spec for the audit scorecard checker (``scripts/check_audit_scores.py``).

The checker exists because three classes of drift had already happened in the
audit by hand. It had no tests of its own, which is the same gap it was written
to close, so the drift classes are pinned here against synthetic documents
rather than against the real audit (which is expected to stay clean and would
therefore never exercise a failure path).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_audit_scores.py"


def _load():
    spec = importlib.util.spec_from_file_location("check_audit_scores", _SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["check_audit_scores"] = mod
    spec.loader.exec_module(mod)
    return mod


cas = _load()


def _row(name: str, repo: str, comps: list[float], total: float | None = None) -> str:
    total = sum(comps) if total is None else total
    cells = " | ".join(f"{c:.2f}" for c in comps)
    return f"| `{name}` | {repo} | {cells} | **{total:.2f}** | none |"


_SEVEN = [0.50, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50]


def _doc(scorecard: list[str], details: str = "") -> str:
    return "\n".join(
        [
            "# Audit",
            "",
            "| File | repo | C1 | C2 | C3 | C4 | C5 | C6 | C7 | Σ | tests |",
            "|---|---|---|---|---|---|---|---|---|---|---|",
            *scorecard,
            "",
            "## 6. Permission prompts over many files (C4)",
            "",
            "| File | C4 | Rationale |",
            "|---|---|---|",
            details,
            "",
            "## 10. Timeouts",
            "",
        ]
    )


def _check(tmp_path: Path, text: str) -> list[str]:
    p = tmp_path / "audit.md"
    p.write_text(text, encoding="utf-8")
    return cas.check(p)


# ─── the three drift classes the checker was written for ─────────────────────


def test_components_that_do_not_sum_to_the_stated_total_are_caught(
    tmp_path: Path,
) -> None:
    doc = _doc([_row("a.sh", "ndb", _SEVEN, total=9.99)])
    assert any("components sum" in p for p in _check(tmp_path, doc))


def test_rows_out_of_descending_order_are_caught(tmp_path: Path) -> None:
    low = [0.10] * 7
    doc = _doc([_row("a.sh", "ndb", low), _row("b.sh", "ndb", _SEVEN)])
    assert any("order:" in p for p in _check(tmp_path, doc))


def test_detail_row_disagreeing_with_the_scorecard_is_caught(tmp_path: Path) -> None:
    """§8's C6 row for word-convert.sh sat at 0.85 while the scorecard said 0.80."""
    doc = _doc([_row("a.sh", "ndb", _SEVEN)], details="| `a.sh` | 0.85 | why |")
    problems = _check(tmp_path, doc)
    assert any("shows 0.85" in p and "0.5" in p for p in problems)


def test_a_clean_document_reports_nothing(tmp_path: Path) -> None:
    doc = _doc([_row("a.sh", "ndb", _SEVEN)], details="| `a.sh` | 0.50 | why |")
    assert _check(tmp_path, doc) == []


# ─── repository identity ─────────────────────────────────────────────────────


def test_same_script_name_in_two_repos_does_not_overwrite(tmp_path: Path) -> None:
    """`word-open-probe.sh` exists in two repositories with its own scorecard row.

    Keying on the name alone let the second row silently replace the first, so a
    divergence between the two copies could not be detected at all.
    """
    jf = [0.45, 0.40, 0.70, 0.10, 0.50, 0.45, 0.20]
    jr = [0.45, 0.40, 0.70, 0.99, 0.50, 0.45, 0.20]  # C4 diverges
    doc = _doc(
        [_row("p.sh", "jf", jf), _row("p.sh", "jr", jr)],
        details="| `p.sh` ×2 | 0.10 | why |",
    )
    problems = _check(tmp_path, doc)
    assert any("disagree" in p.lower() for p in problems), problems


def test_identical_duplicate_rows_still_validate_against_the_detail(
    tmp_path: Path,
) -> None:
    same = [0.45, 0.40, 0.70, 0.10, 0.50, 0.45, 0.20]
    doc = _doc(
        [_row("p.sh", "jf", same), _row("p.sh", "jr", same)],
        details="| `p.sh` ×2 | 0.10 | why |",
    )
    assert _check(tmp_path, doc) == []


def test_duplicate_rows_are_compared_on_every_criterion_without_a_detail_row(
    tmp_path: Path,
) -> None:
    """Divergence was only caught where a detail row happened to restate it.

    The comparison ran inside the detail-row loop and only looked at that
    section's criterion, so a C1 to C3 disagreement was never examined at all,
    and a C4 to C7 one slipped through whenever no detail row named the script.
    Two copies of one script that have drifted apart are wrong on their own.
    """
    jf = [0.99, 0.40, 0.70, 0.10, 0.50, 0.45, 0.20]
    jr = [0.10, 0.40, 0.70, 0.10, 0.50, 0.45, 0.20]  # C1 diverges
    doc = _doc([_row("p.sh", "jf", jf), _row("p.sh", "jr", jr)])  # no detail rows
    problems = _check(tmp_path, doc)
    assert any("C1" in p and "disagree" in p.lower() for p in problems), problems


# ─── multi-name detail rows ──────────────────────────────────────────────────


def test_multi_name_detail_rows_are_validated(tmp_path: Path) -> None:
    """`| \\`x\\` ×2, \\`y\\` | 0.10 | …` never matched, so those rows were skipped."""
    doc = _doc(
        [_row("x.sh", "ndb", _SEVEN), _row("y.sh", "ndb", [0.10] * 7)],
        details="| `x.sh` ×2, `y.sh` | 0.10 | why |",
    )
    problems = _check(tmp_path, doc)
    # x.sh's C4 is 0.50 in the scorecard but the shared row claims 0.10.
    assert any("x.sh" in p and "shows 0.1" in p for p in problems), problems


def test_aggregate_rows_without_a_backticked_name_are_ignored(tmp_path: Path) -> None:
    """`| family A (6 files) | 0.05 | …` names no script, so there is nothing to check."""
    doc = _doc(
        [_row("x.sh", "ndb", _SEVEN)], details="| family A (6 files) | 0.05 | why |"
    )
    assert _check(tmp_path, doc) == []


def test_scorecard_rows_are_not_mistaken_for_detail_rows(tmp_path: Path) -> None:
    """The scorecard's own rows sit above §6 and have a repo cell, not a score."""
    doc = _doc([_row("x.sh", "ndb", _SEVEN)], details="| `x.sh` | 0.50 | why |")
    assert _check(tmp_path, doc) == []


# ─── the real audit ──────────────────────────────────────────────────────────


def test_the_checked_in_audit_is_clean() -> None:
    audit = Path(__file__).resolve().parents[1] / "docs" / "WORD_DRIVER_AUDIT.md"
    assert cas.check(audit) == []


def test_main_returns_two_without_arguments() -> None:
    assert cas.main([]) == 2


def test_help_flag_prints_usage_instead_of_crashing(capsys) -> None:
    """`--help` treated the flag as a path and raised FileNotFoundError."""
    code = cas.main(["--help"])
    assert code == 0
    assert "Usage:" in capsys.readouterr().out


def test_missing_file_is_reported_not_raised(tmp_path: Path) -> None:
    """A typo'd path in CI should say so, not dump a traceback."""
    missing = tmp_path / "nope.md"
    problems = cas.check(missing)
    assert problems and any("nope.md" in p for p in problems)
    assert any("cannot read" in p.lower() or "no such" in p.lower() for p in problems)


# ─── the checker's own edges ─────────────────────────────────────────────────


def test_a_document_with_no_scorecard_says_so(tmp_path: Path) -> None:
    """A renamed heading or a reformatted table silently parses to nothing.

    Returning `[]` there would report "ok" for a file the checker never read,
    which is worse than a failure: it is a green light for an unchecked doc.
    """
    problems = _check(tmp_path, "# Audit\n\nNo tables here at all.\n")
    assert any("no scorecard rows parsed" in p for p in problems), problems


def test_detail_rows_naming_an_unknown_script_are_skipped(tmp_path: Path) -> None:
    """§6-§9 name scripts the scorecard drops; there is nothing to compare them to."""
    doc = _doc([_row("x.sh", "ndb", _SEVEN)], details="| `absent.sh` | 0.05 | why |")
    assert _check(tmp_path, doc) == []


def test_only_the_out_of_order_adjacent_pair_is_reported(tmp_path: Path) -> None:
    """The scan walks every adjacent pair, so ordered ones must stay quiet."""
    doc = _doc(
        [
            _row("a.sh", "ndb", [0.70] * 7),
            _row("b.sh", "ndb", [0.30] * 7),
            _row("c.sh", "ndb", [0.50] * 7),  # only b→c is out of order
        ]
    )
    order = [p for p in _check(tmp_path, doc) if "order:" in p]
    assert len(order) == 1, order
    assert "b.sh" in order[0] and "c.sh" in order[0]


def test_main_prints_ok_and_returns_zero_for_a_clean_file(
    tmp_path: Path, capsys
) -> None:
    p = tmp_path / "audit.md"
    p.write_text(_doc([_row("a.sh", "ndb", _SEVEN)]), encoding="utf-8")
    assert cas.main([str(p)]) == 0
    assert "ok " in capsys.readouterr().out


def test_main_prints_each_problem_and_returns_one(tmp_path: Path, capsys) -> None:
    p = tmp_path / "audit.md"
    p.write_text(_doc([_row("a.sh", "ndb", _SEVEN, total=9.99)]), encoding="utf-8")
    assert cas.main([str(p)]) == 1
    out = capsys.readouterr().out
    assert "FAIL" in out and "components sum" in out


def test_a_malformed_decimal_is_reported_not_raised(tmp_path: Path) -> None:
    """`[\\d.]+` matches `1.2.3`, and float() then raised through main()."""
    row = _row("a.sh", "ndb", _SEVEN).replace("| 0.50 |", "| 1.2.3 |", 1)
    path = tmp_path / "audit.md"
    path.write_text(_doc([row]))
    problems = cas.check(path)
    assert any("a.sh" in p and "'1.2.3'" in p for p in problems), problems


def test_scores_outside_their_range_are_reported(tmp_path: Path) -> None:
    over = [1.20, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50]
    many = [1.00] * 7
    path = tmp_path / "audit.md"
    path.write_text(_doc([_row("a.sh", "ndb", over), _row("b.sh", "ndb", many, total=7.50)]))
    problems = cas.check(path)
    assert any("a.sh" in p and "C1" in p and "1.2" in p and "[0.00, 1.00]" in p for p in problems)
    assert any("b.sh" in p and "7.5" in p and "[0.00, 7.00]" in p for p in problems)


def test_the_same_script_twice_in_one_repo_is_reported(tmp_path: Path) -> None:
    """Two rows for one (script, repo) cannot both be the score; the second won silently."""
    path = tmp_path / "audit.md"
    path.write_text(_doc([_row("a.sh", "ndb", _SEVEN), _row("a.sh", "ndb", _SEVEN)]))
    problems = cas.check(path)
    assert any("a.sh" in p and "ndb" in p and "twice" in p for p in problems), problems
