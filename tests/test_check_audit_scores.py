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
