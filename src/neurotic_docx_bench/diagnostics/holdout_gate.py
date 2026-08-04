"""S0.4 — the holdout gate (execution contract C6).

Every plan ended with "sealed 40-pair holdout once, at the end" and never said what
passes. This module is C6's answer: three checks that make "done" decidable.

- :func:`holdout_verdict` — the sealed holdout passes when its mean AND median are
  each within 5 points of the same engine's ITT figures on the visible corpus. It is
  not required to *hit* the targets (40 documents is far too small for that); it is
  required to be *consistent* with the corpus result. More than 5 points below and
  the programme's gains are corpus-specific: the verdict carries the honesty clause
  that must accompany the published figures.
- :func:`check_seal` — recompute the sealed list's checksum and compare it with what
  a result recorded, so a silently-changed holdout is detectable. Reuses
  ``oracle_manifest``'s checksum, not a second implementation of it.
- :func:`assert_single_use` — the holdout is run ONCE per engine per programme.
  Running it per stage converts it into training data and destroys the only
  overfitting check the benchmark has.

Measurement only: nothing here changes a score.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

# Reuse the repo's single checksum implementation rather than writing a second one
# (oracle_manifest.py owns the idiom: streaming SHA-256 over the file's bytes).
from neurotic_docx_bench.oracle_manifest import _sha256

DEFAULT_TOLERANCE = 5.0

# Float-representation slack ONLY — 64.01 − 59.01 is 5.000000000000007 in binary
# floating point, and a bare ``> tolerance`` would turn the documented boundary
# PASS into a spurious DIVERGENT. This is not gate.py's ``_EPS``: that one is a
# domain threshold (the render noise floor), this one is arithmetic hygiene.
_FP_SLACK = 1e-9

# Shortest recorded prefix accepted as evidence of the seal. ``cli._corpus_revision``
# records ``sha256(...)[:12]``, so short hashes are a real recorded form; anything
# below 8 hex chars is too weak to distinguish a holdout from a collision.
_MIN_PREFIX = 8

Verdict = Literal["PASS", "DIVERGENT", "UNREPRESENTATIVE"]
SealState = Literal["intact", "mismatch", "unverifiable"]


@dataclass(frozen=True)
class HoldoutVerdict:
    verdict: Verdict
    # Signed, holdout − ITT: negative means the holdout scored BELOW the corpus.
    mean_delta: float
    median_delta: float
    tolerance: float
    reason: str
    # The exact sentence that must accompany any published figure. C6 mandates it
    # for DIVERGENT and calls it non-negotiable after seeing the number; it also
    # carries a (different) sentence for UNREPRESENTATIVE. None on a PASS.
    publication_note: str | None = None

    @property
    def passed(self) -> bool:
        return self.verdict == "PASS"


@dataclass(frozen=True)
class SealStatus:
    state: SealState
    expected: str | None  # what the result recorded
    actual: str | None  # what the manifest hashes to now (None if unreadable)
    reason: str

    @property
    def intact(self) -> bool:
        return self.state == "intact"


@dataclass(frozen=True)
class RepeatUseWarning:
    engine: str
    n_uses: int
    run_ids: tuple[str, ...]
    message: str


def holdout_verdict(
    *,
    itt_mean: float,
    itt_median: float,
    holdout_mean: float,
    holdout_median: float,
    tolerance: float = DEFAULT_TOLERANCE,
) -> HoldoutVerdict:
    """Decide whether the sealed holdout corroborates the corpus ITT figures.

    **PASS** — both figures within ``tolerance``. Exactly ``tolerance`` PASSES, in
    both directions: C6 passes when the holdout is "within 5 points" and diverges
    only when it falls "more than 5 points below", so the boundary itself is
    neither. The band is closed, ``[-tolerance, +tolerance]``.

    **DIVERGENT** — either figure more than ``tolerance`` BELOW its ITT counterpart.
    The programme's gains are corpus-specific and did not generalise. The ITT
    numbers may still be published, but only alongside the holdout figures and
    ``publication_note``.

    **UNREPRESENTATIVE** — either figure more than ``tolerance`` ABOVE its ITT
    counterpart, and neither below. This is the branch C6 does not name, and the
    call made here is that it is neither a PASS nor a DIVERGENT:

    - It is not DIVERGENT, because beating the corpus is not evidence of
      overfitting; attaching the honesty clause would publish a claim the number
      does not support.
    - It is not a PASS, because the criterion is *consistency*, and consistency is
      symmetric. A 40-document sample landing 5+ points above a 763-document corpus
      is most cheaply explained by the sealed set not being a representative
      sample, or by the two figures having been computed over different universes
      or corpus vintages. Either explanation undermines the check in BOTH
      directions — including the credibility of a DIVERGENT verdict from the same
      machinery — so it must be resolved rather than published as corroboration.

    When the two figures diverge in opposite directions, DIVERGENT wins: evidence
    of non-generalisation is the more serious finding and outranks evidence of an
    unrepresentative sample.
    """
    mean_delta = holdout_mean - itt_mean
    median_delta = holdout_median - itt_median
    limit = tolerance + _FP_SLACK

    below = [
        f"{label} {itt:.2f}→{hold:.2f} ({delta:+.2f})"
        for label, itt, hold, delta in (
            ("mean", itt_mean, holdout_mean, mean_delta),
            ("median", itt_median, holdout_median, median_delta),
        )
        if delta < -limit
    ]
    above = [
        f"{label} {itt:.2f}→{hold:.2f} ({delta:+.2f})"
        for label, itt, hold, delta in (
            ("mean", itt_mean, holdout_mean, mean_delta),
            ("median", itt_median, holdout_median, median_delta),
        )
        if delta > limit
    ]

    if below:
        return HoldoutVerdict(
            "DIVERGENT",
            mean_delta=mean_delta,
            median_delta=median_delta,
            tolerance=tolerance,
            reason=(
                f"holdout more than {tolerance:g} points below ITT: "
                + ", ".join(below)
            ),
            publication_note=(
                "The programme's gains are corpus-specific and did not generalise: "
                f"on the sealed holdout this engine scores mean {holdout_mean:.2f} / "
                f"median {holdout_median:.2f} against corpus ITT mean {itt_mean:.2f} / "
                f"median {itt_median:.2f}. The ITT figures may be published only "
                "alongside the holdout figures and this statement."
            ),
        )

    if above:
        return HoldoutVerdict(
            "UNREPRESENTATIVE",
            mean_delta=mean_delta,
            median_delta=median_delta,
            tolerance=tolerance,
            reason=(
                f"holdout more than {tolerance:g} points above ITT: "
                + ", ".join(above)
            ),
            publication_note=(
                f"The sealed holdout scores mean {holdout_mean:.2f} / median "
                f"{holdout_median:.2f} against corpus ITT mean {itt_mean:.2f} / median "
                f"{itt_median:.2f} — more than {tolerance:g} points above. The sealed "
                "set is therefore not a representative sample of the corpus, and these "
                "holdout figures must not be cited as corroborating the ITT result."
            ),
        )

    return HoldoutVerdict(
        "PASS",
        mean_delta=mean_delta,
        median_delta=median_delta,
        tolerance=tolerance,
        reason=(
            f"holdout consistent with ITT within {tolerance:g} points "
            f"(mean {mean_delta:+.2f}, median {median_delta:+.2f})"
        ),
    )


def seal_checksum(manifest_path: Path) -> str:
    """SHA-256 of the sealed holdout list, in the oracle-manifest idiom."""
    return _sha256(Path(manifest_path))


def check_seal(manifest_path: Path, recorded_checksum: str | None) -> SealStatus:
    """Recompute the sealed list's checksum and compare it with the recorded one.

    Bytes, not parsed keys: the seal is the file, and reordering or re-commenting
    it is exactly the kind of quiet edit worth a second look.

    ``recorded_checksum`` may be the full 64-hex digest or the short prefix form
    ``cli._corpus_revision`` records (``[:12]``); comparison is case-insensitive.
    Anything that cannot be checked — manifest absent, nothing recorded, a prefix
    too short to be evidence — is ``unverifiable``, never ``intact``: a result that
    recorded no seal must not read as a result whose seal held.
    """
    path = Path(manifest_path)
    if not path.is_file():
        return SealStatus(
            "unverifiable",
            expected=recorded_checksum,
            actual=None,
            reason=f"holdout manifest not found: {path}",
        )

    actual = seal_checksum(path)
    recorded = (recorded_checksum or "").strip().lower()
    if not recorded:
        return SealStatus(
            "unverifiable",
            expected=recorded_checksum,
            actual=actual,
            reason="result recorded no seal checksum — the holdout cannot be verified",
        )
    if len(recorded) < _MIN_PREFIX:
        return SealStatus(
            "unverifiable",
            expected=recorded_checksum,
            actual=actual,
            reason=(
                f"recorded checksum is {len(recorded)} chars — too short to be "
                f"evidence (need {_MIN_PREFIX}+)"
            ),
        )
    if actual.startswith(recorded):
        return SealStatus(
            "intact",
            expected=recorded_checksum,
            actual=actual,
            reason=f"seal intact ({path.name} matches the recorded checksum)",
        )
    return SealStatus(
        "mismatch",
        expected=recorded_checksum,
        actual=actual,
        reason=(
            f"sealed holdout changed since the result was recorded: {path.name} "
            f"hashes to {actual[:12]}…, result recorded {recorded[:12]}…"
        ),
    )


def assert_single_use(
    runs_for_engine: Sequence[Mapping[str, object] | object],
    *,
    engine: str | None = None,
) -> RepeatUseWarning | None:
    """Detect more than one holdout run for an engine. ``None`` when clean.

    C6: the holdout is run once per engine per programme. Running it per stage
    converts it into training data and destroys the only overfitting check we have.

    ``runs_for_engine`` is the engine's recorded result lines (JSONL dicts or
    ``Results`` objects). Uses are counted by DISTINCT RUN, not by line: one
    ``bench run --holdout`` emits a line per benchmark, all sharing the ``id_run``
    the CLI assigns once per run config, and counting lines would condemn a legal
    single use. Lines without ``id_run`` fall back to ``timestamp``; a record with
    neither counts as its own use, because a false alarm is recoverable and a
    silently-missed second use is not.
    """
    seen: list[str] = []
    vendors: list[str] = []
    for i, record in enumerate(runs_for_engine):
        if _field(record, "holdout_mode") != "only":
            continue
        vendor = _field(record, "vendor")
        if isinstance(vendor, str) and vendor and vendor not in vendors:
            vendors.append(vendor)
        key = _field(record, "id_run") or _field(record, "timestamp")
        # No identity at all → count it separately rather than merge it away.
        marker = str(key) if key is not None else f"<unidentified #{i}>"
        if marker not in seen:
            seen.append(marker)

    if len(seen) <= 1:
        return None

    name = engine or ("+".join(sorted(vendors)) if vendors else "<unknown engine>")
    return RepeatUseWarning(
        engine=name,
        n_uses=len(seen),
        run_ids=tuple(seen),
        message=(
            f"HOLDOUT REUSED: {len(seen)} holdout runs recorded for {name}, but C6 "
            "allows ONE per engine per programme. Repeated use turns the sealed set "
            "into training data and destroys the only overfitting check the benchmark "
            f"has — every holdout figure for {name} after the first is uninterpretable. "
            f"Runs: {', '.join(seen)}"
        ),
    )


def _field(record: Mapping[str, object] | object, key: str) -> object:
    """Read ``key`` off a JSONL dict or a ``Results``-shaped object."""
    if isinstance(record, Mapping):
        return record.get(key)
    return getattr(record, key, None)
