#!/usr/bin/env python3
"""Execute Stage L1 of plans/jubarte-lossless-to-target.md — the cluster lens partition.

Stage L1 asks one question about the ≈50 cluster: *is the engine failing to mark
the edit, or is the scorer failing to credit markup that is already correct?*
The instrument is the functional lens (``accept(candidate) == next``,
``reject(candidate) == base``) and the answer is a four-way partition plus the
gate that reads it (``diagnostics/cluster_lens.py``). Neither is reimplemented
here; this is the runner that puts real documents through them.

**Why a script and not a ``bench`` subcommand.** Every ``bench`` subcommand
operates on a corpus or a run directory that exists. This one reaches backwards
into a *finished* run whose directory has been deleted, re-derives its inputs,
and shells out to the Node generator to rebuild them. That is a one-off
archaeological operation against a specific recorded run, not a benchmark stage,
and putting it in the CLI would imply it is part of the normal pipeline. It is
not: once L1 has answered, nothing re-runs it.

**Why regeneration is needed at all.** ``results/bench.jsonl`` records only
run-level lens counts. The per-document verdicts live in
``results/detail/<run>__script_redlines*.json.gz`` — but only for the 46 cluster
documents the original run actually lensed. The lens stage resolves its source
DOCX through ``cli._source_docx_map``, which looks only under
``cfg.source_of_truth.parent`` (``corpus/word_based``), so the entire
``word_redlines_superdoc`` pool was never lensed. 120 of the 166 cluster
documents are in that pool. Partitioning on the recorded 46 would be
partitioning on a **biased 27% subsample drawn from one corpus** — so the
candidates are regenerated and the lens is run over the whole cluster.

**The regeneration control.** The run directory is gone, so "are these the same
candidates that were scored?" cannot be answered by comparing bytes. It is
answered three ways, all reported: the engine build still hashes to the
``tool_version`` the run recorded; the generate command is taken from
``bench.yaml`` via ``config.expand_generate_commands`` rather than retyped; and
the fresh lens verdicts are compared against the 46 the original run recorded.
A disagreement there is a finding, not a rounding error — it would mean the
partition describes a different artefact than the published scores.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import os
import shlex
import subprocess
import sys
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))

from neurotic_docx_bench import config as bench_config
from neurotic_docx_bench import functional_lens, pipeline, tool_updater
from neurotic_docx_bench.diagnostics.cluster_lens import (
    CLUSTER_HIGH,
    CLUSTER_LOW,
    Bucket,
    ClusterPartition,
    cross_tabulate,
    gate,
    partition,
    select_cluster,
)

DEFAULT_SCORE_FIELD = "overall_score_pagefair"
"""The one per-document field that reproduces the published run figures.

The detail file carries eight score fields spanning 74.33–78.60 mean. Only
``overall_score_pagefair`` reproduces run ``019fcc6f``'s recorded ITT mean
77.0151 / median 78.5311 / exact-100 142 exactly, and the plan's cluster was
drawn on the published scorer. Selecting on any other field selects a different
set of documents and answers a different question, so the field is named, never
inferred.
"""

DEFAULT_MIN_TOKEN_DOCS = 3


# --- reading the recorded run ------------------------------------------------


def load_detail(path: Path | str) -> dict[str, dict]:
    """``per_doc`` out of a gzipped detail file."""
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        payload = json.load(fh)
    per_doc = payload.get("per_doc")
    if not isinstance(per_doc, dict) or not per_doc:
        raise ValueError(f"{path}: no per_doc records")
    return per_doc


def scores_from_detail(
    per_doc: Mapping[str, Mapping[str, object]], *, field: str = DEFAULT_SCORE_FIELD
) -> dict[str, float]:
    """``{doc: score}`` on ``field``, skipping records that do not carry it.

    A missing score is skipped rather than defaulted: ``score_v2`` is present on
    195 of 763 records, and defaulting the absent ones to 0.0 would fabricate
    documents into the low bands. A field that names nothing at all raises,
    because the failure mode of a typo is an empty cluster and a gate that
    PROCEEDs on no evidence.
    """
    scores = {
        name: float(value)
        for name, record in per_doc.items()
        if isinstance(value := record.get(field), (int, float)) and not isinstance(value, bool)
    }
    if not scores:
        raise ValueError(f"no numeric {field!r} values in per_doc — is the field name right?")
    return scores


# --- restricting the corpus to the cluster -----------------------------------


def filter_manifest(src: Path | str, keys: Iterable[str], out: Path | str) -> tuple[str, ...]:
    """Write the rows of ``src`` whose ``pair_stem`` is in ``keys``; return the
    matched keys, lower-cased and sorted.

    The generator reads the manifest with its own CSV parser and expects the
    committed schema, so the header is preserved verbatim and only rows are
    dropped. Nothing is written when no row matches — an empty manifest makes
    the generator produce zero redlines and exit 1, which reads as a
    regeneration failure rather than as a pool that simply holds no cluster
    documents.
    """
    wanted = {k.lower() for k in keys}
    with Path(src).open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        fieldnames = reader.fieldnames or []
        rows = [r for r in reader if (r.get("pair_stem") or "").strip().lower() in wanted]
    if not rows:
        return ()
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return tuple(sorted((r["pair_stem"] or "").strip().lower() for r in rows))


def index_candidates(docx_dir: Path | str, tool: str) -> dict[str, Path]:
    """``{pair_stem: candidate_docx}`` for regenerated ``<pair>_<tool>_redline.docx``.

    Keyed through ``pipeline.redline_key`` — the same function the bench uses to
    key candidates during a real run — so a naming convention change moves both
    together. ``~$`` Word owner-lock files are skipped, as they are there.
    """
    index: dict[str, Path] = {}
    for p in sorted(Path(docx_dir).glob("*.docx")):
        if p.name.startswith("~$"):
            continue
        index[pipeline.redline_key(p.stem, tool)] = p
    return index


# --- generation --------------------------------------------------------------


def _tool_from_command(command: str, default: str) -> str:
    for token in shlex.split(command):
        if token.startswith("--tool="):
            return token.split("=", 1)[1]
    return default


def _replace_flag(command: str, flag: str, value: str) -> str:
    """Swap ``--flag=<x>`` for ``--flag=<value>``, preserving everything else.

    The command comes from ``bench.yaml`` through ``expand_generate_commands``,
    so the method, dist and tool flags are exactly the ones the published run
    used. Only the corpus pointers move.
    """
    tokens = shlex.split(command)
    swapped = [f"{flag}={value}" if t.startswith(f"{flag}=") else t for t in tokens]
    return shlex.join(swapped)


def count_present(docx_dir: Path | str, tool: str, keys: Iterable[str]) -> int:
    """How many of ``keys`` have a candidate DOCX on disk.

    Counted by existence, not by creation: the generator skips a pair whose
    output already exists (there is no ``--force`` in the run's command), so a
    second invocation writes nothing and a "files created" count would report a
    fully-covered pool as ``0 written``. What the lens consumes is what exists.
    """
    index = index_candidates(docx_dir, tool)
    return sum(1 for k in keys if k in index)


@dataclass(frozen=True)
class GenerationResult:
    corpus: str
    tool: str
    n_requested: int
    n_present: int
    n_new: int
    command: str
    returncode: int
    stderr_tail: str


def regenerate_cluster(
    cfg: bench_config.BenchConfig,
    rc: bench_config.RunConfig,
    keys: Iterable[str],
    workdir: Path,
) -> tuple[list[GenerationResult], dict[str, Path]]:
    """Regenerate candidates for ``keys`` only, one generator call per corpus pool.

    Only the cluster is regenerated: a full 763-pair sweep answers nothing L1
    asks and costs the rest of the corpus in wall clock for it.
    """
    keys = {k.lower() for k in keys}
    commands = bench_config.expand_generate_commands(cfg, rc)
    entries = bench_config.corpora_for_run(cfg, rc)
    if len(commands) != len(entries):
        raise RuntimeError(
            f"expected one generate command per corpus, got {len(commands)} for {len(entries)}"
        )
    docx_dir = workdir / "docx"
    docx_dir.mkdir(parents=True, exist_ok=True)
    results: list[GenerationResult] = []
    for entry, command in zip(entries, commands, strict=True):
        manifest = workdir / f"manifest__{entry.name}.csv"
        selected = filter_manifest(_REPO / entry.manifest, keys, manifest)
        if not selected:
            continue
        before = set(docx_dir.glob("*.docx"))
        cmd = _replace_flag(command, "--manifest", str(manifest))
        env = {**os.environ, "RUN_DIR": str(workdir)}
        cmd = cmd.replace("$RUN_DIR/docx", str(docx_dir)).replace("$RUN_DIR", str(workdir))
        proc = subprocess.run(
            cmd, shell=True, cwd=_REPO, env=env, capture_output=True, text=True, check=False
        )
        tool = _tool_from_command(command, rc.name)
        results.append(
            GenerationResult(
                corpus=entry.name,
                tool=tool,
                n_requested=len(selected),
                n_present=count_present(docx_dir, tool, selected),
                n_new=len(set(docx_dir.glob("*.docx")) - before),
                command=cmd,
                returncode=proc.returncode,
                stderr_tail="\n".join(proc.stderr.strip().splitlines()[-12:]),
            )
        )
    tool = results[0].tool if results else rc.name
    return results, index_candidates(docx_dir, tool)


# --- the regeneration control ------------------------------------------------


@dataclass(frozen=True)
class RegenerationControl:
    """Fresh lens verdicts vs the ones the original run recorded."""

    n_compared: int
    n_agree: int
    n_no_recorded_verdict: int
    disagreements: tuple[dict, ...]

    @property
    def agreement(self) -> float:
        return self.n_agree / self.n_compared if self.n_compared else 0.0


def _recorded_triple(record: Mapping[str, object]) -> tuple | None:
    """``(accept_ok, reject_ok, blind)`` as recorded, or None if never lensed."""
    if "functional_accept_ok" not in record and "functional_reject_ok" not in record:
        return None
    accept, reject = record.get("functional_accept_ok"), record.get("functional_reject_ok")
    return (
        accept if isinstance(accept, bool) else None,
        reject if isinstance(reject, bool) else None,
        record.get("functional_blind") is True,
    )


def compare_to_recorded(
    fresh: Mapping[str, functional_lens.FunctionalVerdict],
    per_doc: Mapping[str, Mapping[str, object]],
) -> RegenerationControl:
    """Check the regenerated candidates against the run's own recorded verdicts.

    Only the fields that decide a bucket are compared — the two tolerant
    invariants and ``blind``, which decides whether the document is in the
    gate's denominator at all. Documents the original run never lensed are
    counted separately and never as agreement.
    """
    n_compared = n_agree = n_absent = 0
    disagreements: list[dict] = []
    for name, verdict in fresh.items():
        recorded = _recorded_triple(per_doc.get(name, {}))
        if recorded is None:
            n_absent += 1
            continue
        n_compared += 1
        got = (verdict.accept_ok, verdict.reject_ok, verdict.blind)
        if got == recorded:
            n_agree += 1
        else:
            disagreements.append({
                "doc": name,
                "recorded": dict(zip(("accept_ok", "reject_ok", "blind"), recorded, strict=True)),
                "fresh": dict(zip(("accept_ok", "reject_ok", "blind"), got, strict=True)),
            })
    return RegenerationControl(n_compared, n_agree, n_absent, tuple(disagreements))


# --- cross-tabulation ranking ------------------------------------------------


@dataclass(frozen=True)
class TokenStat:
    token: str
    n_in_bucket: int
    n_token_judged: int
    concentration: float


def top_tokens(
    table: Mapping[str, Counter],
    bucket: Bucket,
    *,
    limit: int = 8,
    min_docs: int = DEFAULT_MIN_TOKEN_DOCS,
) -> tuple[TokenStat, ...]:
    """Fixture-name tokens most present in ``bucket``, with their concentration.

    Two numbers, because either alone misleads. ``n_in_bucket`` answers "how
    much of this bucket is this family" and ranks; ``concentration`` — the share
    of that token's judged documents landing here — answers "is this family
    characteristic of the bucket, or merely large". Ranking on concentration
    alone surfaces every n=1 token at 100%, which is why ``min_docs`` floors it.
    """
    stats = [
        TokenStat(token, n, total, n / total)
        for token, counts in table.items()
        if (n := counts.get(bucket, 0)) >= min_docs and (total := sum(counts.values()))
    ]
    stats.sort(key=lambda s: (-s.n_in_bucket, -s.concentration, s.token))
    return tuple(stats[:limit])


# --- report ------------------------------------------------------------------


@dataclass
class L1Report:
    run_id: str
    run_name: str
    tool_version_recorded: str | None
    tool_version_now: str | None
    score_field: str
    band: tuple[float, float]
    cluster: tuple[str, ...] = ()
    cluster_median: float | None = None
    generation: list[GenerationResult] = field(default_factory=list)
    workdir: str | None = None
    n_candidates: int = 0
    n_unresolved_sources: int = 0
    part: ClusterPartition | None = None
    control: RegenerationControl | None = None
    gate_outcome: object = None
    tokens: dict[str, tuple[TokenStat, ...]] = field(default_factory=dict)


def _json_payload(rep: L1Report) -> dict:
    assert rep.part is not None and rep.control is not None
    counts = {b.value: n for b, n in rep.part.counts.items()}
    n_judged = rep.part.n_judged
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "stage": "L1",
        "plan": "plans/jubarte-lossless-to-target.md",
        "run": {
            "id_run": rep.run_id,
            "name": rep.run_name,
            "tool_version_recorded": rep.tool_version_recorded,
            "tool_version_now": rep.tool_version_now,
            "tool_version_match": rep.tool_version_recorded == rep.tool_version_now,
        },
        "selection": {
            "score_field": rep.score_field,
            "band": {"low": rep.band[0], "high": rep.band[1], "convention": "[low, high)"},
            "n_cluster": len(rep.cluster),
            "cluster_median": rep.cluster_median,
        },
        "regeneration": {
            "workdir": rep.workdir,
            "n_candidates": rep.n_candidates,
            "n_unresolved_sources": rep.n_unresolved_sources,
            "pools": [
                {
                    "corpus": g.corpus,
                    "tool": g.tool,
                    "n_requested": g.n_requested,
                    "n_present": g.n_present,
                    "n_newly_written": g.n_new,
                    "returncode": g.returncode,
                    "command": g.command,
                    "stderr_tail": g.stderr_tail,
                }
                for g in rep.generation
            ],
            "control": {
                "n_compared": rep.control.n_compared,
                "n_agree": rep.control.n_agree,
                "agreement": rep.control.agreement,
                "n_no_recorded_verdict": rep.control.n_no_recorded_verdict,
                "disagreements": list(rep.control.disagreements),
            },
        },
        "partition": {
            "buckets": counts,
            "n_judged": n_judged,
            "n_unjudged": len(rep.part.unjudged),
            "unjudged_reasons": dict(Counter(rep.part.unjudged.values())),
            "fractions_of_judged": {
                b: (n / n_judged if n_judged else 0.0) for b, n in counts.items()
            },
            "members": {b.value: list(rep.part.members(b)) for b in Bucket},
            "unjudged": dict(sorted(rep.part.unjudged.items())),
        },
        "gate": {
            "verdict": rep.gate_outcome.verdict.value,
            "both_hold_fraction": rep.gate_outcome.both_hold_fraction,
            "n_both_hold": rep.gate_outcome.n_both_hold,
            "n_judged": rep.gate_outcome.n_judged,
            "reason": rep.gate_outcome.reason,
        },
        "cross_tabulation": {
            b: [
                {
                    "token": s.token,
                    "n_in_bucket": s.n_in_bucket,
                    "n_token_judged": s.n_token_judged,
                    "concentration": s.concentration,
                }
                for s in stats
            ]
            for b, stats in rep.tokens.items()
        },
    }


_BUCKET_MEANING = {
    # BOTH_HOLD is stated as what the lens actually establishes, not as the plan's
    # inference from it. The lens compares TEXT: a candidate whose accept and reject
    # both round-trip is a functionally valid redline, which is not the same claim as
    # "the markup is correct". Paragraph alignment, change granularity and
    # formatting-change markup are all invisible to it, and all three move the pixel
    # score. Printing the plan's inference in the table would launder an unproven
    # claim into the artefact people read — see plans/reviews/l1-partition-lossless.md.
    Bucket.BOTH_HOLD: "accept→next and reject→base both hold at text level "
    "(functionally valid redline; says nothing about how it renders)",
    Bucket.REJECT_ONLY: "reject→base holds, accept→next fails",
    Bucket.ACCEPT_ONLY: "accept→next holds, reject→base fails",
    Bucket.NEITHER: "neither invariant holds",
}


def _markdown(rep: L1Report) -> str:
    assert rep.part is not None and rep.control is not None
    counts = rep.part.counts
    n_judged = rep.part.n_judged
    lines = [
        f"# Stage L1 partition — {rep.run_name}",
        "",
        f"Run `{rep.run_id}` · scorer field `{rep.score_field}` · "
        f"band [{rep.band[0]:g}, {rep.band[1]:g}) · generated "
        f"{datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}.",
        "",
        "## Buckets (raw counts, before interpretation)",
        "",
        "| bucket | n | % of judged | meaning |",
        "|---|---:|---:|---|",
    ]
    for b in Bucket:
        pct = (counts[b] / n_judged * 100) if n_judged else 0.0
        lines.append(f"| `{b.value}` | {counts[b]} | {pct:.1f}% | {_BUCKET_MEANING[b]} |")
    lines += [
        f"| **judged total** | **{n_judged}** | 100% | |",
        f"| *unjudged (excluded, contract C5)* | *{len(rep.part.unjudged)}* | — | "
        f"*{', '.join(f'{k}: {v}' for k, v in Counter(rep.part.unjudged.values()).most_common())}* |",
        f"| *cluster size* | *{len(rep.cluster)}* | — | *median "
        f"{rep.cluster_median:.2f}* |" if rep.cluster_median is not None
        else f"| *cluster size* | *{len(rep.cluster)}* | — | |",
        "",
        "The `meaning` column states what the lens **establishes**, not what the plan",
        "infers from it. The lens compares text only; see the L1 review for what that",
        "does and does not license.",
        "",
        "## Gate",
        "",
        f"**{rep.gate_outcome.verdict.value.upper()}** — {rep.gate_outcome.reason}",
        "",
        "## Regeneration control",
        "",
        f"- engine build: recorded `{rep.tool_version_recorded}`, now "
        f"`{rep.tool_version_now}` — "
        f"{'**identical**' if rep.tool_version_recorded == rep.tool_version_now else '**DIFFERENT**'}",
        f"- candidates regenerated: {rep.n_candidates} of {len(rep.cluster)} cluster documents",
        f"- fresh verdicts vs. recorded: {rep.control.n_agree}/{rep.control.n_compared} agree "
        f"({rep.control.agreement:.1%}); {rep.control.n_no_recorded_verdict} documents had no "
        f"recorded verdict to compare against",
    ]
    if rep.control.disagreements:
        lines.append("- **disagreements:**")
        lines += [
            f"  - `{d['doc']}` recorded {d['recorded']} → fresh {d['fresh']}"
            for d in rep.control.disagreements
        ]
    lines += ["", "## Cross-tabulation — top fixture tokens per bucket", "",
              "`n` is documents of that token in the bucket; `conc.` is the share of that "
              "token's judged documents landing there. Tokens are not disjoint.", ""]
    for b in Bucket:
        stats = rep.tokens.get(b.value, ())
        lines += [f"### `{b.value}` (n={counts[b]})", ""]
        if not stats:
            lines += ["_no token reaches the minimum population._", ""]
            continue
        lines += ["| token | n | of token's judged docs | conc. |", "|---|---:|---:|---:|"]
        lines += [
            f"| `{s.token}` | {s.n_in_bucket} | {s.n_token_judged} | {s.concentration:.0%} |"
            for s in stats
        ]
        lines.append("")
    lines += [
        "## Generation",
        "",
        "`present` counts candidates on disk for the requested pairs; `new` counts the",
        "ones this invocation created. They differ on a re-run, because the generator",
        "skips pairs whose output already exists.",
        "",
        "| corpus | requested | present | new | rc |",
        "|---|---:|---:|---:|---:|",
    ]
    lines += [
        f"| `{g.corpus}` | {g.n_requested} | {g.n_present} | {g.n_new} | {g.returncode} |"
        for g in rep.generation
    ]
    lines.append("")
    return "\n".join(lines) + "\n"


# --- driver ------------------------------------------------------------------


def _find_detail(results_dir: Path, run_id: str, benchmark: str) -> Path:
    matches = sorted(results_dir.glob(f"{run_id}__{benchmark}*.json.gz"))
    if not matches:
        raise FileNotFoundError(
            f"no detail file for run {run_id} benchmark {benchmark} under {results_dir}"
        )
    return matches[0]


def _recorded_run(jsonl: Path, run_id: str) -> dict:
    for line in jsonl.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("id_run") == run_id:
            return record
    raise LookupError(f"run {run_id} not in {jsonl}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-id", default="019fcc6f-4eb8-72f7-957e-799895a04342")
    ap.add_argument("--run-name", default="jubarte-final-lossless")
    ap.add_argument("--benchmark", default="script_redlines")
    ap.add_argument("--config", type=Path, default=_REPO / "bench.yaml")
    ap.add_argument("--results-dir", type=Path, default=_REPO / "results")
    ap.add_argument("--out-dir", type=Path, default=_REPO / "results" / "l1_partition")
    # Regenerated candidates and lens scratch are ~47 MB over ~500 files for the
    # 166-document cluster. They are reproducible from the committed report in
    # under a minute, so they belong under the already-ignored `runs/` tree and
    # NOT in `results/`, whose contents are committed as data.
    ap.add_argument(
        "--workdir",
        type=Path,
        default=None,
        help="where regenerated candidates land (default: runs/l1_partition__<run>)",
    )
    ap.add_argument("--score-field", default=DEFAULT_SCORE_FIELD)
    ap.add_argument("--low", type=float, default=CLUSTER_LOW)
    ap.add_argument("--high", type=float, default=CLUSTER_HIGH)
    ap.add_argument("--jobs", type=int, default=12)
    ap.add_argument("--min-token-docs", type=int, default=DEFAULT_MIN_TOKEN_DOCS)
    args = ap.parse_args(argv)

    detail = _find_detail(args.results_dir / "detail", args.run_id, args.benchmark)
    per_doc = load_detail(detail)
    recorded = _recorded_run(args.results_dir / "bench.jsonl", args.run_id)
    cfg = bench_config.load_config(args.config)
    matching = [r for r in cfg.runs if r.name == args.run_name]
    if not matching:
        raise LookupError(f"run {args.run_name!r} not in {args.config}")
    rc = matching[0]

    scores = scores_from_detail(per_doc, field=args.score_field)
    cluster = select_cluster(scores, low=args.low, high=args.high)
    if not cluster:
        raise SystemExit(f"empty cluster in [{args.low}, {args.high}) — nothing to partition")
    ordered = sorted(scores[c] for c in cluster)
    median = (
        ordered[len(ordered) // 2]
        if len(ordered) % 2
        else (ordered[len(ordered) // 2 - 1] + ordered[len(ordered) // 2]) / 2
    )

    rep = L1Report(
        run_id=args.run_id,
        run_name=args.run_name,
        tool_version_recorded=recorded.get("tool_version"),
        tool_version_now=(
            tool_updater.resolve_local_version(_REPO / rc.dist) if rc.dist else None
        ),
        score_field=args.score_field,
        band=(args.low, args.high),
        cluster=cluster,
        cluster_median=median,
    )
    print(f"cluster: {len(cluster)} documents in [{args.low:g}, {args.high:g}), median {median:.2f}")
    print(f"engine build: recorded {rep.tool_version_recorded} / now {rep.tool_version_now}")

    workdir = args.workdir or (_REPO / "runs" / f"l1_partition__{args.run_name}")
    workdir.mkdir(parents=True, exist_ok=True)
    rep.workdir = str(workdir.relative_to(_REPO) if workdir.is_relative_to(_REPO) else workdir)
    rep.generation, candidates = regenerate_cluster(cfg, rc, cluster, workdir)
    rep.n_candidates = len(candidates)
    for g in rep.generation:
        print(
            f"  {g.corpus}: requested {g.n_requested}, present {g.n_present} "
            f"({g.n_new} new, rc={g.returncode})"
        )
        if g.returncode != 0 and g.stderr_tail:
            print(f"    stderr: {g.stderr_tail}", file=sys.stderr)

    # Sources across EVERY declared pool, not just source_of_truth's — resolving
    # only the latter is precisely why the original run lensed 46 of 166.
    mapping_csvs = [_REPO / c.manifest for c in bench_config.corpora_for_run(cfg, rc)]
    source_dirs = [_REPO / c.source_dir for c in bench_config.corpora_for_run(cfg, rc)]
    sources = functional_lens.resolve_source_docx(mapping_csvs, source_dirs)

    tasks: list[functional_lens.CheckTask] = []
    unresolved = 0
    for key in cluster:
        cand, pair = candidates.get(key), sources.get(key)
        if cand is None or pair is None:
            unresolved += 1
            continue
        tasks.append((key, cand, pair[0], pair[1], workdir / "lens" / key))
    rep.n_unresolved_sources = unresolved
    print(f"lens: {len(tasks)} tasks ({unresolved} cluster documents unresolved)")

    verdicts = functional_lens.check_folder(tasks, jobs=args.jobs)
    rep.part = partition(verdicts)
    rep.control = compare_to_recorded(verdicts, per_doc)
    rep.gate_outcome = gate(rep.part)
    table = cross_tabulate(rep.part)
    rep.tokens = {
        b.value: top_tokens(table, b, min_docs=args.min_token_docs) for b in Bucket
    }

    args.out_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.out_dir / f"{args.run_name}.json"
    md_path = args.out_dir / f"{args.run_name}.md"
    json_path.write_text(json.dumps(_json_payload(rep), indent=2) + "\n", encoding="utf-8")
    md_path.write_text(_markdown(rep), encoding="utf-8")

    counts = rep.part.counts
    print("\nbuckets:", {b.value: counts[b] for b in Bucket})
    print(f"judged {rep.part.n_judged}, unjudged {len(rep.part.unjudged)}")
    print(f"control: {rep.control.n_agree}/{rep.control.n_compared} agree with recorded verdicts")
    print(f"GATE: {rep.gate_outcome.verdict.value.upper()} — {rep.gate_outcome.reason}")
    print(f"\nwrote {json_path}\nwrote {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
