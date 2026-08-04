"""Pairing spec for the superdoc Word-redline subcorpus (plan Chapter 2.2).

The generator is a pure function from (pool inventory, seed) -> manifest rows, so
everything here runs without touching the fixture repo or Microsoft Word.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_superdoc_pairs.py"


def _load():
    spec = importlib.util.spec_from_file_location("build_superdoc_pairs", _SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["build_superdoc_pairs"] = mod
    spec.loader.exec_module(mod)
    return mod


bsp = _load()


def _pool(n: int = 40, bucket: str = "behavior") -> list:
    """Synthetic pool: n files in one bucket, each with a distinct sha."""
    return [
        bsp.PoolFile(relative_path=f"{bucket}/doc-{i:03d}.docx", sha256=f"{i:064x}", size=100 + i)
        for i in range(n)
    ]


# --------------------------------------------------------------------------- #
# flat_stem — the bench's pair identity depends on these names being safe
# --------------------------------------------------------------------------- #


def test_flat_stem_prefixes_bucket_and_sanitizes():
    stem = bsp.flat_stem("super-editor/Hello docx world.docx")
    assert stem.startswith("super_editor__Hello_docx_world_")


def test_flat_stem_disambiguates_same_basename_in_different_buckets():
    a = bsp.flat_stem("evals/numwords.docx")
    b = bsp.flat_stem("super-editor/numwords.docx")
    assert a != b


def test_flat_stem_disambiguates_hyphen_vs_underscore_variants():
    """Regression: sanitizing `-` and `_` to the same char collapsed
    `sd-1494-table-left-indent.docx` and `sd_1494_table_left_indent.docx` — both
    real, both in `super-editor` — onto one staged file, so one document
    silently stood in for the other in every pair that used it."""
    a = bsp.flat_stem("super-editor/sd-1494-table-left-indent.docx")
    b = bsp.flat_stem("super-editor/sd_1494_table_left_indent.docx")
    assert a != b


def test_flat_stem_stays_within_the_length_cap():
    rel = "super-editor/h_f-normal-odd-even-unchecked-first-pg-unchecked.docx"
    stem = bsp.flat_stem(rel)
    assert len(stem) <= bsp.MAX_STEM
    # the suffix is derived from the path, not the content, so two byte-identical
    # files at different paths still get different stems.
    other = bsp.flat_stem("super-editor/h_f-normal-odd-even-unchecked-first-pg-uncheckedX.docx")
    assert stem != other


def test_flat_stem_is_injective_over_the_real_pool_inventory():
    """The end-to-end guarantee: every distinct source path gets a distinct
    staged filename, case-insensitively (the scorer lower-cases keys)."""
    csv_path = Path(__file__).resolve().parents[1] / "plans" / "superdoc-source-pool.sha256.csv"
    rels = [
        line.split(",")[0]
        for line in csv_path.read_text().splitlines()[1:]
        if line.strip()
    ]
    stems = [bsp.flat_stem(r).lower() for r in rels]
    assert len(set(stems)) == len(stems)


def test_flat_stem_never_ends_with_reserved_markers():
    """``_word`` / ``_redline`` suffixes are eaten by pipeline.oracle_pair_key /
    redline_key, which would silently mis-key the oracle PDF."""
    for rel in ("behavior/foo_word.docx", "behavior/bar_redline.docx", "behavior/baz_WORD.docx"):
        stem = bsp.flat_stem(rel)
        assert not stem.lower().endswith("_word")
        assert not stem.lower().endswith("_redline")


def test_flat_stem_is_pure_ascii_wordchars():
    stem = bsp.flat_stem("super-editor/Google Docs Originated comments & TCs.docx")
    assert all(c.isalnum() or c == "_" for c in stem), stem


# --------------------------------------------------------------------------- #
# inventory — exclusions the pairing algorithm must honor
# --------------------------------------------------------------------------- #


def test_inventory_excludes_encrypted_and_lock_files(tmp_path: Path):
    (tmp_path / "behavior").mkdir()
    (tmp_path / "encryption").mkdir()
    (tmp_path / "behavior" / "a.docx").write_bytes(b"a")
    (tmp_path / "behavior" / "~$a.docx").write_bytes(b"lock")
    (tmp_path / "encryption" / "encrypted-hello.docx").write_bytes(b"e")

    pool = bsp.inventory(tmp_path)
    rels = [p.relative_path for p in pool]
    assert rels == ["behavior/a.docx"]


def test_inventory_is_path_sorted_and_hashes_content(tmp_path: Path):
    (tmp_path / "behavior").mkdir()
    for name in ("c.docx", "a.docx", "b.docx"):
        (tmp_path / "behavior" / name).write_bytes(name.encode())
    pool = bsp.inventory(tmp_path)
    assert [p.relative_path for p in pool] == [
        "behavior/a.docx",
        "behavior/b.docx",
        "behavior/c.docx",
    ]
    assert len({p.sha256 for p in pool}) == 3


# --------------------------------------------------------------------------- #
# build_pairs — the 400-pair spec
# --------------------------------------------------------------------------- #


def test_build_pairs_returns_exactly_the_requested_count():
    assert len(bsp.build_pairs(_pool(40), target=400)) == 400


def test_build_pairs_is_deterministic():
    a = bsp.build_pairs(_pool(40), target=400)
    b = bsp.build_pairs(_pool(40), target=400)
    assert a == b


def test_build_pairs_never_pairs_identical_content():
    """Word compare of byte-identical documents yields an empty redline."""
    pool = _pool(30)
    # force a duplicate-sha cluster, as the real pool has (6 duplicate shas)
    pool[5] = bsp.PoolFile(pool[5].relative_path, pool[4].sha256, pool[5].size)
    pool[6] = bsp.PoolFile(pool[6].relative_path, pool[4].sha256, pool[6].size)
    for p in bsp.build_pairs(pool, target=200):
        assert p.base.sha256 != p.next.sha256


def test_build_pairs_never_pairs_a_file_with_itself():
    for p in bsp.build_pairs(_pool(30), target=200):
        assert p.base.relative_path != p.next.relative_path


def test_build_pairs_emits_no_duplicate_ordered_pairs():
    pairs = bsp.build_pairs(_pool(40), target=400)
    keys = [(p.base.relative_path, p.next.relative_path) for p in pairs]
    assert len(set(keys)) == len(keys)


def test_build_pairs_starts_with_same_bucket_chain_neighbours():
    """Path-sorted neighbours inside a bucket are related fixtures -> realistic diffs."""
    pool = _pool(6, "behavior") + _pool(6, "evals")
    pool.sort(key=lambda p: p.relative_path)
    pairs = bsp.build_pairs(pool, target=20)
    chain = pairs[:10]
    for p in chain:
        assert p.base.relative_path.split("/")[0] == p.next.relative_path.split("/")[0]
        assert p.kind == "chain"
    assert {p.kind for p in pairs[10:]} == {"cross"}


def test_build_pairs_pair_keys_are_unique_case_insensitively():
    """pipeline.redline_key lower-cases; a case-only clash is a hard scorer error."""
    pairs = bsp.build_pairs(_pool(40), target=400)
    keys = [f"{bsp.flat_stem(p.base.relative_path)}_{bsp.flat_stem(p.next.relative_path)}".lower() for p in pairs]
    assert len(set(keys)) == len(keys)


def test_drop_unreadable_removes_sources_word_cannot_open():
    """A document Word loads as empty doesn't just fail its own pair — it leaves
    Word returning empty documents for every LATER open in the session, silently.
    They have to leave the pool, not merely be retried."""
    pool = _pool(10)
    bad = {bsp.flat_stem(pool[3].relative_path) + ".docx"}
    kept = bsp.drop_unreadable(pool, bad)
    assert len(kept) == 9
    assert all(f"{bsp.flat_stem(p.relative_path)}.docx" not in bad for p in kept)


def test_drop_unreadable_is_a_no_op_for_an_empty_list():
    pool = _pool(10)
    assert bsp.drop_unreadable(pool, set()) == pool


def test_excluded_sources_never_appear_in_any_pair():
    pool = _pool(30)
    bad = {bsp.flat_stem(p.relative_path) + ".docx" for p in pool[:5]}
    pairs = bsp.build_pairs(bsp.drop_unreadable(pool, bad), target=200)
    used = {p.base.relative_path for p in pairs} | {p.next.relative_path for p in pairs}
    assert not any(f"{bsp.flat_stem(r)}.docx" in bad for r in used)


def test_build_pairs_raises_when_pool_cannot_supply_the_target():
    with pytest.raises(ValueError, match="cannot reach"):
        bsp.build_pairs(_pool(3), target=400)


# --------------------------------------------------------------------------- #
# manifest rows — schema the bench actually consumes
# --------------------------------------------------------------------------- #


def test_mapping_rows_match_the_bench_manifest_schema():
    """generate-native-redlines.ts parseManifest reads `base` / `next`; the scorer
    keys oracles on `<base>_<next>_redline.pdf`."""
    rows = bsp.mapping_rows(bsp.build_pairs(_pool(40), target=400))
    assert len(rows) == 400
    assert list(rows[0]) == bsp.MAPPING_FIELDS
    for r in rows:
        assert r["docx_source_base"] == f"{r['base']}.docx"
        assert r["docx_source_next"] == f"{r['next']}.docx"
        assert r["redline_docx"] == f"{r['base']}_{r['next']}_redline.docx"
        assert r["pdf_redline"] == f"{r['base']}_{r['next']}_redline.pdf"
        assert r["pair_stem"] == f"{r['base']}_{r['next']}"


def test_provenance_rows_carry_three_shas_and_a_status():
    rows = bsp.provenance_rows(bsp.build_pairs(_pool(40), target=400))
    assert list(rows[0]) == bsp.PROVENANCE_FIELDS
    r = rows[0]
    assert r["base_sha256"] and r["next_sha256"]
    assert r["redline_sha256"] == ""  # filled in after Word runs
    assert r["status"] == "pending"
    assert r["base_rel"].endswith(".docx")


def test_output_filenames_stay_under_the_macos_255_byte_cap():
    """`<base>_<next>_<tool>_redline.docx` for the longest tool name must fit."""
    longest_tool = "jubarte-final-lossless"
    rows = bsp.mapping_rows(bsp.build_pairs(_pool(40), target=400))
    for r in rows:
        name = f"{r['base']}_{r['next']}_{longest_tool}_redline.docx"
        assert len(name.encode()) < 255, name
