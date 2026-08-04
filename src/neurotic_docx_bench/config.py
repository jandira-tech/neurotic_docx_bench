"""bench.yaml parsing (minimal for PR2; expanded to the full sequential-run schema in PR4).

PR2 needs just enough to drive a single tool: the oracle PDF dir, scoring DPI, and one or
more runs each naming a render backend and a source (a DOCX folder to render, or a PDF
folder to pass through).
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from neurotic_docx_bench.benchmarks import BENCHMARKS, BenchmarkName
from neurotic_docx_bench.memory_budget import SizeClass, size_classes_from_config


@dataclass(frozen=True)
class ScoringConfig:
    dpi: int = 144


@dataclass(frozen=True)
class CorpusEntry:
    """One (manifest, source_dir) pool that every generating run is scored on.

    ``manifest``/``source_dir`` are kept as the raw config strings, not resolved
    ``Path``s: they are shell arguments appended to a run's ``generate`` command,
    which executes with the repo root as cwd (the same base every generator's
    argparse default assumes). Resolving them would bake this checkout's absolute
    path into every recorded command line.
    """

    name: str
    manifest: str
    source_dir: str


@dataclass(frozen=True)
class RunConfig:
    name: str
    render: str  # "soffice" | "passthrough" (more in later PRs)
    docx: Path | None = None       # folder of candidate DOCX to render (soffice)
    modified: Path | None = None   # folder of already-rendered PDFs (passthrough)
    generate: str | None = None    # shell command to produce candidate docx (writes $RUN_DIR/docx)
    package: str | None = None     # npm pkg to update before running → tool_version
    python_package: str | None = None  # installed pip/uv package (e.g. superdoc-sdk) → tool_version
    dist: Path | None = None       # local tool build dir (e.g. dist/jubarte) → tool_version
    jobs: int = 12
    timeout: float = 1200.0  # soffice render timeout per document (seconds)
    harness: dict[str, Any] | None = None  # playwright profile (PR9)
    vendor: str | None = None  # benchmark vendor identity (schema v4)
    benchmarks: list[BenchmarkName] = field(default_factory=list)  # which benchmarks this run targets
    viewer: dict[str, Any] | None = None  # dependency viewer config (Task 7)
    unversioned: bool = False  # explicit opt-out of the version-pin requirement (sanity runs)
    corpora: tuple[str, ...] | None = None  # None ⇒ every corpus declared at top level


@dataclass(frozen=True)
class GenerateScript:
    """A named shell command under the yaml's ``generate_scripts`` (run via ``--generate``)."""

    name: str
    command: str


@dataclass(frozen=True)
class BenchConfig:
    source_of_truth: Path
    scoring: ScoringConfig = field(default_factory=ScoringConfig)
    runs: list[RunConfig] = field(default_factory=list)
    accepted_ground_truth: Path | None = None  # folder of accepted (changes applied) oracle DOCX
    generate_scripts: list[GenerateScript] = field(default_factory=list)
    # Per-benchmark visual oracle PDF folders. Keys are the three visual_*
    # BenchmarkNames. `visual_redlines` defaults to `source_of_truth` if unset.
    # `visual_rendering` and `visual_accepted_changes` have no default — they must
    # be declared when any run declares them.
    visual_oracles: dict[str, Path] = field(default_factory=dict)
    # Optional peak-memory budget table per corpus size class (TODO §1/§3). Absent
    # from the yaml → empty tuple; consumers fall back to
    # ``memory_budget.DEFAULT_SIZE_CLASSES``. Backward-compatible: no bench.yaml
    # change is required and the config file's hash is unaffected when omitted.
    memory_budgets: tuple[SizeClass, ...] = field(default_factory=tuple)
    # Additional oracle redline PDF dirs (the randomized file_N_file_M corpus)
    # union-indexed with source_of_truth for script_redlines matching. Kept
    # separate from source_of_truth so the visual_redlines default, provenance,
    # and every single-dir consumer stay untouched. Absent → empty tuple.
    extra_oracle_dirs: tuple[Path, ...] = field(default_factory=tuple)
    # Sealed-holdout key list (one oracle pair key per line; see
    # ``pipeline.load_holdout``). When set, normal runs EXCLUDE these keys from
    # scoring and ``bench run --holdout`` scores ONLY them — an overfitting
    # detector for the visible corpus. Absent → None (no holdout).
    holdout_list: Path | None = None
    # The corpus pools every generating run is scored on, declared ONCE so a
    # fourth pool cannot be added to one vendor and forgotten on the rest. Empty
    # ⇒ legacy behaviour: each run's ``generate`` command is executed verbatim
    # and inherits the generators' own argparse defaults.
    corpora: tuple[CorpusEntry, ...] = field(default_factory=tuple)


def corpora_for_run(cfg: BenchConfig, rc: RunConfig) -> tuple[CorpusEntry, ...]:
    """The corpus pools ``rc`` is generated over.

    A run that declares no ``corpora:`` gets **all** of them. That default is the
    whole point: silence must mean the full document set, never the first pool.
    """
    if not cfg.corpora:
        return ()
    if rc.corpora is None:
        return cfg.corpora
    by_name = {c.name: c for c in cfg.corpora}
    return tuple(by_name[n] for n in rc.corpora)


def expand_generate_commands(cfg: BenchConfig, rc: RunConfig) -> list[str]:
    """Expand ``rc.generate`` into one invocation per corpus pool.

    Every generator accepts ``--manifest``/``--source-dir`` (see
    ``generate-native-redlines.ts``, ``superdoc_gen.py``, ``redlines_gen.py``,
    ``superdoc_redlines_gen.py``), so corpus coverage is the driver's decision,
    not each run's hand-written shell chain.
    """
    if not rc.generate:
        return []
    entries = corpora_for_run(cfg, rc)
    if not entries:
        return [rc.generate]
    return [
        f"{rc.generate} "
        f"{shlex.quote(f'--manifest={c.manifest}')} "
        f"{shlex.quote(f'--source-dir={c.source_dir}')}"
        for c in entries
    ]


_KNOWN_RENDERERS = frozenset({"soffice", "passthrough", "playwright", "word"})

# Exact version pins. Anchored with \A...\z so the WHOLE string must match
# (the previous unanchored .search() accepted malformed tails like
# ``pkg==1.0.`` or ``pkg @ 1.2.3``). Forms supported: ``name@x.y.z`` (npm,
# optionally scoped ``@scope/name@x.y.z``), ``name==x.y.z`` (pip). No @latest,
# no bare names, no dist-tags. Whitespace is rejected — copy-pasting
# ``pkg @ 1.2.3`` from a registry URL is a config error, not a pin.
_NPM_PIN = re.compile(r"\A@?[A-Za-z0-9][\w.-]*(?:/[\w.-]+)?@\d[\w.+-]*\d\Z")  # name@x.y.z | @scope/name@x.y.z (version ends in a digit)
_PY_PIN = re.compile(r"\A[A-Za-z0-9][\w.-]*==\d[\w.+!*-]*\d\Z")              # name==x.y.z (version ends in a digit)


def _vendor_or_warn(name: str, raw: dict[str, Any], path: Path) -> str:
    """Return the configured ``vendor``, or fall back to ``name`` with a warning.

    A missing ``vendor:`` silently fell back to the run's ``name``, conflating the
    two and making the run invisible to ``default_benchmarks_for_vendor`` (which
    keys on vendor). The fallback stays (back-compat) but is now visible.
    """
    import warnings

    warnings.warn(
        f"{path}: run '{name}' has no 'vendor:' field; falling back to '{name}'. "
        "Set 'vendor:' explicitly so default_benchmark mapping and snapshot keys "
        "are stable.",
        stacklevel=2,
    )
    return name


def _validate_pin(path: Path, name: str, raw: dict[str, Any]) -> None:
    """Fairness invariant: every run must pin what it benchmarks.

    Exactly one of ``dist`` / ``package`` / ``python_package`` is required, and the
    package forms must carry an exact version (``pkg@x.y.z`` / ``pkg==x.y.z`` —
    never ``@latest`` or a bare name). ``unversioned: true`` is the explicit
    escape hatch for sanity runs like word-redlines-soffice.
    """
    if raw.get("unversioned"):
        return
    sources = [k for k in ("dist", "package", "python_package") if raw.get(k)]
    if len(sources) != 1:
        raise ValueError(
            f"{path}: run '{name}' must declare exactly one version pin "
            f"(dist: | package: | python_package:), got {sources or 'none'} — "
            "or set 'unversioned: true' for a sanity run",
        )
    pkg = raw.get("package")
    if pkg is not None:
        pkg = pkg.strip()
    if pkg and not _NPM_PIN.match(pkg):
        raise ValueError(
            f"{path}: run '{name}' package '{pkg}' is not pinned — use an exact "
            "'name@x.y.z' (no @latest, no bare name, no spaces)",
        )
    pypkg = raw.get("python_package")
    if pypkg is not None:
        pypkg = pypkg.strip()
    if pypkg and not _PY_PIN.match(pypkg):
        raise ValueError(
            f"{path}: run '{name}' python_package '{pypkg}' is not pinned — use an "
            "exact 'name==x.y.z' (no spaces, no trailing dot)",
        )


# Flags the driver owns once ``corpora:`` is declared. A run that writes them by
# hand is re-declaring its own document set — precisely the defect that left 8 of
# 12 generating runs on 207 pairs while 4 ran on 803, all published in the same
# comparison table.
_DRIVER_OWNED_FLAGS = ("--manifest", "--source-dir")


def _parse_corpora(path: Path, data: dict[str, Any]) -> tuple[CorpusEntry, ...]:
    raw_list = data.get("corpora") or []
    if not isinstance(raw_list, list):
        raise ValueError(f"{path}: 'corpora' must be a list of {{name, manifest, source_dir}}")
    entries: list[CorpusEntry] = []
    seen: set[str] = set()
    for i, raw in enumerate(raw_list):
        if not isinstance(raw, dict):
            raise ValueError(f"{path}: corpora[{i}] must be a mapping, got {type(raw).__name__}")
        c_name = raw.get("name")
        if not c_name:
            raise ValueError(f"{path}: corpora[{i}] is missing 'name'")
        for key in ("manifest", "source_dir"):
            if not raw.get(key):
                raise ValueError(f"{path}: corpus '{c_name}' is missing '{key}'")
        if c_name in seen:
            raise ValueError(f"{path}: duplicate corpus name '{c_name}'")
        seen.add(c_name)
        entries.append(
            CorpusEntry(name=c_name, manifest=str(raw["manifest"]), source_dir=str(raw["source_dir"])),
        )
    return tuple(entries)


def _parse_run_corpora(
    path: Path, name: str, raw: dict[str, Any], corpora: tuple[CorpusEntry, ...],
) -> tuple[str, ...] | None:
    """Per-run escape hatch: an explicit subset of the declared corpus names.

    Absent ⇒ ``None`` ⇒ every corpus. Only a run that *genuinely* applies to one
    pool names it, and it must name a pool that exists.
    """
    raw_corpora = raw.get("corpora")
    if raw_corpora is None:
        return None
    if not corpora:
        raise ValueError(
            f"{path}: run '{name}' declares 'corpora:' but the config has no top-level "
            "'corpora:' list to select from",
        )
    if not isinstance(raw_corpora, list) or not raw_corpora:
        raise ValueError(f"{path}: run '{name}' 'corpora' must be a non-empty list of corpus names")
    known = {c.name for c in corpora}
    unknown = [n for n in raw_corpora if n not in known]
    if unknown:
        raise ValueError(
            f"{path}: run '{name}' names unknown corpora {unknown} "
            f"(declared: {sorted(known)})",
        )
    return tuple(raw_corpora)


def _validate_generate_owns_no_corpus_flags(path: Path, name: str, generate: str | None) -> None:
    """The driver expands across corpora; a run must not pick its own pool."""
    if not generate:
        return
    hardcoded = [f for f in _DRIVER_OWNED_FLAGS if f in generate]
    if hardcoded:
        raise ValueError(
            f"{path}: run '{name}' hardcodes {hardcoded} in its 'generate' command. "
            "The driver expands generate once per top-level corpus — remove the flags, "
            "and use the run's 'corpora:' list to restrict the pools instead.",
        )


def load_config(path: Path | str) -> BenchConfig:
    """Parse a bench.yaml file into a :class:`BenchConfig`.

    - ``source_of_truth``: path to the committed oracle PDF dir (required).
    - ``scoring.dpi``: int, default 144.
    - ``runs``: list; each item requires ``name`` and ``render``; optional ``docx``,
      ``modified``, ``generate``, ``package``, ``jobs`` (default 12), ``harness``.
    - Relative paths resolve against the bench.yaml's parent directory.
    - Raise ``ValueError`` on: missing ``source_of_truth``, a run without ``name`` or
      ``render``, or an unknown ``render`` backend name.
    """
    path = Path(path)
    base = path.parent
    data = yaml.safe_load(path.read_text()) or {}

    def _resolve(value: str | None) -> Path | None:
        if value is None:
            return None
        p = Path(value)
        return p if p.is_absolute() else (base / p)

    sot = data.get("source_of_truth")
    if not sot:
        raise ValueError(f"{path}: 'source_of_truth' is required")
    source_of_truth = _resolve(sot)
    assert source_of_truth is not None

    scoring_raw = data.get("scoring") or {}
    scoring = ScoringConfig(dpi=int(scoring_raw.get("dpi", 144)))

    corpora = _parse_corpora(path, data)

    runs: list[RunConfig] = []
    for i, raw in enumerate(data.get("runs") or []):
        name = raw.get("name")
        render = raw.get("render")
        if not name:
            raise ValueError(f"{path}: runs[{i}] is missing 'name'")
        if not render:
            raise ValueError(f"{path}: run '{name}' is missing 'render'")
        if render not in _KNOWN_RENDERERS:
            raise ValueError(
                f"{path}: run '{name}' has unknown render backend '{render}' "
                f"(known: {', '.join(sorted(_KNOWN_RENDERERS))})",
            )
        _validate_pin(path, name, raw)
        run_corpora = _parse_run_corpora(path, name, raw, corpora)
        if corpora:
            _validate_generate_owns_no_corpus_flags(path, name, raw.get("generate"))
        # Validate benchmark names if provided
        raw_benchmarks = raw.get("benchmarks") or []
        unknown_benchmarks = [b for b in raw_benchmarks if b not in BENCHMARKS]
        if unknown_benchmarks:
            raise ValueError(
                f"{path}: run '{name}' has unknown benchmark(s): {unknown_benchmarks}. "
                f"Known: {list(BENCHMARKS)}",
            )
        runs.append(
            RunConfig(
                name=name,
                render=render,
                docx=_resolve(raw.get("docx")),
                modified=_resolve(raw.get("modified")),
                generate=raw.get("generate"),
                package=raw.get("package"),
                python_package=raw.get("python_package"),
                dist=_resolve(raw.get("dist")),
                vendor=raw.get("vendor") or _vendor_or_warn(name, raw, path),
                benchmarks=list(raw_benchmarks),
                viewer=raw.get("viewer"),
                jobs=int(raw.get("jobs", 12)),
                timeout=float(raw.get("timeout", 1200.0)),
                harness=raw.get("harness"),
                unversioned=bool(raw.get("unversioned", False)),
                corpora=run_corpora,
            ),
        )

    scripts: list[GenerateScript] = []
    for i, raw in enumerate(data.get("generate_scripts") or []):
        s_name = raw.get("name")
        s_cmd = raw.get("command")
        if not s_name:
            raise ValueError(f"{path}: generate_scripts[{i}] is missing 'name'")
        if not s_cmd:
            raise ValueError(f"{path}: generate_scripts '{s_name}' is missing 'command'")
        scripts.append(GenerateScript(name=s_name, command=s_cmd))

    raw_visual = data.get("visual_oracles") or {}
    visual_oracles: dict[str, Path] = {}
    for vname, vp in raw_visual.items():
        resolved = _resolve(vp)
        if resolved is None or not resolved.is_dir():
            raise ValueError(
                f"{path}: visual_oracles.{vname} not found or not a directory: {vp}",
            )
        visual_oracles[vname] = resolved
    # visual_redlines defaults to source_of_truth if not explicitly declared.
    if "visual_redlines" not in visual_oracles:
        visual_oracles["visual_redlines"] = source_of_truth

    extra_raw = data.get("extra_oracle_dirs") or []
    if not isinstance(extra_raw, list):
        raise ValueError(f"{path}: 'extra_oracle_dirs' must be a list of paths")
    extra_oracle_dirs: list[Path] = []
    for entry in extra_raw:
        resolved_extra = _resolve(entry)
        if resolved_extra is None or not resolved_extra.is_dir():
            raise ValueError(
                f"{path}: extra_oracle_dirs entry not found or not a directory: {entry}",
            )
        extra_oracle_dirs.append(resolved_extra)

    holdout_raw = data.get("holdout_list")
    holdout_list = _resolve(holdout_raw)
    if holdout_list is not None and not holdout_list.is_file():
        raise ValueError(f"{path}: holdout_list not found: {holdout_raw}")

    return BenchConfig(
        source_of_truth=source_of_truth,
        scoring=scoring,
        runs=runs,
        accepted_ground_truth=_resolve(data.get("accepted_ground_truth")),
        generate_scripts=scripts,
        visual_oracles=visual_oracles,
        memory_budgets=size_classes_from_config(data.get("memory_budgets") or []),
        extra_oracle_dirs=tuple(extra_oracle_dirs),
        holdout_list=holdout_list,
        corpora=corpora,
    )


def environment_config_for_run(cfg: BenchConfig, run_name: str) -> BenchConfig:
    """Return a :class:`BenchConfig` filtered to only the named run.

    The JSONL ``environment_config`` field should be self-contained for
    reproducibility but must not redundantly embed every other vendor's run
    config.  The shared environment (``source_of_truth``, ``scoring``,
    ``accepted_ground_truth``, ``generate_scripts``) is preserved; only
    ``runs`` is narrowed to the single matching :class:`RunConfig`.
    """
    matching = [r for r in cfg.runs if r.name == run_name]
    if not matching:
        raise ValueError(
            f"No run named {run_name!r} in config (available: "
            f"{[r.name for r in cfg.runs]})",
        )
    return BenchConfig(
        source_of_truth=cfg.source_of_truth,
        scoring=cfg.scoring,
        runs=matching,
        accepted_ground_truth=cfg.accepted_ground_truth,
        generate_scripts=cfg.generate_scripts,
        visual_oracles=cfg.visual_oracles,
        memory_budgets=cfg.memory_budgets,
        extra_oracle_dirs=cfg.extra_oracle_dirs,
        holdout_list=cfg.holdout_list,
        corpora=cfg.corpora,
    )
