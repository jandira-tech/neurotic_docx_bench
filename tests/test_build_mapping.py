"""corpus/word_based/build_mapping.py — centralized mapping CSV builder.

This is a standalone script (top-level code, no ``if __name__ == "__main__"`` guard)
that derives its ``BASE`` directory from its own ``__file__`` and enumerates five
sibling corpus folders. To exercise its logic (stem extraction, base/next splitting,
origin classification, missing-field detection) without touching the real
``corpus/word_based/`` tree, each test copies the script's source into an isolated
``tmp_path``, builds a synthetic sibling-folder layout there, and runs it as a
subprocess.
"""

from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_SRC = (REPO_ROOT / "corpus" / "word_based" / "build_mapping.py").read_text()

_DIR_NAMES = {
    "source": "docx_source",
    "redline": "docx_redlines_word",
    "accepted": "docx_accepted_word",
    "pdf_red": "pdf_redlines_word",
    "pdf_acc": "pdf_accepted_word",
    # Randomized chain corpus (file_N → file_M); oracle PDFs live one level down.
    "rand_source": "docx_source_randomized",
    "rand_redline": "docx_redlines_randomized",
    "rand_pdf": "pdf_redlines_randomized/pdf",
}


def _write_script(tmp_path: Path) -> Path:
    script = tmp_path / "build_mapping.py"
    script.write_text(SCRIPT_SRC)
    return script


def _run(tmp_path: Path, create_dirs: bool = True, **files: list[str]):
    """Build a synthetic corpus tree next to a copy of the script and run it.

    ``files`` maps the short keys in ``_DIR_NAMES`` to lists of filenames to create
    (empty files — the script only inspects names, never contents).
    Returns ``(rows, stdout)`` where ``rows`` are the parsed CSV records.
    """
    script = _write_script(tmp_path)
    if create_dirs:
        for key, dirname in _DIR_NAMES.items():
            d = tmp_path / dirname
            d.mkdir(parents=True)
            for name in files.get(key, []):
                (d / name).write_bytes(b"")

    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr

    csv_path = tmp_path / "centralized_mapping.csv"
    rows: list[dict[str, str]] = []
    if csv_path.exists():
        with csv_path.open(newline="") as f:
            rows = list(csv.DictReader(f))
    return rows, proc.stdout


def _row(rows: list[dict[str, str]], stem: str) -> dict[str, str]:
    matches = [r for r in rows if r["pair_stem"] == stem]
    assert len(matches) == 1, f"expected exactly one row for {stem!r}, got {matches}"
    return matches[0]


def _trailing_count(stdout: str, label: str) -> str | None:
    """Grab the last whitespace-separated token on the line containing ``label``.

    Used instead of matching the summary lines' exact column padding.
    """
    for line in stdout.splitlines():
        if label in line:
            return line.strip().split()[-1]
    return None


# --------------------------------------------------------------------------- #
# Empty / absent corpus
# --------------------------------------------------------------------------- #


def test_no_corpus_files_produces_empty_csv(tmp_path):
    rows, stdout = _run(tmp_path)
    assert rows == []
    assert "Rows with missing items: 0 / 0" in stdout
    assert "No missing source files" in stdout


def test_missing_directories_handled_gracefully(tmp_path):
    """None of the five sibling folders exist at all (not even empty) — ``list_dir``
    must guard with ``Path.is_dir()`` rather than raising on ``os.listdir``.
    """
    rows, stdout = _run(tmp_path, create_dirs=False)
    assert rows == []
    assert "Total unique pairs:" in stdout


# --------------------------------------------------------------------------- #
# Happy path: a fully-populated pair
# --------------------------------------------------------------------------- #


def test_full_pair_both_origin_no_missing(tmp_path):
    # Accepted docx carry the REDLINE names (they are the redline with all
    # changes applied) — the old `_word_redline_accepted.docx` suffix matched
    # zero real files.
    rows, _ = _run(
        tmp_path,
        source=["base.docx", "next.docx"],
        redline=["base_next_redline.docx"],
        accepted=["base_next_redline.docx"],
        pdf_red=["base_next_redline.pdf"],
        pdf_acc=["base_next_word_redline_accepted.pdf"],
    )
    row = _row(rows, "base_next")
    assert row["base"] == "base"
    assert row["next"] == "next"
    assert row["origin"] == "both"
    assert row["docx_source_base"] == "base.docx"
    assert row["docx_source_next"] == "next.docx"
    assert row["redline_docx"] == "base_next_redline.docx"
    assert row["redline_docx_word"] == ""
    assert row["accepted_docx"] == "base_next_redline.docx"
    assert row["pdf_redline"] == "base_next_redline.pdf"
    assert row["pdf_accepted"] == "base_next_word_redline_accepted.pdf"
    assert row["missing"] == ""


def test_csv_header_matches_expected_fields(tmp_path):
    rows, _ = _run(
        tmp_path,
        source=["base.docx", "next.docx"],
        redline=["base_next_redline.docx"],
    )
    assert list(rows[0].keys()) == [
        "pair_stem", "base", "next", "origin",
        "docx_source_base", "docx_source_next",
        "redline_docx", "redline_docx_word",
        "accepted_docx", "pdf_redline", "pdf_accepted", "missing",
    ]


# --------------------------------------------------------------------------- #
# extract_stems suffix priority
# --------------------------------------------------------------------------- #


def test_word_redline_suffix_takes_priority_over_plain_redline(tmp_path):
    """``_word_redline.docx`` is checked before the shorter ``_redline.docx`` — a file
    ending in the former must have the *longer* suffix stripped, not the shorter one
    (both are literal suffixes of ``..._word_redline.docx``).
    """
    rows, _ = _run(tmp_path, redline=["doc_word_redline.docx"])
    row = _row(rows, "doc")
    assert row["redline_docx_word"] == "doc_word_redline.docx"
    assert row["redline_docx"] == ""


def test_plain_redline_suffix_used_when_no_word_variant(tmp_path):
    rows, _ = _run(tmp_path, redline=["doc_redline.docx"])
    row = _row(rows, "doc")
    assert row["redline_docx"] == "doc_redline.docx"
    assert row["redline_docx_word"] == ""


# --------------------------------------------------------------------------- #
# split_core: base/next resolution
# --------------------------------------------------------------------------- #


def test_split_core_prefers_longest_source_suffix_match(tmp_path):
    """Both "next" and "sub_next" are registered source stems and both match as a
    suffix of "foo_sub_next"; the longer one ("sub_next") must win over the shorter.
    """
    rows, _ = _run(
        tmp_path,
        source=["foo.docx", "next.docx", "sub_next.docx"],
        redline=["foo_sub_next_redline.docx"],
        accepted=["foo_sub_next_redline.docx"],
        pdf_red=["foo_sub_next_redline.pdf"],
        pdf_acc=["foo_sub_next_word_redline_accepted.pdf"],
    )
    row = _row(rows, "foo_sub_next")
    assert row["base"] == "foo"
    assert row["next"] == "sub_next"
    assert row["missing"] == ""


def test_split_core_falls_back_to_prefix_match(tmp_path):
    """When no registered source stem matches as a *suffix*, split_core falls back to
    checking whether the stem *starts with* a known source name.
    """
    rows, _ = _run(
        tmp_path,
        source=["foo.docx"],
        redline=["foo_c_redline.docx"],
    )
    row = _row(rows, "foo_c")
    assert row["base"] == "foo"
    assert row["next"] == "c"


def test_find_source_case_insensitive_fallback(tmp_path):
    rows, _ = _run(
        tmp_path,
        source=["Base.docx", "next.docx"],
        redline=["base_next_redline.docx"],
    )
    row = _row(rows, "base_next")
    assert row["base"] == "base"
    assert row["docx_source_base"] == "Base.docx"
    assert row["docx_source_next"] == "next.docx"


# --------------------------------------------------------------------------- #
# Missing-field detection
# --------------------------------------------------------------------------- #


def test_missing_flags_without_any_source_docx(tmp_path):
    """With no docx_source at all, split_core has nothing to match against and the
    whole stem lands in ``next``; only ``source_next`` (never ``source_base``, since
    ``base`` is the empty string) is flagged as missing.
    """
    rows, _ = _run(tmp_path, redline=["alpha_beta_redline.docx"])
    row = _row(rows, "alpha_beta")
    assert row["base"] == ""
    assert row["next"] == "alpha_beta"
    missing = row["missing"].split("; ")
    assert "source_next" in missing
    assert "source_base" not in missing
    assert "accepted_docx" in missing
    assert "pdf_redline" in missing
    assert "pdf_accepted" in missing


def test_missing_docx_source_base_is_prefixed(tmp_path):
    rows, _ = _run(
        tmp_path,
        source=["bb.docx"],
        redline=["aa_bb_redline.docx"],
    )
    row = _row(rows, "aa_bb")
    assert row["base"] == "aa"
    assert row["docx_source_base"] == "MISSING:aa.docx"
    assert "source_base" in row["missing"].split("; ")
    assert row["docx_source_next"] == "bb.docx"


def test_missing_accepted_and_pdfs_only(tmp_path):
    """Sources resolve cleanly and the redline docx exists, but nothing downstream of
    it (accepted docx, both PDFs) was generated.
    """
    rows, _ = _run(
        tmp_path,
        source=["cc.docx", "dd.docx"],
        redline=["cc_dd_redline.docx"],
    )
    row = _row(rows, "cc_dd")
    assert row["missing"] == "accepted_docx; pdf_redline; pdf_accepted"


# --------------------------------------------------------------------------- #
# origin classification
# --------------------------------------------------------------------------- #


def test_origin_classification_all_three_kinds(tmp_path):
    rows, _ = _run(
        tmp_path,
        source=["aa.docx", "bb.docx", "cc.docx", "dd.docx", "ee.docx", "ff.docx"],
        redline=["aa_bb_redline.docx", "cc_dd_redline.docx"],
        accepted=["aa_bb_redline.docx", "ee_ff_redline.docx"],
    )
    assert _row(rows, "aa_bb")["origin"] == "both"
    assert _row(rows, "cc_dd")["origin"] == "redline_only"
    assert _row(rows, "ee_ff")["origin"] == "accepted_only"


# --------------------------------------------------------------------------- #
# Summary printed to stdout
# --------------------------------------------------------------------------- #


def test_stdout_reports_inventory_and_summary_counts(tmp_path):
    rows, stdout = _run(
        tmp_path,
        source=["base.docx", "next.docx"],
        redline=["base_next_redline.docx"],
        accepted=["base_next_redline.docx"],
        pdf_red=["base_next_redline.pdf"],
        pdf_acc=["base_next_word_redline_accepted.pdf"],
    )
    assert len(rows) == 1
    assert _trailing_count(stdout, "source .docx") == "2"
    assert _trailing_count(stdout, "redline .docx") == "1"
    assert _trailing_count(stdout, "accepted .docx") == "1"
    assert _trailing_count(stdout, "pdf_red .pdf") == "1"
    assert _trailing_count(stdout, "pdf_acc .pdf") == "1"
    assert _trailing_count(stdout, "Total unique pairs:") == "1"
    assert _trailing_count(stdout, "Both red+accepted:") == "1"
    assert "CSV:" in stdout


# --------------------------------------------------------------------------- #
# Additional edge cases (both-variant redline docs, non-matching stems, and
# irrelevant-extension filtering)
# --------------------------------------------------------------------------- #


def test_both_redline_variants_present_for_same_stem(tmp_path):
    """When a pair stem has *both* a ``_redline.docx`` and a ``_word_redline.docx``
    file, both must be reported (they are not mutually exclusive at the per-row
    level — only ``extract_stems`` dedupes the stem set itself), and the row must
    not be flagged as missing a ``redline_docx``.
    """
    rows, _ = _run(
        tmp_path,
        source=["base.docx", "next.docx"],
        redline=["base_next_redline.docx", "base_next_word_redline.docx"],
        accepted=["base_next_word_redline_accepted.docx"],
        pdf_red=["base_next_redline.pdf"],
        pdf_acc=["base_next_word_redline_accepted.pdf"],
    )
    row = _row(rows, "base_next")
    assert row["redline_docx"] == "base_next_redline.docx"
    assert row["redline_docx_word"] == "base_next_word_redline.docx"
    assert "redline_docx" not in row["missing"].split("; ")


def test_stem_exactly_matches_a_registered_source_name(tmp_path):
    """``split_core`` requires a separating underscore both for the suffix check
    (``cl.endswith("_" + ss)``) and the prefix fallback (``cl.startswith(ss + "_")``).
    A pair stem that is *exactly* equal to a registered source stem (no separator on
    either side) must therefore match neither branch and fall through to the
    ``("", core)`` default — the whole stem lands in ``next`` with no base resolved.
    """
    rows, _ = _run(
        tmp_path,
        source=["solo.docx"],
        redline=["solo_redline.docx"],
    )
    row = _row(rows, "solo")
    assert row["base"] == ""
    assert row["next"] == "solo"
    # "next" resolves via find_source since "solo.docx" exists directly.
    assert row["docx_source_next"] == "solo.docx"
    assert row["docx_source_base"] == ""
    assert "source_base" not in row["missing"].split("; ")


def test_accepted_word_variant_preferred_when_both_exist(tmp_path):
    """When docx_accepted_word holds both name variants for one stem, the
    `_word_redline` (Word-capture, provenance-matching) variant wins."""
    rows, _ = _run(
        tmp_path,
        source=["base.docx", "next.docx"],
        redline=["base_next_redline.docx"],
        accepted=["base_next_redline.docx", "base_next_word_redline.docx"],
    )
    row = _row(rows, "base_next")
    assert row["accepted_docx"] == "base_next_word_redline.docx"
    assert row["origin"] == "both"


def test_pdf_redline_word_variant_fallback(tmp_path):
    """43 real pairs only exist as `_word_redline.pdf` captures — the mapping must
    record the file that exists, never a stale `_redline.pdf` guess."""
    rows, _ = _run(
        tmp_path,
        source=["base.docx", "next.docx"],
        redline=["base_next_redline.docx"],
        pdf_red=["base_next_word_redline.pdf"],
    )
    row = _row(rows, "base_next")
    assert row["pdf_redline"] == "base_next_word_redline.pdf"
    assert "pdf_redline" not in row["missing"].split("; ")


def test_pdf_redline_word_variant_preferred_over_plain(tmp_path):
    rows, _ = _run(
        tmp_path,
        source=["base.docx", "next.docx"],
        redline=["base_next_redline.docx"],
        pdf_red=["base_next_redline.pdf", "base_next_word_redline.pdf"],
    )
    row = _row(rows, "base_next")
    assert row["pdf_redline"] == "base_next_word_redline.pdf"


# --------------------------------------------------------------------------- #
# Randomized chain corpus (second CSV)
# --------------------------------------------------------------------------- #


def _rand_rows(tmp_path: Path) -> list[dict[str, str]]:
    csv_path = tmp_path / "centralized_mapping_randomized.csv"
    assert csv_path.exists(), "randomized CSV must always be written"
    with csv_path.open(newline="") as f:
        return list(csv.DictReader(f))


def test_randomized_corpus_written_and_classified(tmp_path):
    rows, stdout = _run(
        tmp_path,
        rand_source=["file_1.docx", "file_2.docx"],
        rand_redline=["file_1_file_2_redline.docx"],
        rand_pdf=["file_1_file_2_redline.pdf"],
    )
    assert rows == []  # named-corpus CSV untouched by randomized inputs
    rand = _rand_rows(tmp_path)
    assert len(rand) == 1
    row = rand[0]
    assert row["pair_stem"] == "file_1_file_2"
    assert row["base"] == "file_1"
    assert row["next"] == "file_2"
    assert row["origin"] == "randomized_chain"
    assert row["redline_docx"] == "file_1_file_2_redline.docx"
    assert row["pdf_redline"] == "file_1_file_2_redline.pdf"
    # No accepted artifacts exist for the randomized chain — always MISSING.
    assert row["accepted_docx"] == "MISSING"
    assert row["pdf_accepted"] == "MISSING"
    assert "RANDOMIZED CHAIN CORPUS" in stdout


def test_randomized_corpus_missing_oracle_pdf_flagged(tmp_path):
    _run(
        tmp_path,
        rand_source=["file_1.docx", "file_2.docx"],
        rand_redline=["file_1_file_2_redline.docx"],
    )
    row = _rand_rows(tmp_path)[0]
    assert row["pdf_redline"] == "MISSING"
    assert "pdf_redline" in row["missing"].split("; ")


def test_randomized_corpus_empty_when_no_dirs(tmp_path):
    _run(tmp_path, create_dirs=False)
    assert _rand_rows(tmp_path) == []


def test_non_matching_extensions_are_ignored(tmp_path):
    """Files with an extension other than ``.docx``/``.pdf`` in the source/redline
    folders must not be picked up by the set comprehensions that filter by suffix.
    """
    rows, _ = _run(
        tmp_path,
        source=["base.docx", "next.docx", "base.docx.bak", "readme.txt"],
        redline=["base_next_redline.docx", "base_next_redline.docx.orig"],
    )
    assert len(rows) == 1
    row = _row(rows, "base_next")
    assert row["redline_docx"] == "base_next_redline.docx"
    assert row["docx_source_base"] == "base.docx"
    assert row["docx_source_next"] == "next.docx"
