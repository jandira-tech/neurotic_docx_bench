"""results/bench.jsonl diet (plan Chapter 1.5).

The file reached 103 MB over 203 lines, 90% of it `per_doc` payloads that nothing reads
back. Compaction moves the heavy per-doc payloads of SUPERSEDED lines into
`results/detail/<id_run>.json.gz` and leaves a `detail:` stub, so history is preserved
byte-for-byte in the detail file rather than discarded.
"""

from __future__ import annotations

import gzip
import importlib.util
import json
import sys
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "compact-results.py"


def _load():
    spec = importlib.util.spec_from_file_location("compact_results", _SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["compact_results"] = mod
    spec.loader.exec_module(mod)
    return mod


cr = _load()


def _line(vendor: str, version: str, run_id: str, *, mean: float = 80.0) -> dict:
    return {
        "vendor": vendor,
        "benchmark": "script_redlines",
        "tool_version": version,
        "id_run": run_id,
        "overall_mean": mean,
        "overall_median": mean,
        "itt_mean": mean,
        "itt_median": mean,
        "itt_n_docs": 2,
        "n_docs": 2,
        "corpus_revision": "rev1",
        "timestamp": f"2026-08-0{run_id[-1]}T00:00:00Z",
        "scores": {"a": mean, "b": mean},
        "per_doc": {"a": {"pages": [1, 2, 3]}, "b": {"pages": [4, 5, 6]}},
        "timings": {"a": {"render_s": 1.0}, "b": {"render_s": 2.0}},
    }


def _write(path: Path, lines: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(x) for x in lines) + "\n")


def test_latest_line_per_identity_keeps_its_payload_inline(tmp_path: Path) -> None:
    """Only SUPERSEDED lines are compacted: the current line is what every consumer
    reads, and stubbing it would put a decompress on the hot path for no saving."""
    p = tmp_path / "bench.jsonl"
    _write(p, [_line("v", "1.0", "r1"), _line("v", "1.0", "r2")])
    cr.compact(p, detail_dir=tmp_path / "results" / "detail", root=tmp_path)

    out = [json.loads(x) for x in p.read_text().splitlines()]
    assert "per_doc" not in out[0] and out[0]["detail"]
    assert out[1]["per_doc"], "the newest line for an identity must stay inline"
    assert "detail" not in out[1]


def test_distinct_identities_are_each_kept(tmp_path: Path) -> None:
    """Identity is (vendor, benchmark, tool_version) — a different pin is not a
    supersession, so compacting across pins would stub a line that is still current."""
    p = tmp_path / "bench.jsonl"
    _write(p, [_line("v", "1.0", "r1"), _line("v", "2.0", "r2")])
    cr.compact(p, detail_dir=tmp_path / "results" / "detail", root=tmp_path)

    out = [json.loads(x) for x in p.read_text().splitlines()]
    assert out[0]["per_doc"] and out[1]["per_doc"]


def test_moved_payload_is_recoverable_byte_for_byte(tmp_path: Path) -> None:
    p = tmp_path / "bench.jsonl"
    original = _line("v", "1.0", "r1")
    _write(p, [original, _line("v", "1.0", "r2")])
    cr.compact(p, detail_dir=tmp_path / "results" / "detail", root=tmp_path)

    detail = tmp_path / "results" / "detail" / "r1__script_redlines.json.gz"
    assert detail.is_file()
    with gzip.open(detail, "rt", encoding="utf-8") as fh:
        payload = json.load(fh)
    assert payload["per_doc"] == original["per_doc"]
    assert payload["timings"] == original["timings"]


def test_stub_is_read_transparently(tmp_path: Path) -> None:
    p = tmp_path / "bench.jsonl"
    original = _line("v", "1.0", "r1")
    _write(p, [original, _line("v", "1.0", "r2")])
    cr.compact(p, detail_dir=tmp_path / "results" / "detail", root=tmp_path)

    stub = json.loads(p.read_text().splitlines()[0])
    hydrated = cr.hydrate(stub, root=tmp_path)
    assert hydrated["per_doc"] == original["per_doc"]
    assert hydrated["timings"] == original["timings"]


def test_hydrate_is_a_noop_for_an_uncompacted_line(tmp_path: Path) -> None:
    line = _line("v", "1.0", "r1")
    assert cr.hydrate(line, root=tmp_path) == line


def test_scores_stay_inline(tmp_path: Path) -> None:
    """`scores` is the per-doc payload that export/gate/accept-scores actually consume
    and is only ~3% of the file. Moving it would put every ranking behind a decompress
    for almost no saving — and is why RESULTS.md can be byte-identical by construction.
    """
    p = tmp_path / "bench.jsonl"
    _write(p, [_line("v", "1.0", "r1"), _line("v", "1.0", "r2")])
    cr.compact(p, detail_dir=tmp_path / "results" / "detail", root=tmp_path)

    out = [json.loads(x) for x in p.read_text().splitlines()]
    assert out[0]["scores"] == {"a": 80.0, "b": 80.0}


def test_compaction_is_idempotent(tmp_path: Path) -> None:
    """A second run must be a no-op — a compactor that re-stubs its own stubs would
    nest detail files and lose the payload."""
    p = tmp_path / "bench.jsonl"
    _write(p, [_line("v", "1.0", "r1"), _line("v", "1.0", "r2")])
    cr.compact(p, detail_dir=tmp_path / "results" / "detail", root=tmp_path)
    first = p.read_bytes()
    stats = cr.compact(p, detail_dir=tmp_path / "results" / "detail", root=tmp_path)
    assert p.read_bytes() == first
    assert stats.compacted == 0


def test_line_without_id_run_is_left_alone(tmp_path: Path) -> None:
    """Legacy lines predate id_run. Inventing a filename for them risks collisions that
    would overwrite one line's payload with another's — leaving them inline is the only
    safe option, and they are a handful of the file."""
    p = tmp_path / "bench.jsonl"
    old = _line("v", "1.0", "r1")
    del old["id_run"]
    _write(p, [old, _line("v", "1.0", "r2")])
    stats = cr.compact(p, detail_dir=tmp_path / "results" / "detail", root=tmp_path)

    out = [json.loads(x) for x in p.read_text().splitlines()]
    assert out[0]["per_doc"], "a line with no id_run must keep its payload"
    assert stats.skipped_no_id == 1


def test_holdout_lines_are_compacted_on_their_own_identity(tmp_path: Path) -> None:
    """A holdout-only line is not superseded by a full-corpus line of the same pin —
    they describe different document sets, and stubbing one because the other is newer
    would compact a line that is still the current view of the sealed set."""
    p = tmp_path / "bench.jsonl"
    hold = _line("v", "1.0", "r1")
    hold["holdout_mode"] = "only"
    _write(p, [hold, _line("v", "1.0", "r2")])
    cr.compact(p, detail_dir=tmp_path / "results" / "detail", root=tmp_path)

    out = [json.loads(x) for x in p.read_text().splitlines()]
    assert out[0]["per_doc"], "the holdout line is the latest of its own identity"


def test_results_md_is_byte_identical_after_compaction(tmp_path: Path) -> None:
    """The acceptance test from the plan: compaction must not move a single character
    of the published tables."""
    exp_path = Path(__file__).resolve().parents[1] / "scripts" / "export-results-md.py"
    spec = importlib.util.spec_from_file_location("export_results_md_compact", exp_path)
    assert spec and spec.loader
    exp = importlib.util.module_from_spec(spec)
    sys.modules["export_results_md_compact"] = exp
    spec.loader.exec_module(exp)

    p = tmp_path / "bench.jsonl"
    _write(
        p,
        [
            _line("v", "1.0", "r1", mean=70.0),
            _line("v", "1.0", "r2", mean=80.0),
            _line("w", "3.0", "r3", mean=90.0),
        ],
    )
    before = exp.to_fidelity_markdown(exp.rows_from_jsonl(p), p)
    cr.compact(p, detail_dir=tmp_path / "results" / "detail", root=tmp_path)
    after = exp.to_fidelity_markdown(exp.rows_from_jsonl(p), p)
    assert before == after


def test_stub_path_is_root_relative_and_matches_what_hydrate_reads(tmp_path: Path) -> None:
    """The stub is written by compact() and resolved by hydrate(); if they disagree on
    the anchor directory the payload is unreachable. A test that threads its own root
    through BOTH sides passes either way, so this asserts the literal stored value —
    the plan specifies `results/detail/<id_run>.json.gz`.
    """
    p = tmp_path / "results" / "bench.jsonl"
    p.parent.mkdir(parents=True)
    _write(p, [_line("v", "1.0", "r1"), _line("v", "1.0", "r2")])
    cr.compact(p, detail_dir=tmp_path / "results" / "detail", root=tmp_path)

    stub = json.loads(p.read_text().splitlines()[0])
    assert stub["detail"] == "results/detail/r1__script_redlines.json.gz"
    # and the anchor actually resolves
    assert (tmp_path / stub["detail"]).is_file()
    assert cr.hydrate(stub, root=tmp_path)["per_doc"] == _line("v", "1.0", "r1")["per_doc"]


def test_detail_dir_outside_root_is_rejected(tmp_path: Path) -> None:
    """Silently writing an unresolvable stub would lose the payload on read."""
    import pytest

    p = tmp_path / "bench.jsonl"
    _write(p, [_line("v", "1.0", "r1"), _line("v", "1.0", "r2")])
    with pytest.raises(ValueError, match="not under root"):
        cr.compact(p, detail_dir=tmp_path / "detail", root=tmp_path / "elsewhere")


def test_all_lines_also_compacts_the_current_line(tmp_path: Path) -> None:
    """The plan's rule (supersededonly) recovers 18.9% on the real file because most
    lines ARE the latest of their identity. `--all-lines` recovers 96.5%. It is opt-in
    because it is only safe while nothing reads the moved fields back from this file.
    """
    p = tmp_path / "results" / "bench.jsonl"
    p.parent.mkdir(parents=True)
    _write(p, [_line("v", "1.0", "r1"), _line("v", "1.0", "r2")])
    cr.compact(p, detail_dir=tmp_path / "results" / "detail", root=tmp_path, all_lines=True)

    out = [json.loads(x) for x in p.read_text().splitlines()]
    assert all("per_doc" not in line for line in out)
    assert all(line["detail"] for line in out)
    # Still fully recoverable — compaction never discards.
    assert cr.hydrate(out[1], root=tmp_path)["per_doc"] == _line("v", "1.0", "r2")["per_doc"]


def test_all_lines_still_keeps_scores_inline(tmp_path: Path) -> None:
    p = tmp_path / "results" / "bench.jsonl"
    p.parent.mkdir(parents=True)
    _write(p, [_line("v", "1.0", "r1"), _line("v", "1.0", "r2")])
    cr.compact(p, detail_dir=tmp_path / "results" / "detail", root=tmp_path, all_lines=True)
    out = [json.loads(x) for x in p.read_text().splitlines()]
    assert all(line["scores"] for line in out)


def test_lines_sharing_an_id_run_do_not_overwrite_each_other(tmp_path: Path) -> None:
    """`id_run` identifies a RUN, not a line: one bench run emits script_redlines,
    accepted_changes, roundtrip and visual_redlines lines that all carry the same
    id_run (up to 4 on the real file). Keying detail files on id_run alone made the
    last line's payload overwrite the earlier ones — silent data loss, caught only by
    hydrating every stub back and comparing against a pre-compaction backup.
    """
    p = tmp_path / "results" / "bench.jsonl"
    p.parent.mkdir(parents=True)
    lines = []
    for bench in ("script_redlines", "accepted_changes", "roundtrip"):
        old = _line("v", "1.0", "r1")
        old["benchmark"] = bench
        old["per_doc"] = {"marker": bench}          # distinct payload per benchmark
        lines.append(old)
        new = _line("v", "1.0", "r2")
        new["benchmark"] = bench
        lines.append(new)
    _write(p, lines)

    cr.compact(p, detail_dir=tmp_path / "results" / "detail", root=tmp_path)

    out = [json.loads(x) for x in p.read_text().splitlines()]
    stubs = [line for line in out if line.get("detail")]
    assert len(stubs) == 3
    assert len({s["detail"] for s in stubs}) == 3, "each line needs its OWN detail file"
    for stub in stubs:
        assert cr.hydrate(stub, root=tmp_path)["per_doc"] == {"marker": stub["benchmark"]}
