"""Cluster lens partition (S0.1 — Stage L1 of the lossless plan).

166 documents of the lossless run sit in [40,60) with a cluster median of 51.5 —
the signature of "document preserved, change not marked". That cluster is the
single largest lever in the plan, and Stage L1 exists to find out *what it is*
before the engine is touched.

The instrument is the functional lens (``functional_lens.py``), whose two
invariants — ``accept(candidate) == next`` and ``reject(candidate) == base`` —
are already implemented there and are not reimplemented here. This module is the
partitioning layer on top: it splits the cluster by which invariants hold, and
reads one number off the split.

That number is the gate. When both invariants hold, the markup is *correct* and
the pixel scorer disagrees — a benchmark defect, not an engine defect. If that
happens on more than ~15% of the cluster, L2 would be tuning the engine against
our own scorer bug, so the gate stops the stage instead. It is the only thing
standing between the plan and the failure mode the audit exists to remove.

**Judgeable vs. bucketed.** A ``FunctionalVerdict`` may carry no verdict at all:
``None`` fields mean the check could not run, and ``blind`` means base and next
carry identical text, so both invariants hold trivially for a candidate that
does nothing. Neither is a bucket. Both are held in ``unjudged`` and kept out of
the gate's denominator — a blind document scored as "both hold" is a false STOP,
and a crashed one scored as "neither holds" is a false engine defect.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum

from neurotic_docx_bench.functional_lens import FunctionalVerdict

CLUSTER_LOW = 40.0
CLUSTER_HIGH = 60.0

BOTH_HOLD_THRESHOLD = 0.15
"""Fraction of the cluster above which the gate stops the stage (contract L1)."""

STOP_WORDS = frozenset({
    # Corpus-source prefixes: which fixture collection a pair came from, never a
    # document feature. `sd` is the SuperDoc ticket prefix (sd_2447, sd_2672).
    "behavior", "evals", "editor", "sd", "super",
    # Naming scaffolding shared by nearly every fixture — ubiquitous tokens carry
    # no information about which family a bucket belongs to (the same reason
    # mine_failure_clusters reads `lift` and not raw mass).
    "and", "doc", "docx", "document", "file", "files", "id", "test", "tests",
    "the", "with",
})
"""Tokens dropped by :func:`default_tokenizer`. A stop list is a judgement call:
too aggressive and it hides the signal, so it holds only source prefixes and
scaffolding, never anything that names an OOXML feature."""

_SPLIT = re.compile(r"[_-]+")
_CONTENT_HASH = re.compile(r"[0-9a-f]{8}")
"""Fixture names end each side with an 8-hex content hash
(``behavior__math_all_objects_36ab389c``). It is unique per fixture by
construction, so it can never group anything."""


class Bucket(StrEnum):
    """The four Stage-L1 outcomes. Only the tolerant ``*_ok`` flags decide the
    bucket: ``*_strict`` fails on the documented ``accept_changes``
    paragraph-merge limitation, which would read as an engine defect it is not.
    """

    BOTH_HOLD = "both_hold"
    """Markup correct, the SCORER disagrees — a benchmark defect. Not engine work."""
    REJECT_ONLY = "reject_only"
    """Deletions marked; insertions missing or inert."""
    ACCEPT_ONLY = "accept_only"
    """Insertions marked; deletions dropped rather than struck."""
    NEITHER = "neither"
    """No usable redline — the output is paint."""


class GateVerdict(StrEnum):
    PROCEED = "proceed"
    STOP_FIX_SCORER = "stop_fix_scorer"


@dataclass(frozen=True)
class ClusterPartition:
    """Every input document lands in exactly one of ``buckets`` or ``unjudged``.

    ``unjudged`` maps a document to why the lens could not judge it (``blind``,
    ``partial``, or ``error: …``); those documents are excluded from every rate
    computed here, never silently folded into a bucket.
    """

    buckets: Mapping[str, Bucket] = field(default_factory=dict)
    unjudged: Mapping[str, str] = field(default_factory=dict)

    @property
    def n_judged(self) -> int:
        return len(self.buckets)

    @property
    def counts(self) -> dict[Bucket, int]:
        """Population per bucket, with every bucket present at zero so a summary
        table has fixed columns whatever the run contained."""
        tally = dict.fromkeys(Bucket, 0)
        for bucket in self.buckets.values():
            tally[bucket] += 1
        return tally

    def members(self, bucket: Bucket) -> tuple[str, ...]:
        """Documents in ``bucket``, sorted by name."""
        return tuple(sorted(name for name, b in self.buckets.items() if b is bucket))


@dataclass(frozen=True)
class GateOutcome:
    """The L1 gate decision, carrying the numbers it was decided on."""

    verdict: GateVerdict
    both_hold_fraction: float
    n_both_hold: int
    n_judged: int
    reason: str


def select_cluster(
    scores: Mapping[str, float], *, low: float = CLUSTER_LOW, high: float = CLUSTER_HIGH,
) -> tuple[str, ...]:
    """Documents scoring in ``[low, high)``, sorted by name.

    The interval is half-open, so a document at exactly ``low`` is in the cluster
    and one at exactly ``high`` is not — the band boundaries tile without overlap
    and the count is reproducible. Sorting by name rather than by score keeps the
    tuple stable when documents tie, which they do in bulk at the cluster median.

    Non-numeric values are skipped, and NaN drops out on its own because it
    compares False against both bounds.
    """
    if low > high:
        raise ValueError(f"inverted band: low={low} > high={high}")
    return tuple(sorted(
        name for name, score in scores.items()
        if isinstance(score, (int, float)) and low <= float(score) < high
    ))


def _classify(verdict: FunctionalVerdict) -> Bucket | str:
    """``Bucket`` when the lens judged the document, else the reason it did not."""
    if verdict.blind:
        # Base and next carry identical text: both invariants hold for a candidate
        # that emitted nothing. Bucketing this as BOTH_HOLD is a false STOP.
        return "blind"
    if verdict.error is not None:
        return f"error: {verdict.error}"
    if verdict.accept_ok is None or verdict.reject_ok is None:
        return "partial"
    match bool(verdict.accept_ok), bool(verdict.reject_ok):
        case True, True:
            return Bucket.BOTH_HOLD
        case False, True:
            return Bucket.REJECT_ONLY
        case True, False:
            return Bucket.ACCEPT_ONLY
        case _:
            return Bucket.NEITHER


def partition(results: Mapping[str, FunctionalVerdict]) -> ClusterPartition:
    """Split per-document lens outcomes into the four Stage-L1 buckets."""
    buckets: dict[str, Bucket] = {}
    unjudged: dict[str, str] = {}
    for name, verdict in results.items():
        outcome = _classify(verdict)
        if isinstance(outcome, Bucket):
            buckets[name] = outcome
        else:
            unjudged[name] = outcome
    return ClusterPartition(buckets, unjudged)


def gate(
    partition: ClusterPartition, *, threshold: float = BOTH_HOLD_THRESHOLD,
) -> GateOutcome:
    """The L1 gate: stop the stage when the scorer, not the engine, is the defect.

    The plan's wording is that bucket 1 must *exceed* ~15% to stop, so the
    comparison is strict and the boundary itself passes. An exact ``threshold``
    ratio (3/20, 15/100) divides to precisely the ``0.15`` literal under IEEE
    rounding, so the boundary case is decidable and not luck.

    The denominator is judged documents only. Padding it with blind or crashed
    documents would dilute the fraction and let a real scorer defect through.
    """
    n_judged = partition.n_judged
    n_both_hold = partition.counts[Bucket.BOTH_HOLD]
    if not n_judged:
        # Nothing to weigh. The gate's question is "is the scorer the problem?",
        # and with no verdicts there is no evidence that it is — but L1 has not
        # characterised anything either, so the reason says so out loud.
        return GateOutcome(
            GateVerdict.PROCEED, 0.0, 0, 0,
            "no judgeable documents in the cluster — the gate had nothing to weigh "
            "and L1 has characterised nothing; treat this as L1 not having run.",
        )
    fraction = n_both_hold / n_judged
    if fraction > threshold:
        return GateOutcome(
            GateVerdict.STOP_FIX_SCORER, fraction, n_both_hold, n_judged,
            f"{n_both_hold} of {n_judged} judged documents ({fraction:.1%}) have BOTH "
            f"invariants holding, above the {threshold:.0%} threshold: the markup is "
            f"correct and the scorer disagrees. Fix the scorer before lifting the "
            f"cluster — a mean built on a scorer that under-credits correct markup "
            f"optimises the engine against our own bug.",
        )
    return GateOutcome(
        GateVerdict.PROCEED, fraction, n_both_hold, n_judged,
        f"{n_both_hold} of {n_judged} judged documents ({fraction:.1%}) have both "
        f"invariants holding, at or below the {threshold:.0%} threshold: the cluster "
        f"is an engine defect, not a scorer defect. Proceed to L2.",
    )


def default_tokenizer(name: str) -> list[str]:
    """Fixture-name tokens: lower-cased, split on ``_`` and ``-``, with stop
    words, pure-digit tokens and 8-hex content hashes removed."""
    return [
        token for raw in _SPLIT.split(name.lower())
        if (token := raw.strip())
        and token not in STOP_WORDS
        and not token.isdigit()
        and not _CONTENT_HASH.fullmatch(token)
    ]


def cross_tabulate(
    partition: ClusterPartition,
    *,
    tokenizer: Callable[[str], Iterable[str]] | None = None,
) -> dict[str, Counter[Bucket]]:
    """``{token: Counter({bucket: n_documents})}`` over judged documents.

    Attributes a bucket to a feature family: if ``rtl`` is overwhelmingly
    NEITHER, the L2 sub-work for that family is markup emission, not the
    insertion path. A token is counted **once per document** however many times
    it appears in the name — pair names concatenate both sides, so a family token
    routinely appears twice and would otherwise double-count the document.

    Tokens are not disjoint (one document carries several), so the columns sum to
    more than the bucket populations. Read it as "where to look first".
    """
    tokenize = tokenizer or default_tokenizer
    table: dict[str, Counter[Bucket]] = {}
    for name, bucket in partition.buckets.items():
        for token in set(tokenize(name)):
            table.setdefault(token, Counter())[bucket] += 1
    return table


def _flag(record: Mapping[str, object], key: str) -> bool | None:
    """A recorded lens flag, or ``None`` when absent or not a bool — a missing
    field means the check did not run, which is never a fail."""
    value = record.get(key)
    return value if isinstance(value, bool) else None


def verdicts_from_per_doc(
    per_doc: Mapping[str, Mapping[str, object]], *, keys: Sequence[str] | None = None,
) -> dict[str, FunctionalVerdict]:
    """Rebuild lens verdicts from recorded ``per_doc`` records, so the partition
    can run against a stored run without re-running the lens.

    Reads the same fields ``lens_health`` does. A record with no lens fields
    yields a partial verdict, which :func:`partition` files as unjudged rather
    than inventing a bucket for it. ``keys`` restricts the result to a cluster.
    """
    wanted = per_doc if keys is None else {k: per_doc[k] for k in keys if k in per_doc}
    verdicts: dict[str, FunctionalVerdict] = {}
    for name, record in wanted.items():
        verdicts[name] = FunctionalVerdict(
            accept_ok=_flag(record, "functional_accept_ok"),
            reject_ok=_flag(record, "functional_reject_ok"),
            accept_strict=_flag(record, "functional_accept_strict"),
            reject_strict=_flag(record, "functional_reject_strict"),
            error=err if isinstance(err := record.get("functional_error"), str) else None,
            blind=record.get("functional_blind") is True,
        )
    return verdicts
