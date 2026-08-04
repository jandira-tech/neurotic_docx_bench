"""Corpus symmetry: every generating run is scored on the SAME document set.

The bug this file guards against (plan Chapter 6, D1): corpus coverage was
per-run copy-paste, and copy-paste does not propagate. Of the 12 runs declaring
``script_redlines``, four (``jubarte-rust``, ``jubarte-final-native``,
``jubarte-final-lossless``, ``docxodus``) hand-chained three ``generate:``
invocations with explicit ``--manifest``/``--source-dir`` — 803 pairs. The other
eight (``docx-redline-js``, ``folio``, ``superdoc``, ``redlines``,
``superdoc-redlines``, ``jubarte-wasm``, ``superdoc-ts``, ``superdoc-native``)
omitted the flags and silently inherited the generators' argparse default — one
pool, 207 pairs. All 12 were published in the same comparison table, so rows with
different ``n`` were not the same measurement.

The split is not "us vs them" and the footgun has been tripped in both
directions: ``docxodus``, a competitor, already had full coverage, while
``jubarte-wasm``, ours, did not.

The fix is structural, not a copy-paste into the remaining eight: the pools are
declared ONCE at the top level of bench.yaml and the driver expands each run's
single ``generate:`` command across them, so full coverage is the default and a
future fourth pool cannot be added to one vendor and forgotten on the rest.
"""

from __future__ import annotations

import json
import shlex
from pathlib import Path

import pytest

from neurotic_docx_bench import cli
from neurotic_docx_bench.config import (
    CorpusEntry,
    corpora_for_run,
    expand_generate_commands,
    load_config,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

_THREE_CORPORA = """
source_of_truth: oracle
corpora:
  - name: word_based
    manifest: corpus/word_based/centralized_mapping.csv
    source_dir: corpus/word_based/docx_source
  - name: word_based_randomized
    manifest: corpus/word_based/centralized_mapping_randomized.csv
    source_dir: corpus/word_based/docx_source_randomized
  - name: word_redlines_superdoc
    manifest: corpus/word_redlines_superdoc/centralized_mapping.csv
    source_dir: corpus/word_redlines_superdoc/docx_source
runs:
  - name: vendor-a
    render: soffice
    unversioned: true
    generate: "uv run python -m gen --out=$RUN_DIR/docx --tool=vendor-a"
"""


def _write(tmp_path: Path, text: str) -> Path:
    cfg_path = tmp_path / "bench.yaml"
    cfg_path.write_text(text)
    return cfg_path


def test_top_level_corpora_parsed(tmp_path):
    cfg = load_config(_write(tmp_path, _THREE_CORPORA))
    assert [c.name for c in cfg.corpora] == [
        "word_based",
        "word_based_randomized",
        "word_redlines_superdoc",
    ]
    assert cfg.corpora[0] == CorpusEntry(
        name="word_based",
        manifest="corpus/word_based/centralized_mapping.csv",
        source_dir="corpus/word_based/docx_source",
    )


def test_run_without_corpora_gets_every_corpus(tmp_path):
    """THE regression guard for D1: silence means *all* pools, never just the first."""
    cfg = load_config(_write(tmp_path, _THREE_CORPORA))
    run = cfg.runs[0]
    assert run.corpora is None, "the run declared no corpora"

    cmds = expand_generate_commands(cfg, run)
    assert cmds == [
        "uv run python -m gen --out=$RUN_DIR/docx --tool=vendor-a "
        "--manifest=corpus/word_based/centralized_mapping.csv "
        "--source-dir=corpus/word_based/docx_source",
        "uv run python -m gen --out=$RUN_DIR/docx --tool=vendor-a "
        "--manifest=corpus/word_based/centralized_mapping_randomized.csv "
        "--source-dir=corpus/word_based/docx_source_randomized",
        "uv run python -m gen --out=$RUN_DIR/docx --tool=vendor-a "
        "--manifest=corpus/word_redlines_superdoc/centralized_mapping.csv "
        "--source-dir=corpus/word_redlines_superdoc/docx_source",
    ]


def test_run_may_declare_its_own_corpus_subset(tmp_path):
    """Escape hatch: a run that genuinely applies to one pool says so explicitly."""
    cfg = load_config(
        _write(tmp_path, _THREE_CORPORA + "    corpora: [word_redlines_superdoc]\n"),
    )
    run = cfg.runs[0]
    assert run.corpora == ("word_redlines_superdoc",)
    assert [c.name for c in corpora_for_run(cfg, run)] == ["word_redlines_superdoc"]
    assert expand_generate_commands(cfg, run) == [
        "uv run python -m gen --out=$RUN_DIR/docx --tool=vendor-a "
        "--manifest=corpus/word_redlines_superdoc/centralized_mapping.csv "
        "--source-dir=corpus/word_redlines_superdoc/docx_source",
    ]


def test_run_corpora_must_name_a_declared_corpus(tmp_path):
    with pytest.raises(ValueError, match="unknown corpora"):
        load_config(_write(tmp_path, _THREE_CORPORA + "    corpora: [typo_pool]\n"))


def test_duplicate_corpus_names_rejected(tmp_path):
    dupe = _THREE_CORPORA.replace("name: word_based_randomized", "name: word_based")
    with pytest.raises(ValueError, match="duplicate corpus name"):
        load_config(_write(tmp_path, dupe))


def test_corpus_entry_requires_manifest_and_source_dir(tmp_path):
    bad = """
source_of_truth: oracle
corpora:
  - name: word_based
    manifest: corpus/word_based/centralized_mapping.csv
runs: []
"""
    with pytest.raises(ValueError, match="source_dir"):
        load_config(_write(tmp_path, bad))


def test_generate_may_not_hardcode_the_corpus_flags(tmp_path):
    """A hand-written --manifest is exactly how the asymmetry arose. Reject it."""
    sneaky = _THREE_CORPORA.replace(
        '--tool=vendor-a"',
        '--tool=vendor-a --manifest=corpus/word_based/centralized_mapping.csv"',
    )
    with pytest.raises(ValueError, match="--manifest"):
        load_config(_write(tmp_path, sneaky))


def test_config_without_corpora_runs_the_command_verbatim(tmp_path):
    """Back-compat: bench.randomized.yaml / bench.compare.yaml declare no corpora."""
    legacy = """
source_of_truth: oracle
runs:
  - name: vendor-a
    render: soffice
    unversioned: true
    generate: "uv run python -m gen --manifest=corpus/word_based/centralized_mapping_randomized.csv"
"""
    cfg = load_config(_write(tmp_path, legacy))
    assert cfg.corpora == ()
    assert expand_generate_commands(cfg, cfg.runs[0]) == [
        "uv run python -m gen --manifest=corpus/word_based/centralized_mapping_randomized.csv",
    ]


def test_environment_config_for_run_keeps_corpora(tmp_path):
    from neurotic_docx_bench.config import environment_config_for_run

    cfg = load_config(_write(tmp_path, _THREE_CORPORA))
    narrowed = environment_config_for_run(cfg, "vendor-a")
    assert narrowed.corpora == cfg.corpora


# --------------------------------------------------------------------------
# The shipped bench.yaml: the actual claim under test.
# --------------------------------------------------------------------------


def test_shipped_bench_yaml_declares_all_three_pools():
    cfg = load_config(REPO_ROOT / "bench.yaml")
    assert {c.name for c in cfg.corpora} == {
        "word_based",
        "word_based_randomized",
        "word_redlines_superdoc",
    }


def test_every_generating_run_covers_every_corpus():
    """No vendor is scored on a smaller document set than any other vendor."""
    cfg = load_config(REPO_ROOT / "bench.yaml")
    generating = [r for r in cfg.runs if r.generate]
    assert generating, "bench.yaml has generating runs"
    assert len(cfg.corpora) == 3, "bench.yaml declares the three pools (803 pairs)"
    short = {
        r.name: [c.name for c in corpora_for_run(cfg, r)]
        for r in generating
        if len(corpora_for_run(cfg, r)) != len(cfg.corpora)
    }
    assert short == {}, f"runs scored on a subset of the corpus: {short}"


def test_no_run_hand_chains_its_generate_command():
    """All four previously-chaining runs drop their chain, not just ours."""
    cfg = load_config(REPO_ROOT / "bench.yaml")
    for run in cfg.runs:
        if not run.generate:
            continue
        assert "&&" not in run.generate, (
            f"run '{run.name}' still hand-chains its generate command; "
            "the driver expands across corpora now"
        )
    for name in _PREVIOUSLY_CHAINED:
        run = next(r for r in cfg.runs if r.name == name)
        assert len(expand_generate_commands(cfg, run)) == 3


# The `generate:` chains exactly as they stood before the corpus list was
# hoisted (bench.yaml @ 1b1fa110). Four runs, three invocations each. Kept
# verbatim so the equivalence check below compares against what actually ran,
# not against a paraphrase of it.
_HISTORICAL_CHAINS = {
    "jubarte-final-native": (
        "node --import tsx scripts/generate-native-redlines.ts --method=jubarte-native --dist=dist/jubarte-final --out=$RUN_DIR/docx --run-dir=$RUN_DIR --tool=jubarte-final-native && "
        "node --import tsx scripts/generate-native-redlines.ts --method=jubarte-native --manifest=corpus/word_based/centralized_mapping_randomized.csv --source-dir=corpus/word_based/docx_source_randomized --dist=dist/jubarte-final --out=$RUN_DIR/docx --run-dir=$RUN_DIR --tool=jubarte-final-native && "
        "node --import tsx scripts/generate-native-redlines.ts --method=jubarte-native --manifest=corpus/word_redlines_superdoc/centralized_mapping.csv --source-dir=corpus/word_redlines_superdoc/docx_source --dist=dist/jubarte-final --out=$RUN_DIR/docx --run-dir=$RUN_DIR --tool=jubarte-final-native"
    ),
    "jubarte-final-lossless": (
        "node --import tsx scripts/generate-native-redlines.ts --method=jubarte-lossless --dist=dist/jubarte-final --out=$RUN_DIR/docx --run-dir=$RUN_DIR --tool=jubarte-final-lossless && "
        "node --import tsx scripts/generate-native-redlines.ts --method=jubarte-lossless --manifest=corpus/word_based/centralized_mapping_randomized.csv --source-dir=corpus/word_based/docx_source_randomized --dist=dist/jubarte-final --out=$RUN_DIR/docx --run-dir=$RUN_DIR --tool=jubarte-final-lossless && "
        "node --import tsx scripts/generate-native-redlines.ts --method=jubarte-lossless --manifest=corpus/word_redlines_superdoc/centralized_mapping.csv --source-dir=corpus/word_redlines_superdoc/docx_source --dist=dist/jubarte-final --out=$RUN_DIR/docx --run-dir=$RUN_DIR --tool=jubarte-final-lossless"
    ),
    "docxodus": (
        "node --import tsx scripts/generate-native-redlines.ts --method=docxodus --out=$RUN_DIR/docx --run-dir=$RUN_DIR --tool=docxodus && "
        "node --import tsx scripts/generate-native-redlines.ts --method=docxodus --manifest=corpus/word_based/centralized_mapping_randomized.csv --source-dir=corpus/word_based/docx_source_randomized --out=$RUN_DIR/docx --run-dir=$RUN_DIR --tool=docxodus && "
        "node --import tsx scripts/generate-native-redlines.ts --method=docxodus --manifest=corpus/word_redlines_superdoc/centralized_mapping.csv --source-dir=corpus/word_redlines_superdoc/docx_source --out=$RUN_DIR/docx --run-dir=$RUN_DIR --tool=docxodus"
    ),
    "jubarte-rust": (
        "node --import tsx scripts/generate-native-redlines.ts --method=jubarte-rust --dist=src/neurotic_docx_bench/utils/jubarte/jubarte-rust --out=$RUN_DIR/docx --run-dir=$RUN_DIR --tool=jubarte-rust && "
        "node --import tsx scripts/generate-native-redlines.ts --method=jubarte-rust --manifest=corpus/word_based/centralized_mapping_randomized.csv --source-dir=corpus/word_based/docx_source_randomized --dist=src/neurotic_docx_bench/utils/jubarte/jubarte-rust --out=$RUN_DIR/docx --run-dir=$RUN_DIR --tool=jubarte-rust && "
        "node --import tsx scripts/generate-native-redlines.ts --method=jubarte-rust --manifest=corpus/word_redlines_superdoc/centralized_mapping.csv --source-dir=corpus/word_redlines_superdoc/docx_source --dist=src/neurotic_docx_bench/utils/jubarte/jubarte-rust --out=$RUN_DIR/docx --run-dir=$RUN_DIR --tool=jubarte-rust"
    ),
}
_PREVIOUSLY_CHAINED = tuple(_HISTORICAL_CHAINS)

# The generators' own argparse defaults (generate-native-redlines.ts:991-992,
# superdoc_gen.py:171-172, redlines_gen.py:240-241,
# superdoc_redlines_gen.py:248-249). A historical segment that passed neither
# flag ran on exactly this pool.
_GENERATOR_DEFAULTS = {
    "--manifest": "corpus/word_based/centralized_mapping.csv",
    "--source-dir": "corpus/word_based/docx_source",
}


def _invocation_shape(cmd: str) -> tuple[tuple[str, ...], str, str]:
    """(non-corpus tokens in order, manifest, source_dir) for one invocation.

    Flag ORDER is irrelevant to both argument parsers (argparse and the TS
    ``get()`` helper scan for ``--flag=``), so equivalence is asserted on what
    each invocation resolves to, not on string equality.
    """
    tokens = shlex.split(cmd)
    resolved = dict(_GENERATOR_DEFAULTS)
    skeleton: list[str] = []
    for tok in tokens:
        matched = next((f for f in _GENERATOR_DEFAULTS if tok.startswith(f"{f}=")), None)
        if matched:
            resolved[matched] = tok.split("=", 1)[1]
        else:
            skeleton.append(tok)
    return tuple(skeleton), resolved["--manifest"], resolved["--source-dir"]


@pytest.mark.parametrize("run_name", _PREVIOUSLY_CHAINED)
def test_expansion_matches_the_hand_written_chain_it_replaced(run_name):
    """The four runs that already covered 803 pairs must still run the same work.

    A historical segment with no ``--manifest`` relied on the generator default;
    the driver now passes that pool explicitly. Equivalence therefore also pins
    that the FIRST corpus entry is the generators' default pool.
    """
    cfg = load_config(REPO_ROOT / "bench.yaml")
    run = next(r for r in cfg.runs if r.name == run_name)
    before = [_invocation_shape(seg) for seg in _HISTORICAL_CHAINS[run_name].split("&&")]
    after = [_invocation_shape(c) for c in expand_generate_commands(cfg, run)]
    assert after == before


# --------------------------------------------------------------------------
# Driver: expansion is executed, and per-invocation artifacts are merged.
# --------------------------------------------------------------------------


def _writer_cmd(timings: dict[str, int], failures: list[dict[str, str]]) -> str:
    return (
        f"printf %s {json.dumps(json.dumps(timings))} > $RUN_DIR/generate_timings.json && "
        f"printf %s {json.dumps(json.dumps(failures))} > $RUN_DIR/generate_failures.json"
    )


def test_run_generate_merges_artifacts_across_invocations(tmp_path):
    """Each invocation OVERWRITES generate_timings/failures.json — merge, don't lose.

    Without merging, expanding to three invocations would discard the first two
    pools' per-doc failures, and ITT would under-count exactly the docs it exists
    to count.
    """
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    cli._run_generate(
        [
            _writer_cmd({"a_b": 1}, [{"doc": "a_b", "stage": "generate", "error": "boom"}]),
            _writer_cmd({"c_d": 2}, [{"doc": "c_d", "stage": "generate", "error": "bang"}]),
            _writer_cmd({"e_f": 3}, []),
        ],
        run_dir,
    )
    timings = json.loads((run_dir / "generate_timings.json").read_text())
    failures = json.loads((run_dir / "generate_failures.json").read_text())
    assert timings == {"a_b": 1, "c_d": 2, "e_f": 3}
    assert [f["doc"] for f in failures] == ["a_b", "c_d"]


def test_run_generate_single_command_still_works(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    cli._run_generate([_writer_cmd({"a_b": 1}, [])], run_dir)
    assert json.loads((run_dir / "generate_timings.json").read_text()) == {"a_b": 1}


# ---------------------------------------------------------------------------
# Plan Chapter 6, D4 — the generate timeout must scale with the corpus, and a
# timeout must be reported as a timeout rather than as the tool's failure.
# ---------------------------------------------------------------------------


def test_generate_timeout_scales_with_pair_count():
    """A 4x bigger pool gets a proportionally bigger budget.

    The hard-coded 1800s budget was chosen for a 207-pair corpus. When the corpus
    grew to 803 pairs the budget did not move, and docxodus was killed at exactly
    1800s having generated 622 of ~763 documents — our clock recorded as their
    failure.
    """
    small = cli._generate_timeout_s(pairs=200)
    big = cli._generate_timeout_s(pairs=800)
    assert big > small, "budget must grow with the pool it has to cover"
    assert big >= 4 * small * 0.9, f"800 pairs got {big}s vs {small}s for 200 — not proportional"


def test_generate_timeout_has_a_floor_for_tiny_pools():
    """A 3-pair smoke pool must not get a 3-second budget — startup dominates."""
    assert cli._generate_timeout_s(pairs=3) >= 300


def test_timeout_is_reported_as_a_timeout_naming_the_budget_and_progress(tmp_path):
    """A killed generate must say it was killed, not merely that it failed.

    This is the D3/D4 disease: our budget attributed to their code. The error has
    to name the budget and how far the tool actually got, so a slow tool can be
    reported as slow instead of broken.
    """
    run_dir = tmp_path / "run"
    (run_dir / "docx").mkdir(parents=True)
    for i in range(7):
        (run_dir / "docx" / f"doc{i}.docx").write_bytes(b"x")

    with pytest.raises(cli.GenerateTimeout) as exc:
        cli._run_generate(["sleep 30"], run_dir, timeout_s=0.4)

    msg = str(exc.value)
    assert "0.4" in msg, f"budget not named: {msg}"
    assert "7" in msg, f"progress not reported: {msg}"
    assert "timed out" in msg.lower()
