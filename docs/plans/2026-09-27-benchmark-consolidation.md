# Benchmark Consolidation Implementation Plan

> Solo execution. Steps use checkbox (`- [ ]`) syntax for tracking. Every task is red-green: write the failing test, watch it fail for the stated reason, write the minimum, watch it pass, commit. Each PR stacks on the previous one (branch over branch). Commands assume the repo root on the mac (`/Users/arthrod/temp/T/neurotic_docx_bench`) unless a step says otherwise.

**Goal:** One canonical result store, one vendor registry, one Python report generator, one stated ranking policy applied identically to every tool (the author's included), with fixed denominators, honest failure accounting, provenance on every row (pin, corpus document set, renderer, scorer, hardware, date), and paired-bootstrap uncertainty on the headline tables.

**Architecture:** A new `neurotic_docx_bench.ledger` package (named `ledger`, not `report`, because `neurotic_docx_bench/report.py` is part of the parity-locked scoring core lifted from superdoc-visual-benchmarks) (pydantic models, pure functions) reads every existing store (`results/bench.jsonl`, `results/speed.jsonl`, `results/redline_speed_bench/**/summary.json`, converter reports) through a registry that maps run names, vendor strings, speed tool names and converter tool names to one `tool_id` each. The write side (`results_schema.Results`, `cli._emit_and_gate_benchmark`) gains the provenance fields the policy needs. `bench report` renders `RESULTS.md`, `RESULTS_DETAILED.md` and the README vendor table; the TypeScript generator, `scripts/export-results-md.py`, the `--update-readme` flags and `docs/RESULTS.md` are retired once their behaviours are covered by pytest.

**Tech Stack:** Python 3.14 via `uv`, pydantic v2, pyyaml, numpy (bootstrap), typer + rich (existing CLI), pytest with `pytest-cov`, `ty` and `ruff` for type and lint, vitest for the two small TypeScript changes.

---

## Decisions taken for this plan (each reversible, each stated once)

These are my calls where your proposal (`docs/plans/proposed/asr-sep-27-2026.md`) and the evidence in steps 1 to 3 diverge. Change a decision and the affected task is named next to it.

| # | Decision | Alternative rejected | Affects |
| --- | --- | --- | --- |
| D1 | Headline tables show one row per tool configuration: the latest eligible run of that tool. No best/worst pin, no best-of-N run. Pin history moves to the detailed view. Author-affiliated tools carry a marker and follow the same rule. | Jubarte best+worst, other vendors every pin (current). | Task 8 |
| D2 | The renderer is an axis of the comparability key (`renderer_id`), never a deprecation. LibreOffice rows stay the CI-reproducible group; Word-rendered rows form their own group when they exist. | Deprecate soffice, Word only. | Task 6 |
| D3 | Scorers are lenses. Each benchmark declares one primary lens that ranks; docxide_metrics becomes a lens over the same converter rows and must be run for every converter to appear in a headline. No merged number. | Merge SuperDoc scorer and docxide metrics into one. | Tasks 3, 11 |
| D4 | Failure policy: fidelity is intent-to-treat with fixed denominators; speed rows report completion and rank only at the canonical fixture count. No corpus-size-scaled penalty. | Smaller penalty for small corpora. | Tasks 4, 5, 7 |
| D5 | New benchmark families (text extraction, rasterization, editing operations), rubric lenses and the side-by-side viewer come after this plan and plug into the registry and schema it builds. | Build them now. | none (out of scope) |
| D6 | Rows without `corpus_revision`, holdout-only rows, retracted rows and non-canonical `score_config` rows are archived: readable, listed in history, never ranked. | Keep as "legacy" ranked tables. | Tasks 12, 13 |

---

## Verified facts this plan relies on (from the repository on 2026-09-27)

- `results/bench.jsonl`: 96 lines, 56 stamped with `corpus_revision`, 53 with per-doc `scores`, ~1 MB per stamped line. `Results` dataclass in `src/neurotic_docx_bench/results_schema.py`.
- `aggregate.compute_aggregate_itt` keeps a doc's score when a failure record also names it; `n_failures = len(failures)`. Eight published rows violate `Docs + Failures = ITT Docs` because of this.
- `cli._corpus_revision` (line 1083) hashes `oracle_manifest.json`, which covers every oracle directory, so the stamp changes for all benchmarks whenever any oracle changes.
- `scripts/update-readme-ranking.ts` picks the best run per (family, benchmark, version) by `[renderFit, n_docs, itt_median, timestamp]`; `scripts/export-results-md.py::_rank` picks the newest. Two policies, two views.
- `pipeline.match_accepted_to_candidate` and `match_by_stem` score oracle ∩ candidate; a missing candidate leaves the denominator.
- Speed rows (`results/speed.jsonl`, 96 lines; 19 `summary.json` files) have no tool version and no hardware.
- Converter tables are rewritten from whichever report JSON the last `--update-readme` run produced (`cli.py` lines 590 to 703).
- `bench.yaml` has 23 runs; `jubarte-final-native` now carries `vendor: jubarte-ast`, earlier lines carry `vendor: jubarte` with the same run name.
- `tests/` is pytest with `-n 12` by default (`pyproject.toml`); vitest is scoped to `scripts/**/*.test.ts`.

---

## File structure

Created:

- `bench.registry.yaml` (repo root): the vendor registry data.
- `src/neurotic_docx_bench/ledger/__init__.py`
- `src/neurotic_docx_bench/ledger/registry.py`: `ToolEntry`, `Registry`, `load_registry`.
- `src/neurotic_docx_bench/ledger/pins.py`: `ToolPin` parsing of every version-string shape in the store.
- `src/neurotic_docx_bench/ledger/rows.py`: `ResultRow`, `SpeedRow`, loaders for the three stores.
- `src/neurotic_docx_bench/ledger/docset.py`: document-set keys and `docset_id` per benchmark.
- `src/neurotic_docx_bench/ledger/policy.py`: eligibility, comparability groups, headline selection, retractions.
- `src/neurotic_docx_bench/ledger/stats.py`: bootstrap intervals (per-row median CI, paired difference CI).
- `src/neurotic_docx_bench/ledger/tables.py`: markdown rendering.
- `src/neurotic_docx_bench/ledger/build.py`: orchestration, file writers.
- `src/neurotic_docx_bench/ledger/archive.py`: store split and retraction ledger.
- `src/neurotic_docx_bench/hardware.py`: hardware fingerprint for provenance.
- `scripts/lib/provenance.ts` + `scripts/lib/provenance.test.ts`: tool version and hardware for speed rows.
- `results/docsets.json`, `results/retractions.jsonl`, `results/converters.jsonl`, `results/archive/` (data, produced by commands in Tasks 5, 11, 12).
- Tests: `tests/test_ledger_registry.py`, `tests/test_ledger_pins.py`, `tests/test_ledger_rows.py`, `tests/test_ledger_docset.py`, `tests/test_ledger_policy.py`, `tests/test_ledger_stats.py`, `tests/test_ledger_tables.py`, `tests/test_ledger_build.py`, `tests/test_ledger_archive.py`, `tests/test_hardware.py`, `tests/test_failure_accounting.py`, `tests/test_store_invariants.py`.

Modified:

- `src/neurotic_docx_bench/aggregate.py`: `failed_doc_keys`.
- `src/neurotic_docx_bench/results_schema.py`: new provenance fields on `Results`, `build_results`.
- `src/neurotic_docx_bench/emit/jsonl.py`: pass-through of the new fields.
- `src/neurotic_docx_bench/cli.py`: `_emit_and_gate_benchmark` (docset, missing-output failures, renderer, hardware), new commands `report`, `docset`, `archive`, `retract`, `calibrate`, `ingest-converter-reports`; removal of `--update-readme`.
- `src/neurotic_docx_bench/docx_to_pdf.py`, `src/neurotic_docx_bench/docxide_metrics.py`: append rows to `results/converters.jsonl`.
- `scripts/redline_speed_bench.ts`, `scripts/speed-bench.ts`: rows carry `tool_version` and `hardware`.
- `README.md`: vendor table between markers, methodology text corrected.
- `pyproject.toml`: `pydantic`, `pytest-cov`.

Deleted (Task 13, after coverage migrates): `scripts/update-readme-ranking.ts`, `scripts/update-readme-ranking.test.ts`, `scripts/export-results-md.py`, `tests/test_export_results_md.py`, `docs/RESULTS.md`, the `update-readme-ranking` npm script.

---

## Conventions for every task

- Run Python tests as `uv run pytest <file> -q -n 0` while iterating on one file; full suite with coverage as `uv run pytest --cov=src/neurotic_docx_bench --cov-report=term-missing --cov-branch -q` before each commit.
- Lint and types before each commit: `uv run ruff check src tests && uv run ruff format --check src tests && uv run ty check src`.
- One branch per PR, stacked: `consolidate/01-registry` from `bench/latest-competitors-0926`, `consolidate/02-failures` from `consolidate/01-registry`, and so on. Push after each task's commit: `git push -u origin <branch>`.
- Commit messages: `type(scope): imperative summary`, body states the invariant the change enforces.
- No em dashes anywhere in code comments, docstrings, or generated markdown.

---

## PR 1: registry, pins, normalized rows (read side only, no behaviour change)

### Task 0: Branch and tooling

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Create the branch**

```bash
git checkout bench/latest-competitors-0926
git checkout -b consolidate/01-registry
```

- [ ] **Step 2: Add pydantic and pytest-cov**

```bash
uv add "pydantic>=2.11"
uv add --group dev "pytest-cov>=6.0"
```

Expected: `pyproject.toml` `dependencies` gains `"pydantic>=2.11"`, `[dependency-groups].dev` gains `"pytest-cov>=6.0"`, `uv.lock` updated.

- [ ] **Step 3: Verify the suite still runs with coverage enabled**

Run: `uv run pytest tests/test_itt.py --cov=src/neurotic_docx_bench --cov-report=term-missing --cov-branch -q -n 0`
Expected: `9 passed`, a coverage table printed (any percentage; this only proves the plugin loads).

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "build: add pydantic and pytest-cov for the report package"
```

---

### Task 1: Vendor registry

**Files:**
- Create: `bench.registry.yaml`
- Create: `src/neurotic_docx_bench/ledger/__init__.py` (empty)
- Create: `src/neurotic_docx_bench/ledger/registry.py`
- Test: `tests/test_ledger_registry.py`

- [ ] **Step 1: Write the failing tests**

```python
"""Vendor registry: one tool_id per run name, bench vendor, speed tool and converter tool."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from neurotic_docx_bench.ledger import registry as reg

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "bench.registry.yaml"


def _write(tmp_path: Path, doc: dict) -> Path:
    p = tmp_path / "bench.registry.yaml"
    p.write_text(yaml.safe_dump(doc, sort_keys=False))
    return p


def _minimal(**overrides) -> dict:
    tool = {
        "id": "acme",
        "vendor": "acme",
        "display": "acme",
        "role": "generator",
        "engine": "acme-core",
        "run_names": ["acme"],
        "bench_vendors": ["acme"],
    }
    tool.update(overrides)
    return {"schema_version": 1, "tools": [tool]}


def test_load_minimal_registry(tmp_path: Path) -> None:
    r = reg.load_registry(_write(tmp_path, _minimal()))
    assert r.by_id("acme").display == "acme"
    assert r.by_id("acme").affiliated is False
    assert r.by_id("acme").status == "active"


def test_unknown_id_raises(tmp_path: Path) -> None:
    r = reg.load_registry(_write(tmp_path, _minimal()))
    with pytest.raises(KeyError):
        r.by_id("nope")


def test_duplicate_ids_rejected(tmp_path: Path) -> None:
    doc = _minimal()
    doc["tools"].append(dict(doc["tools"][0]))
    with pytest.raises(ValueError, match="duplicate tool id"):
        reg.load_registry(_write(tmp_path, doc))


def test_run_name_claimed_twice_rejected(tmp_path: Path) -> None:
    doc = _minimal()
    other = dict(doc["tools"][0], id="acme2", bench_vendors=["acme2"])
    doc["tools"].append(other)
    with pytest.raises(ValueError, match="run name 'acme' claimed by"):
        reg.load_registry(_write(tmp_path, doc))


def test_resolve_bench_prefers_run_name_over_vendor(tmp_path: Path) -> None:
    doc = _minimal(run_names=["jubarte-final-lossless"], bench_vendors=["jubarte"], id="jubarte-lossless")
    doc["tools"].append({
        "id": "jubarte-ast",
        "vendor": "jubarte",
        "display": "jubarte (ast)",
        "role": "generator",
        "engine": "jubarte-final",
        "run_names": ["jubarte-final-native"],
        "bench_vendors": ["jubarte-ast"],
    })
    r = reg.load_registry(_write(tmp_path, doc))
    # Old lines: vendor "jubarte" + run name "jubarte-final-native" must land on jubarte-ast.
    hit = r.resolve_bench(vendor="jubarte", run_name="jubarte-final-native", render="soffice")
    assert hit is not None and hit.id == "jubarte-ast"
    # Vendor fallback when the run name is unknown.
    hit = r.resolve_bench(vendor="jubarte", run_name="something-else", render="soffice")
    assert hit is not None and hit.id == "jubarte-lossless"


def test_resolve_bench_playwright_falls_back_to_editor_entry(tmp_path: Path) -> None:
    doc = _minimal(id="docxodus", bench_vendors=["docxodus"], run_names=["docxodus"])
    doc["tools"].append({
        "id": "docxodus-viewer",
        "vendor": "docxodus",
        "display": "docxodus (viewer)",
        "role": "editor",
        "engine": "react-docxodus-viewer",
        "run_names": ["docxodus-playwright-rendering"],
        "bench_vendors": ["docxodus"],
    })
    r = reg.load_registry(_write(tmp_path, doc))
    hit = r.resolve_bench(vendor="docxodus", run_name="legacy-harness", render="playwright")
    assert hit is not None and hit.id == "docxodus-viewer"
    hit = r.resolve_bench(vendor="docxodus", run_name="legacy-harness", render="soffice")
    assert hit is not None and hit.id == "docxodus"


def test_resolve_speed_strips_inproc_suffix(tmp_path: Path) -> None:
    doc = _minimal(id="jubarte-rust", speed_tools=["jubarte-rust"], bench_vendors=["jubarte-rust"])
    r = reg.load_registry(_write(tmp_path, doc))
    entry, inproc = r.resolve_speed("jubarte-rust-inproc")
    assert entry is not None and entry.id == "jubarte-rust" and inproc is True
    entry, inproc = r.resolve_speed("jubarte-rust")
    assert entry is not None and inproc is False
    assert r.resolve_speed("nobody") == (None, False)


def test_resolve_converter(tmp_path: Path) -> None:
    doc = _minimal(id="pdfitdown", role="converter", engine="office2pdf", converter_tools=["pdfitdown"])
    r = reg.load_registry(_write(tmp_path, doc))
    hit = r.resolve_converter("pdfitdown")
    assert hit is not None and hit.engine == "office2pdf"
    assert r.resolve_converter("nobody") is None


def test_not_applicable_lists_benchmarks(tmp_path: Path) -> None:
    doc = _minimal(id="doxx", role="converter", not_applicable=["docx_to_pdf"])
    r = reg.load_registry(_write(tmp_path, doc))
    assert r.by_id("doxx").applies_to("docx_to_pdf") is False
    assert r.by_id("doxx").applies_to("script_redlines") is True


def test_unknown_field_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        reg.load_registry(_write(tmp_path, _minimal(typo_field=1)))


# ---- the committed registry --------------------------------------------------

@pytest.mark.skipif(not REGISTRY_PATH.is_file(), reason="bench.registry.yaml absent")
def test_committed_registry_loads_and_covers_bench_yaml_runs() -> None:
    r = reg.load_registry(REGISTRY_PATH)
    cfg = yaml.safe_load((ROOT / "bench.yaml").read_text())
    missing = [
        run["name"]
        for run in cfg["runs"]
        if r.resolve_bench(vendor=run.get("vendor") or run["name"], run_name=run["name"], render=run.get("render", "soffice")) is None
    ]
    assert missing == [], f"bench.yaml runs with no registry entry: {missing}"


@pytest.mark.skipif(not REGISTRY_PATH.is_file(), reason="bench.registry.yaml absent")
def test_committed_registry_marks_author_tools() -> None:
    r = reg.load_registry(REGISTRY_PATH)
    affiliated = sorted(t.id for t in r.tools if t.affiliated)
    assert {"jubarte-lossless", "jubarte-ast", "jubarte-rust", "jubarte-wasm", "jubarte-pdf"} <= set(affiliated)
    assert r.by_id("docxodus").affiliated is False
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_ledger_registry.py -q -n 0`
Expected: `ImportError` / `ModuleNotFoundError: No module named 'neurotic_docx_bench.ledger'`.

- [ ] **Step 3: Write the registry module**

`src/neurotic_docx_bench/ledger/__init__.py`: empty file.

`src/neurotic_docx_bench/ledger/registry.py`:

```python
"""Vendor registry: the single source of truth for tool identity.

Every store the report reads names tools differently: ``bench.jsonl`` has a
``vendor`` string plus a run name inside ``environment_config``, speed rows have a
``tool`` string that may carry an ``-inproc`` suffix, converter reports have their
own ``tool`` key. The registry maps each of those spellings to exactly one
``tool_id`` and carries the facts the tables need (display name, role, engine,
author affiliation, benchmarks the tool cannot perform).
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, model_validator

Role = Literal["generator", "editor", "converter", "calibration"]
Status = Literal["active", "retired"]

DEFAULT_REGISTRY_PATH = Path("bench.registry.yaml")
_INPROC_SUFFIX = "-inproc"


class ToolEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    vendor: str
    display: str
    role: Role
    engine: str
    affiliated: bool = False
    status: Status = "active"
    configuration: str | None = None
    run_names: tuple[str, ...] = ()
    bench_vendors: tuple[str, ...] = ()
    speed_tools: tuple[str, ...] = ()
    converter_tools: tuple[str, ...] = ()
    not_applicable: tuple[str, ...] = ()
    url: str | None = None
    note: str | None = None

    def applies_to(self, benchmark: str) -> bool:
        return benchmark not in self.not_applicable


class Registry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int
    tools: tuple[ToolEntry, ...]

    @model_validator(mode="after")
    def _unique_claims(self) -> Registry:
        ids: set[str] = set()
        claims: dict[str, dict[str, str]] = {
            "run name": {},
            "speed tool": {},
            "converter tool": {},
        }
        for t in self.tools:
            if t.id in ids:
                raise ValueError(f"duplicate tool id {t.id!r}")
            ids.add(t.id)
            for label, names in (
                ("run name", t.run_names),
                ("speed tool", t.speed_tools),
                ("converter tool", t.converter_tools),
            ):
                for name in names:
                    owner = claims[label].get(name)
                    if owner is not None:
                        raise ValueError(f"{label} {name!r} claimed by {owner!r} and {t.id!r}")
                    claims[label][name] = t.id
        return self

    def by_id(self, tool_id: str) -> ToolEntry:
        for t in self.tools:
            if t.id == tool_id:
                return t
        raise KeyError(tool_id)

    def resolve_bench(self, *, vendor: str, run_name: str, render: str) -> ToolEntry | None:
        """Run name first (most specific), then bench vendor. A playwright render
        prefers an editor entry for that vendor, a soffice render a non-editor one."""
        for t in self.tools:
            if run_name in t.run_names:
                return t
        want_editor = render == "playwright"
        candidates = [t for t in self.tools if vendor in t.bench_vendors]
        preferred = [t for t in candidates if (t.role == "editor") == want_editor]
        if preferred:
            return preferred[0]
        return candidates[0] if candidates else None

    def resolve_speed(self, tool: str) -> tuple[ToolEntry | None, bool]:
        inproc = tool.endswith(_INPROC_SUFFIX)
        base = tool[: -len(_INPROC_SUFFIX)] if inproc else tool
        for t in self.tools:
            if base in t.speed_tools or tool in t.speed_tools:
                return t, inproc
        return None, False

    def resolve_converter(self, tool: str) -> ToolEntry | None:
        for t in self.tools:
            if tool in t.converter_tools:
                return t
        return None


def load_registry(path: Path = DEFAULT_REGISTRY_PATH) -> Registry:
    raw = yaml.safe_load(Path(path).read_text())
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: registry must be a mapping")
    return Registry.model_validate(raw)
```

- [ ] **Step 4: Write the committed registry**

`bench.registry.yaml`:

```yaml
schema_version: 1
tools:
  # ---- redline generators (author-affiliated) ----
  - id: jubarte-lossless
    vendor: jubarte
    display: "jubarte (lossless)"
    role: generator
    engine: jubarte-final
    configuration: lossless
    affiliated: true
    run_names: [jubarte-final-lossless]
    bench_vendors: [jubarte]
    speed_tools: [jubarte-lossless, jubarte-final-lossless]
    url: https://github.com/jandira-tech/jubarte-redlines
  - id: jubarte-ast
    vendor: jubarte
    display: "jubarte (ast)"
    role: generator
    engine: jubarte-final
    configuration: ast
    affiliated: true
    run_names: [jubarte-final-native]
    bench_vendors: [jubarte-ast]
    speed_tools: [jubarte-native, jubarte-final-native]
    url: https://github.com/jandira-tech/jubarte-redlines
  - id: jubarte-rust
    vendor: jubarte
    display: jubarte-rust
    role: generator
    engine: jubarte-redlines
    affiliated: true
    run_names: [jubarte-rust]
    bench_vendors: [jubarte-rust, jubarte-rs]
    speed_tools: [jubarte-rust]
    url: https://github.com/jandira-tech/jubarte-redlines
  - id: jubarte-wasm
    vendor: jubarte
    display: jubarte-wasm
    role: generator
    engine: jubarte-redlines
    configuration: wasm
    affiliated: true
    run_names: [jubarte-wasm]
    bench_vendors: [jubarte-wasm]
    speed_tools: [jubarte-wasm]
    url: https://github.com/jandira-tech/jubarte-redlines
  # ---- redline generators (third party) ----
  - id: docxodus
    vendor: docxodus
    display: docxodus
    role: generator
    engine: docxodus
    run_names: [docxodus]
    bench_vendors: [docxodus]
    speed_tools: [docxodus]
    url: https://github.com/JSv4/docxodus
  - id: docxodus-csharp
    vendor: docxodus
    display: "docxodus (C#)"
    role: generator
    engine: docxodus
    configuration: csharp
    speed_tools: [docxodus-csharp]
    note: "C# build of docxodus; speed benchmark only."
    url: https://github.com/JSv4/docxodus
  - id: folio
    vendor: folio
    display: folio
    role: generator
    engine: "@stll/folio-core"
    run_names: [folio]
    bench_vendors: [folio]
    url: https://github.com/stella/folio
  - id: superdoc
    vendor: superdoc
    display: superdoc
    role: generator
    engine: superdoc-sdk
    run_names: [superdoc, superdoc-ts, superdoc-native]
    bench_vendors: [superdoc]
    speed_tools: [superdoc]
    url: https://github.com/Harbour-Enterprises/SuperDoc
  - id: docx-redline-js
    vendor: docx-redline-js
    display: docx-redline-js
    role: generator
    engine: docx-redline-js
    run_names: [docx-redline-js]
    bench_vendors: [docx-redline-js]
    speed_tools: [docx-redline-js]
    url: https://github.com/AnsonLai/docx-redline-js
  - id: redlines
    vendor: redlines
    display: redlines
    role: generator
    engine: redlines
    run_names: [redlines]
    bench_vendors: [redlines]
    url: https://github.com/houfu/redlines
  - id: superdoc-redlines
    vendor: superdoc-redlines
    display: superdoc-redlines
    role: generator
    engine: superdoc-redlines
    run_names: [superdoc-redlines]
    bench_vendors: [superdoc-redlines]
    url: https://github.com/yuch85/superdoc-redlines
  - id: stemma
    vendor: stemma
    display: stemma
    role: generator
    engine: stemma
    run_names: [stemma]
    bench_vendors: [stemma]
    url: https://github.com/stemma-sh/stemma
  - id: safe-docx
    vendor: safe-docx
    display: safe-docx
    role: generator
    engine: safe-docx
    run_names: [safe-docx-compare]
    bench_vendors: [safe-docx]
    url: https://github.com/UseJunior/safe-docx
  # ---- editors (playwright renders) ----
  - id: docxodus-viewer
    vendor: docxodus
    display: "docxodus (viewer)"
    role: editor
    engine: react-docxodus-viewer
    run_names: [docxodus-playwright-rendering, docxodus-playwright-redlines, docxodus-playwright-accepted]
    bench_vendors: [docxodus]
    url: https://github.com/JSv4/react-docxodus-viewer
  - id: folio-viewer
    vendor: folio
    display: "folio (viewer)"
    role: editor
    engine: "@stll/folio-react"
    run_names: [folio-playwright-rendering, folio-playwright-redlines, folio-playwright-accepted]
    bench_vendors: [folio]
    url: https://github.com/stella/folio
  - id: superdoc-editor
    vendor: superdoc
    display: "superdoc (editor)"
    role: editor
    engine: superdoc
    run_names: [superdoc-playwright-rendering, superdoc-playwright-redlines, superdoc-playwright-accepted]
    bench_vendors: [superdoc]
    url: https://github.com/Harbour-Enterprises/SuperDoc
  # ---- DOCX to PDF converters ----
  - id: jubarte-pdf
    vendor: jubarte
    display: jubarte
    role: converter
    engine: jubarte-redlines
    affiliated: true
    converter_tools: [jubarte]
    url: https://github.com/jandira-tech/jubarte-redlines
  - id: rdocx
    vendor: rdocx
    display: rdocx
    role: converter
    engine: rdocx
    converter_tools: [rdocx]
    url: https://github.com/tensorbee/rdocx
  - id: office2pdf
    vendor: office2pdf
    display: office2pdf
    role: converter
    engine: office2pdf (Typst)
    converter_tools: [office2pdf]
    url: https://github.com/developer0hye/office2pdf
  - id: pdfitdown
    vendor: pdfitdown
    display: pdfitdown
    role: converter
    engine: office2pdf (Typst)
    converter_tools: [pdfitdown]
    note: "Delegates Office formats to office2pdf; same engine, listed for completeness."
    url: https://github.com/AstraBert/PdfItDown
  - id: doxx
    vendor: doxx
    display: doxx
    role: converter
    engine: doxx
    converter_tools: [doxx]
    not_applicable: [docx_to_pdf, docx_to_pdf_no_redline_docs, docxide_metrics]
    note: "No PDF export; listed as not applicable, never ranked."
    url: https://github.com/bgreenwell/doxx
  - id: libreoffice_convert_rust
    vendor: libreoffice_convert_rust
    display: libreoffice_convert_rust
    role: converter
    engine: LibreOffice
    converter_tools: [libreoffice_convert_rust]
    url: https://gitcode.com/dnrops/libreoffice_convert_rust
  - id: dxpdf
    vendor: dxpdf
    display: dxpdf
    role: converter
    engine: dxpdf
    converter_tools: [dxpdf]
    url: https://github.com/nerdy-pro/dxpdf
  - id: docxide-pdf
    vendor: docxide-pdf
    display: docxide-pdf
    role: converter
    engine: docxide-pdf
    converter_tools: [docxide-pdf]
    url: https://github.com/sverrejb/docxide-pdf
  # ---- calibration rows (never ranked, always shown) ----
  - id: oracle-identity
    vendor: bench
    display: "oracle DOCX (identity)"
    role: calibration
    engine: pipeline
    run_names: [oracle-identity]
    bench_vendors: [oracle-identity]
    note: "The oracle DOCX through the candidate pipeline; must score 100."
  - id: null-baseline
    vendor: bench
    display: "null baseline (base unchanged)"
    role: calibration
    engine: pipeline
    run_names: [null-baseline]
    bench_vendors: [null-baseline]
    note: "The base DOCX submitted unchanged; the floor a redline tool must beat."
  # ---- retired identities kept so history stays readable ----
  - id: sanity-word
    vendor: bench
    display: sanity-word
    role: calibration
    engine: passthrough
    status: retired
    run_names: [sanity-word]
    bench_vendors: [sanity-word]
    note: "July 2026 passthrough of pre-rendered PDFs from a directory no longer in the repo."
  - id: ooxmlsdk
    vendor: ooxmlsdk
    display: ooxmlsdk
    role: generator
    engine: ooxmlsdk
    status: retired
    run_names: [ooxmlsdk]
    bench_vendors: [ooxmlsdk]
  - id: prebaked
    vendor: bench
    display: prebaked
    role: generator
    engine: prebaked
    status: retired
    bench_vendors: [prebaked]
  - id: jubarte-dev-variants
    vendor: jubarte
    display: "jubarte (dev variants)"
    role: generator
    engine: jubarte-final
    affiliated: true
    status: retired
    speed_tools: [jubarte-second-native, jubarte-second-docxodus, jubarte-third-native, jubarte-third-docxodus]
    note: "Development builds measured in July 2026 microbenchmarks; never published as vendors."
```

- [ ] **Step 5: Run the tests**

Run: `uv run pytest tests/test_ledger_registry.py -q -n 0`
Expected: `12 passed`. If `test_committed_registry_loads_and_covers_bench_yaml_runs` fails, its message lists the missing run names: add them to the matching entry's `run_names` (do not invent new entries for spellings of an existing tool).

- [ ] **Step 6: Lint, types, commit**

```bash
uv run ruff check src tests && uv run ruff format src tests && uv run ty check src
git add bench.registry.yaml src/neurotic_docx_bench/ledger tests/test_ledger_registry.py
git commit -m "feat(report): vendor registry mapping every store's tool spelling to one tool_id"
```

---

### Task 2: Tool pin parsing

**Files:**
- Create: `src/neurotic_docx_bench/ledger/pins.py`
- Test: `tests/test_ledger_pins.py`

- [ ] **Step 1: Write the failing tests**

```python
"""Every version-string shape in results/bench.jsonl and the converter reports parses."""

from __future__ import annotations

import pytest

from neurotic_docx_bench.ledger.pins import ToolPin


@pytest.mark.parametrize(
    ("raw", "label", "content_hash", "git_sha"),
    [
        ("9.8.0", "9.8.0", None, None),
        ("0.3.0-ts-migration", "0.3.0-ts-migration", None, None),
        ("jubarte-final@dd16ad8fbcf3", "jubarte-final", "dd16ad8fbcf3", None),
        (
            "0.2.0@1286be69c690+git.65014685f960a5c1b9a19250e23fccaa4df5e5ef",
            "0.2.0",
            "1286be69c690",
            "65014685f960a5c1b9a19250e23fccaa4df5e5ef",
        ),
        ("jubarte-rust@9457b6549b5d+git.ebf1a79", "jubarte-rust", "9457b6549b5d", "ebf1a79"),
        ("jubarte 0.7.0", "jubarte 0.7.0", None, None),
        ("LibreOffice Convert Rust v0.1.0", "LibreOffice Convert Rust v0.1.0", None, None),
    ],
)
def test_parse_shapes(raw: str, label: str, content_hash: str | None, git_sha: str | None) -> None:
    pin = ToolPin.parse(raw)
    assert pin.raw == raw
    assert pin.label == label
    assert pin.content_hash == content_hash
    assert pin.git_sha == git_sha


@pytest.mark.parametrize("raw", [None, "", "   ", "None"])
def test_missing_versions_are_unpinned(raw: str | None) -> None:
    pin = ToolPin.parse(raw)
    assert pin.raw is None
    assert pin.pinned is False
    assert pin.display == "unpinned"


def test_identity_is_content_hash_when_present() -> None:
    a = ToolPin.parse("jubarte-final@dd16ad8fbcf3")
    b = ToolPin.parse("0.9.9@dd16ad8fbcf3+git.abcdef1")
    assert a.identity == b.identity == "dd16ad8fbcf3"
    assert ToolPin.parse("9.8.0").identity == "9.8.0"


def test_display_is_short_and_stable() -> None:
    pin = ToolPin.parse("0.2.0@1286be69c690+git.65014685f960a5c1b9a19250e23fccaa4df5e5ef")
    assert pin.display == "0.2.0@1286be69c690+git.6501468"
    assert ToolPin.parse("9.8.0").display == "9.8.0"


def test_same_git_commit_detected_across_short_and_long_sha() -> None:
    a = ToolPin.parse("x@000000000000+git.ebf1a7996df49f99fb40f4f67713e61cfd19c731")
    b = ToolPin.parse("y@111111111111+git.ebf1a79")
    assert a.same_commit(b) is True
    assert a.same_commit(ToolPin.parse("z@222222222222")) is False
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_ledger_pins.py -q -n 0`
Expected: `ModuleNotFoundError: No module named 'neurotic_docx_bench.ledger.pins'`.

- [ ] **Step 3: Write the module**

`src/neurotic_docx_bench/ledger/pins.py`:

```python
"""Parse the tool_version strings the stores carry into comparable parts.

Shapes seen in ``results/bench.jsonl`` and the converter reports:

- ``9.8.0`` (npm / PyPI version)
- ``jubarte-final@dd16ad8fbcf3`` (dist label + 12-hex content hash)
- ``0.2.0@1286be69c690+git.<sha>`` (label + hash + engine commit, sha 7 to 40 hex)
- ``jubarte 0.7.0`` / ``docxide-pdf v0.17.0`` (converter ``--version`` output)
- ``None`` / empty (unversioned sanity runs)
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict

_PIN_RE = re.compile(
    r"^(?P<label>[^@\s]+)@(?P<hash>[0-9a-f]{6,64})(?:\+git\.(?P<sha>[0-9a-f]{7,40}))?$"
)


class ToolPin(BaseModel):
    model_config = ConfigDict(frozen=True)

    raw: str | None
    label: str | None
    content_hash: str | None
    git_sha: str | None

    @classmethod
    def parse(cls, raw: object) -> ToolPin:
        if raw is None:
            return cls(raw=None, label=None, content_hash=None, git_sha=None)
        text = str(raw).strip()
        if not text or text == "None":
            return cls(raw=None, label=None, content_hash=None, git_sha=None)
        m = _PIN_RE.match(text)
        if m:
            return cls(
                raw=text,
                label=m.group("label"),
                content_hash=m.group("hash"),
                git_sha=m.group("sha"),
            )
        return cls(raw=text, label=text, content_hash=None, git_sha=None)

    @property
    def pinned(self) -> bool:
        return self.raw is not None

    @property
    def identity(self) -> str | None:
        """What "the same pin" means: the content hash when there is one, else the raw text."""
        if self.content_hash:
            return self.content_hash
        return self.raw

    @property
    def display(self) -> str:
        if self.raw is None:
            return "unpinned"
        if self.content_hash is None:
            return self.raw
        out = f"{self.label}@{self.content_hash[:12]}"
        if self.git_sha:
            out += f"+git.{self.git_sha[:7]}"
        return out

    def same_commit(self, other: ToolPin) -> bool:
        if not self.git_sha or not other.git_sha:
            return False
        n = min(len(self.git_sha), len(other.git_sha))
        return self.git_sha[:n] == other.git_sha[:n]
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/test_ledger_pins.py -q -n 0`
Expected: `14 passed`.

- [ ] **Step 5: Commit**

```bash
uv run ruff check src tests && uv run ruff format src tests
git add src/neurotic_docx_bench/ledger/pins.py tests/test_ledger_pins.py
git commit -m "feat(report): parse every tool_version shape into label, content hash and commit"
```

---

### Task 3: Normalized result rows from `results/bench.jsonl`

**Files:**
- Create: `src/neurotic_docx_bench/ledger/rows.py`
- Test: `tests/test_ledger_rows.py`
- Test: `tests/test_store_invariants.py` (first invariant; extended in later tasks)

- [ ] **Step 1: Write the failing tests**

`tests/test_ledger_rows.py`:

```python
"""bench.jsonl lines normalize to ResultRow with honest failure counts and ITT."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from neurotic_docx_bench.ledger import rows as rws
from neurotic_docx_bench.ledger.registry import load_registry


@pytest.fixture
def registry(tmp_path: Path):
    doc = {
        "schema_version": 1,
        "tools": [
            {"id": "docxodus", "vendor": "docxodus", "display": "docxodus", "role": "generator",
             "engine": "docxodus", "run_names": ["docxodus"], "bench_vendors": ["docxodus"]},
            {"id": "jubarte-ast", "vendor": "jubarte", "display": "jubarte (ast)", "role": "generator",
             "engine": "jubarte-final", "affiliated": True,
             "run_names": ["jubarte-final-native"], "bench_vendors": ["jubarte-ast"]},
            {"id": "jubarte-lossless", "vendor": "jubarte", "display": "jubarte (lossless)", "role": "generator",
             "engine": "jubarte-final", "affiliated": True,
             "run_names": ["jubarte-final-lossless"], "bench_vendors": ["jubarte"]},
        ],
    }
    p = tmp_path / "reg.yaml"
    p.write_text(yaml.safe_dump(doc))
    return load_registry(p)


def _line(**over) -> dict:
    base = {
        "id_run": "019ff85b-23fd-7450-9744-5669ef0d3c1e",
        "vendor": "docxodus",
        "benchmark": "script_redlines",
        "n_docs": 3,
        "overall_mean": 80.0,
        "overall_median": 90.0,
        "exact_100": 1,
        "scores": {"a": 100.0, "b": 90.0, "c": 50.0},
        "failures": [{"doc": "d", "stage": "generate", "error": "x"},
                     {"doc": "c", "stage": "render", "error": "non-fatal"}],
        "tool_version": "9.8.0",
        "timestamp": "2026-08-12T23:42:30.000000+00:00",
        "corpus_revision": "5ed816028d99",
        "scorer": "pagefair-v2",
        "environment_config": {"runs": [{"name": "docxodus", "render": "soffice"}]},
    }
    base.update(over)
    return base


def test_failed_docs_exclude_docs_that_also_scored(registry) -> None:
    row = rws.row_from_bench_line(_line(), registry)
    assert row is not None
    assert row.n_scored == 3
    assert row.n_failure_events == 2
    assert row.n_failed_docs == 1          # only "d" is zeroed
    assert row.itt_n == 4                  # 3 scored + 1 zeroed
    assert row.n_scored + row.n_failed_docs == row.itt_n


def test_emitted_itt_fields_win_over_recomputation(registry) -> None:
    row = rws.row_from_bench_line(_line(itt_n_docs=4, itt_mean=60.0, itt_median=70.0), registry)
    assert row is not None
    assert (row.itt_n, row.itt_mean, row.itt_median) == (4, 60.0, 70.0)
    assert row.itt_approx is False


def test_itt_recomputed_from_scores_when_not_emitted(registry) -> None:
    row = rws.row_from_bench_line(_line(), registry)
    assert row is not None
    assert row.itt_n == 4
    assert row.itt_median == 70.0          # median of [100, 90, 50, 0]
    assert row.itt_mean == 60.0
    assert row.itt_approx is False


def test_legacy_line_without_scores_is_approximate(registry) -> None:
    row = rws.row_from_bench_line(_line(scores={}, corpus_revision=None), registry)
    assert row is not None
    assert row.itt_approx is True
    assert row.provenance == "legacy"


def test_stamped_line_with_scores_is_stamped(registry) -> None:
    row = rws.row_from_bench_line(_line(), registry)
    assert row is not None and row.provenance == "stamped"


def test_tool_id_uses_run_name_before_vendor(registry) -> None:
    line = _line(vendor="jubarte", environment_config={"runs": [{"name": "jubarte-final-native", "render": "soffice"}]})
    row = rws.row_from_bench_line(line, registry)
    assert row is not None and row.tool_id == "jubarte-ast"
    assert row.affiliated is True


def test_unknown_vendor_returns_none(registry) -> None:
    assert rws.row_from_bench_line(_line(vendor="ghost"), registry) is None


def test_unknown_benchmark_returns_none(registry) -> None:
    assert rws.row_from_bench_line(_line(benchmark="not_a_bench"), registry) is None


def test_load_bench_rows_reports_unmapped(tmp_path: Path, registry) -> None:
    p = tmp_path / "bench.jsonl"
    p.write_text(json.dumps(_line()) + "\n" + json.dumps(_line(vendor="ghost")) + "\n" + "\n")
    rows, unmapped = rws.load_bench_rows(p, registry)
    assert [r.tool_id for r in rows] == ["docxodus"]
    assert [u["vendor"] for u in unmapped] == ["ghost"]


def test_pin_and_render_and_run_name_are_carried(registry) -> None:
    row = rws.row_from_bench_line(_line(), registry)
    assert row is not None
    assert row.pin.display == "9.8.0"
    assert row.render == "soffice"
    assert row.run_name == "docxodus"
    assert row.timestamp.year == 2026
```

`tests/test_store_invariants.py`:

```python
"""Invariants over the committed stores. Skipped when the stores are absent (CI clones
without results/), never skipped locally."""

from __future__ import annotations

from pathlib import Path

import pytest

from neurotic_docx_bench.ledger import rows as rws
from neurotic_docx_bench.ledger.registry import DEFAULT_REGISTRY_PATH, load_registry

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "results" / "bench.jsonl"
REGISTRY = ROOT / DEFAULT_REGISTRY_PATH

needs_store = pytest.mark.skipif(
    not (BENCH.is_file() and REGISTRY.is_file()), reason="results/bench.jsonl or registry absent",
)


@needs_store
def test_every_bench_line_maps_to_a_registry_tool() -> None:
    rows, unmapped = rws.load_bench_rows(BENCH, load_registry(REGISTRY))
    assert rows, "no rows loaded"
    assert unmapped == [], f"unmapped lines: {[(u['vendor'], u['run_name']) for u in unmapped]}"


@needs_store
def test_scored_plus_failed_equals_itt_for_every_row() -> None:
    rows, _ = rws.load_bench_rows(BENCH, load_registry(REGISTRY))
    bad = [(r.tool_id, r.benchmark, r.n_scored, r.n_failed_docs, r.itt_n) for r in rows
           if not r.itt_approx and r.n_scored + r.n_failed_docs != r.itt_n]
    assert bad == []
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_ledger_rows.py tests/test_store_invariants.py -q -n 0`
Expected: `ModuleNotFoundError: No module named 'neurotic_docx_bench.ledger.rows'`.

- [ ] **Step 3: Write the module**

`src/neurotic_docx_bench/ledger/rows.py`:

```python
"""Normalized rows: one shape for every store the report reads.

``row_from_bench_line`` is the only place that understands the raw ``bench.jsonl``
line. It recomputes intent-to-treat stats from per-doc scores when the line did
not emit them (legacy lines) and separates *failure events* (records) from *failed
documents* (documents that produced no score and enter the ITT pool at 0).
"""

from __future__ import annotations

import json
import statistics
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from neurotic_docx_bench.benchmarks import BENCHMARKS, LEGACY_STAGE_TO_BENCHMARK
from neurotic_docx_bench.ledger.pins import ToolPin
from neurotic_docx_bench.ledger.registry import Registry

Provenance = Literal["stamped", "legacy"]


class ResultRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: Literal["bench", "converter"]
    id_run: str
    tool_id: str
    display: str
    affiliated: bool
    benchmark: str
    lens: str = "pixel"
    pin: ToolPin
    timestamp: datetime
    corpus_revision: str | None = None
    docset_id: str | None = None
    renderer_id: str | None = None
    scorer: str = "v1"
    n_scored: int
    n_failed_docs: int
    n_failure_events: int
    n_oracle_unmatched: int = 0
    itt_n: int
    itt_mean: float
    itt_median: float
    itt_approx: bool = False
    mean: float
    median: float
    exact_100: int
    scores: dict[str, float] = {}
    holdout_mode: str | None = None
    hardware: dict[str, object] | None = None
    render: str | None = None
    run_name: str | None = None
    configuration: str | None = None

    @property
    def provenance(self) -> Provenance:
        if self.corpus_revision and self.scores and not self.itt_approx:
            return "stamped"
        return "legacy"


def _num(value: object, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return default


def _run_meta(data: dict) -> tuple[str, str]:
    env = data.get("environment_config") or {}
    runs = env.get("runs") if isinstance(env, dict) else None
    first = runs[0] if isinstance(runs, list) and runs and isinstance(runs[0], dict) else {}
    return str(first.get("name") or data.get("tool") or ""), str(first.get("render") or data.get("render") or "")


def _benchmark_name(data: dict) -> str | None:
    name = data.get("benchmark")
    if not name and isinstance(data.get("stage"), str):
        name = LEGACY_STAGE_TO_BENCHMARK.get(data["stage"])
    return name if name in BENCHMARKS else None


def _timestamp(data: dict) -> datetime:
    raw = data.get("timestamp") or data.get("run_ts") or ""
    try:
        ts = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return datetime(1970, 1, 1, tzinfo=UTC)
    return ts if ts.tzinfo else ts.replace(tzinfo=UTC)


def _failed_docs(data: dict) -> list[str]:
    out: list[str] = []
    for f in data.get("failures") or []:
        if isinstance(f, dict) and f.get("doc"):
            out.append(str(f["doc"]))
    return out


def row_from_bench_line(data: dict, registry: Registry) -> ResultRow | None:
    benchmark = _benchmark_name(data)
    if benchmark is None:
        return None
    vendor = str(data.get("vendor") or data.get("tool") or "")
    run_name, render = _run_meta(data)
    entry = registry.resolve_bench(vendor=vendor, run_name=run_name, render=render)
    if entry is None:
        return None

    scores_raw = data.get("scores")
    scores = (
        {str(k): _num(v) for k, v in scores_raw.items()}
        if isinstance(scores_raw, dict) else {}
    )
    failures = data.get("failures") or []
    n_failure_events = len(failures) if isinstance(failures, list) else int(_num(data.get("n_failures")))
    failed_docs = set(_failed_docs(data))
    n_scored = len(scores) if scores else int(_num(data.get("n_docs")))

    if data.get("itt_median") is not None and data.get("itt_n_docs") is not None:
        itt_n = int(_num(data["itt_n_docs"]))
        itt_mean = _num(data.get("itt_mean"))
        itt_median = _num(data["itt_median"])
        itt_approx = False
        n_failed_docs = max(itt_n - n_scored, 0) if not scores else len(failed_docs - scores.keys())
    elif scores:
        zeroed = sorted(failed_docs - scores.keys())
        values = list(scores.values()) + [0.0] * len(zeroed)
        itt_n = len(values)
        itt_mean = round(statistics.mean(values), 4)
        itt_median = round(statistics.median(values), 4)
        itt_approx = False
        n_failed_docs = len(zeroed)
    else:
        n_failed_docs = n_failure_events
        values = [_num(data.get("overall_median"))] * n_scored + [0.0] * n_failed_docs
        itt_n = len(values)
        itt_mean = round(statistics.mean(values), 4) if values else 0.0
        itt_median = round(statistics.median(values), 4) if values else 0.0
        itt_approx = True

    return ResultRow(
        source="bench",
        id_run=str(data.get("id_run") or data.get("uuid7") or ""),
        tool_id=entry.id,
        display=entry.display,
        affiliated=entry.affiliated,
        benchmark=benchmark,
        lens="pixel",
        pin=ToolPin.parse(data.get("tool_version")),
        timestamp=_timestamp(data),
        corpus_revision=(str(data["corpus_revision"]) if data.get("corpus_revision") else None),
        docset_id=(str(data["docset_id"]) if data.get("docset_id") else None),
        renderer_id=(str(data["renderer_id"]) if data.get("renderer_id") else None),
        scorer=str(data.get("scorer") or "v1"),
        n_scored=n_scored,
        n_failed_docs=n_failed_docs,
        n_failure_events=n_failure_events,
        n_oracle_unmatched=int(_num(data.get("n_oracle_unmatched"))),
        itt_n=itt_n,
        itt_mean=itt_mean,
        itt_median=itt_median,
        itt_approx=itt_approx,
        mean=_num(data.get("overall_mean")),
        median=_num(data.get("overall_median")),
        exact_100=int(_num(data.get("exact_100"))),
        scores=scores,
        holdout_mode=(str(data["holdout_mode"]) if data.get("holdout_mode") else None),
        hardware=data.get("hardware") if isinstance(data.get("hardware"), dict) else None,
        render=render or None,
        run_name=run_name or None,
        configuration=entry.configuration,
    )


def load_bench_rows(path: Path, registry: Registry) -> tuple[list[ResultRow], list[dict]]:
    """All rows in ``path`` plus the raw lines the registry could not map."""
    rows: list[ResultRow] = []
    unmapped: list[dict] = []
    with Path(path).open(encoding="utf-8") as fh:
        for raw in fh:
            if not raw.strip():
                continue
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            row = row_from_bench_line(data, registry)
            if row is None:
                run_name, _ = _run_meta(data)
                unmapped.append({
                    "vendor": data.get("vendor") or data.get("tool"),
                    "run_name": run_name,
                    "benchmark": data.get("benchmark") or data.get("stage"),
                    "id_run": data.get("id_run"),
                })
                continue
            rows.append(row)
    return rows, unmapped
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/test_ledger_rows.py tests/test_store_invariants.py -q -n 0`
Expected: `tests/test_ledger_rows.py` 10 passed. `test_every_bench_line_maps_to_a_registry_tool` may fail listing `(vendor, run_name)` pairs from July lines whose run names are not in the registry; add each spelling to the matching entry's `run_names` in `bench.registry.yaml` until it passes. `test_scored_plus_failed_equals_itt_for_every_row` must pass as written: it holds by construction for recomputed rows and by `itt_n_docs` for emitted ones.

- [ ] **Step 5: Commit**

```bash
uv run ruff check src tests && uv run ruff format src tests && uv run ty check src
git add src/neurotic_docx_bench/ledger/rows.py tests/test_ledger_rows.py tests/test_store_invariants.py bench.registry.yaml
git commit -m "feat(report): normalized ResultRow from bench.jsonl; failed docs counted once"
git push -u origin consolidate/01-registry
```

Open PR 1: "report: registry, pins, normalized rows" against `bench/latest-competitors-0926`.

---

## PR 2: honest failure accounting and fixed denominators (write side)

```bash
git checkout -b consolidate/02-failures consolidate/01-registry
```

### Task 4: Failed documents vs failure events on the emitted line

**Files:**
- Modify: `src/neurotic_docx_bench/aggregate.py` (add `failed_doc_keys`, use it in `compute_aggregate_itt`)
- Modify: `src/neurotic_docx_bench/results_schema.py` (fields on `Results`, args on `build_results`)
- Modify: `src/neurotic_docx_bench/emit/jsonl.py:105-156` (`build_results_line` pass-through)
- Test: `tests/test_failure_accounting.py`

- [ ] **Step 1: Write the failing tests**

```python
"""A document is scored or failed, never both in the published counts."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from neurotic_docx_bench.aggregate import compute_aggregate_itt, failed_doc_keys
from neurotic_docx_bench.config import BenchConfig
from neurotic_docx_bench.results_schema import build_results
from pathlib import Path


def _results(**over):
    args = dict(
        id_run=uuid.uuid7(),
        vendor="acme",
        benchmark="script_redlines",
        scores={"a": 100.0, "b": 90.0, "c": 50.0},
        per_doc=None,
        speed_samples_ms=[1.0],
        environment_config=BenchConfig(source_of_truth=Path("oracle")),
        timestamp=datetime(2026, 9, 27, tzinfo=UTC),
        failures=[
            {"doc": "d", "stage": "generate", "error": "boom"},
            {"doc": "c", "stage": "render", "error": "warning only"},
        ],
    )
    args.update(over)
    return build_results(**args)


def test_failed_doc_keys_excludes_scored_docs() -> None:
    assert failed_doc_keys({"c": 50.0}, ["d", "c", "d"]) == {"d"}


def test_itt_uses_failed_doc_keys() -> None:
    agg = compute_aggregate_itt({"c": 50.0}, ["d", "c"])
    assert agg.n_docs == 2 and agg.overall_mean == 25.0


def test_results_carry_both_counts() -> None:
    r = _results()
    assert r.n_failure_events == 2
    assert r.n_failed_docs == 1
    assert r.n_failures == 2  # legacy field keeps its old meaning for old readers
    assert r.n_docs + r.n_failed_docs == r.itt_n_docs == 4


def test_new_provenance_fields_default_to_none_and_serialize() -> None:
    r = _results()
    d = r.to_json_dict()
    for key in ("tool_id", "configuration", "docset_id", "renderer_id", "hardware"):
        assert key in d and d[key] is None
    assert d["n_failed_docs"] == 1 and d["n_failure_events"] == 2


def test_provenance_fields_round_trip() -> None:
    r = _results(
        tool_id="acme", configuration="fast", docset_id="abc123abc123",
        renderer_id="soffice-26.2.4.2", hardware={"cpu": "Apple M3", "cores": 12},
    )
    d = r.to_json_dict()
    assert d["tool_id"] == "acme" and d["configuration"] == "fast"
    assert d["docset_id"] == "abc123abc123" and d["renderer_id"] == "soffice-26.2.4.2"
    assert d["hardware"] == {"cpu": "Apple M3", "cores": 12}
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_failure_accounting.py -q -n 0`
Expected: `ImportError: cannot import name 'failed_doc_keys'`.

- [ ] **Step 3: Implement**

In `src/neurotic_docx_bench/aggregate.py`, replace `compute_aggregate_itt` with:

```python
def failed_doc_keys(scores: Mapping[str, float], failure_docs: Iterable[str]) -> set[str]:
    """Documents that produced no score: the ones that enter the ITT pool at 0.

    A failure record naming a doc that scored anyway is a non-fatal stage event and
    does not make the doc "failed" for ranking purposes.
    """
    return {doc for doc in set(failure_docs) if doc not in scores}


def compute_aggregate_itt(
    scores: dict[str, float],
    failure_docs: Iterable[str],
    per_doc: Mapping[str, Mapping[str, object]] | None = None,
) -> Aggregate:
    """Intent-to-treat aggregate: every failed doc (see :func:`failed_doc_keys`) scores 0."""
    zeroed = {doc: 0.0 for doc in failed_doc_keys(scores, failure_docs)}
    return compute_aggregate({**scores, **zeroed}, per_doc=per_doc)
```

In `src/neurotic_docx_bench/results_schema.py`, add to `Results` after `holdout_mode`:

```python
    # Failure accounting (consolidation): ``n_failure_events`` counts records in
    # ``failures``; ``n_failed_docs`` counts documents with no score, i.e. the docs
    # zeroed by ITT. ``n_docs + n_failed_docs == itt_n_docs`` always holds.
    n_failed_docs: int = 0
    n_failure_events: int = 0
    # Provenance (consolidation): registry tool id and configuration, the hash of
    # the benchmark's document set, the renderer identity, and the machine.
    tool_id: str | None = None
    configuration: str | None = None
    docset_id: str | None = None
    renderer_id: str | None = None
    hardware: dict[str, object] | None = None
```

Add matching keyword parameters to `build_results` (all defaulting to `None`) and set them in the `Results(...)` call; compute the counts:

```python
    from neurotic_docx_bench.aggregate import failed_doc_keys  # top of file with the other import
    ...
    failure_docs = [str(f.get("doc", "")) for f in failure_list]
    itt = compute_aggregate_itt(rounded_scores, failure_docs)
    n_failed_docs = len(failed_doc_keys(rounded_scores, failure_docs))
    ...
        n_failed_docs=n_failed_docs,
        n_failure_events=len(failure_list),
        tool_id=tool_id,
        configuration=configuration,
        docset_id=docset_id,
        renderer_id=renderer_id,
        hardware=hardware,
```

In `src/neurotic_docx_bench/emit/jsonl.py::build_results_line`, add the same five keyword parameters (`tool_id`, `configuration`, `docset_id`, `renderer_id`, `hardware`, each `= None`) and forward them to `build_typed_results`.

- [ ] **Step 4: Run the tests, then the two existing suites this touches**

Run: `uv run pytest tests/test_failure_accounting.py tests/test_itt.py tests/test_results_schema.py tests/test_emit_jsonl.py -q -n 0`
Expected: all pass (`test_itt_scored_doc_keeps_its_score_despite_failure_entry` still passes: a scored doc keeps its score).

- [ ] **Step 5: Commit**

```bash
uv run ruff check src tests && uv run ruff format src tests && uv run ty check src
git add src/neurotic_docx_bench/aggregate.py src/neurotic_docx_bench/results_schema.py src/neurotic_docx_bench/emit/jsonl.py tests/test_failure_accounting.py
git commit -m "feat(schema): count failed documents separately from failure events; provenance fields"
```

---

### Task 5: Fixed document set per benchmark; missing outputs enter at 0

**Files:**
- Create: `src/neurotic_docx_bench/ledger/docset.py`
- Modify: `src/neurotic_docx_bench/cli.py:1098-1160` (`_emit_and_gate_benchmark`), new command `docset`
- Test: `tests/test_ledger_docset.py`

- [ ] **Step 1: Write the failing tests**

```python
"""The denominator of every benchmark is the oracle document set, not oracle ∩ candidate."""

from __future__ import annotations

import json
from pathlib import Path

from neurotic_docx_bench.ledger import docset as ds


def _touch(d: Path, *names: str) -> Path:
    d.mkdir(parents=True, exist_ok=True)
    for n in names:
        (d / n).write_bytes(b"")
    return d


def test_redline_keys_normalize_word_variant_and_skip_non_redlines(tmp_path: Path) -> None:
    d = _touch(tmp_path / "o", "a_b_redline.pdf", "c_d_word_redline.pdf", "c_d_redline.pdf", "a.pdf")
    assert ds.keys_in_dir(d, "redline") == {"a_b", "c_d"}


def test_accepted_keys_from_docx_and_pdf(tmp_path: Path) -> None:
    d = _touch(tmp_path / "o", "a_b_redline_accepted.docx", "a_b_word_redline_accepted.pdf", "c_d_redline_accepted.docx")
    assert ds.keys_in_dir(d, "accepted") == {"a_b", "c_d"}


def test_plain_keys_lowercase_stems(tmp_path: Path) -> None:
    d = _touch(tmp_path / "o", "Alpha.docx", "beta.pdf")
    assert ds.keys_in_dir(d, "plain") == {"alpha", "beta"}


def test_docset_id_is_order_independent_and_12_hex() -> None:
    a = ds.docset_id({"x", "y"})
    b = ds.docset_id(["y", "x"])
    assert a == b and len(a) == 12 and int(a, 16) >= 0


def test_benchmark_docset_applies_holdout(tmp_path: Path) -> None:
    d = _touch(tmp_path / "o", "a_b_redline.pdf", "c_d_redline.pdf", "e_f_redline.pdf")
    full = ds.benchmark_docset("script_redlines", [d], holdout={"c_d"}, holdout_mode=None)
    excl = ds.benchmark_docset("script_redlines", [d], holdout={"c_d"}, holdout_mode="excluded")
    only = ds.benchmark_docset("script_redlines", [d], holdout={"c_d"}, holdout_mode="only")
    assert set(full.keys) == {"a_b", "c_d", "e_f"}
    assert set(excl.keys) == {"a_b", "e_f"}
    assert set(only.keys) == {"c_d"}
    assert full.id != excl.id != only.id


def test_missing_output_failures_name_docs_with_no_score_and_no_failure() -> None:
    keys = {"a", "b", "c", "d"}
    scores = {"a": 1.0}
    failures = [{"doc": "b", "stage": "generate", "error": "x"}]
    added = ds.missing_output_failures(keys, scores, failures)
    assert added == [
        {"doc": "c", "stage": "missing_output", "error": "no candidate output for this document"},
        {"doc": "d", "stage": "missing_output", "error": "no candidate output for this document"},
    ]


def test_missing_output_ignores_docs_outside_the_set() -> None:
    assert ds.missing_output_failures({"a"}, {"zzz": 1.0}, []) == [
        {"doc": "a", "stage": "missing_output", "error": "no candidate output for this document"},
    ]


def test_write_and_load_docsets(tmp_path: Path) -> None:
    d = _touch(tmp_path / "o", "a_b_redline.pdf")
    one = ds.benchmark_docset("script_redlines", [d], holdout=set(), holdout_mode="excluded")
    p = tmp_path / "docsets.json"
    ds.write_docsets(p, [one], source_dirs={one.id: [str(d)]})
    loaded = ds.load_docsets(p)
    assert loaded[one.id]["benchmark"] == "script_redlines"
    assert loaded[one.id]["n"] == 1
    assert json.loads(p.read_text())[one.id]["holdout_mode"] == "excluded"
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_ledger_docset.py -q -n 0`
Expected: `ModuleNotFoundError: No module named 'neurotic_docx_bench.ledger.docset'`.

- [ ] **Step 3: Write the module**

`src/neurotic_docx_bench/ledger/docset.py`:

```python
"""Document sets: the fixed denominator of every benchmark.

A benchmark's document set is the key set of its ORACLE directory (minus the sealed
holdout for a normal run). Its ``docset_id`` is a 12-hex SHA-256 of the sorted keys,
so two runs are comparable exactly when they share it, whichever oracle PDFs were
re-rendered in between (that is what ``corpus_revision`` tracks, separately).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from neurotic_docx_bench import pipeline

KeyKind = Literal["redline", "accepted", "plain"]

KEY_KIND: dict[str, KeyKind] = {
    "script_redlines": "redline",
    "accepted_changes": "accepted",
    "roundtrip": "plain",
    "visual_rendering": "plain",
    "visual_redlines": "redline",
    "visual_accepted_changes": "accepted",
}

ROUNDTRIP_CORPUS = Path("corpus/word_based/word_working_roundtrip")
DEFAULT_DOCSETS_PATH = Path("results/docsets.json")
MISSING_OUTPUT_STAGE = "missing_output"
MISSING_OUTPUT_ERROR = "no candidate output for this document"
_SUFFIXES = {".pdf", ".docx"}


class DocSet(BaseModel):
    model_config = ConfigDict(frozen=True)

    benchmark: str
    keys: tuple[str, ...]
    id: str
    holdout_mode: str | None = None

    @property
    def n(self) -> int:
        return len(self.keys)


def keys_in_dir(directory: Path, kind: KeyKind) -> set[str]:
    stems = {p.stem for p in Path(directory).iterdir() if p.suffix.lower() in _SUFFIXES}
    if kind == "redline":
        return {pipeline.oracle_pair_key(s) for s in stems if pipeline.is_redline(s)}
    if kind == "accepted":
        return {pipeline.accepted_key(s) for s in stems}
    return {pipeline.normalize_stem(s) for s in stems}


def docset_id(keys: Iterable[str]) -> str:
    joined = "\n".join(sorted(set(keys))).encode("utf-8")
    return hashlib.sha256(joined).hexdigest()[:12]


def benchmark_docset(
    benchmark: str,
    oracle_dirs: Sequence[Path],
    *,
    holdout: set[str],
    holdout_mode: str | None,
) -> DocSet:
    kind = KEY_KIND[benchmark]
    keys: set[str] = set()
    for d in oracle_dirs:
        if Path(d).is_dir():
            keys |= keys_in_dir(Path(d), kind)
    if holdout_mode == "excluded":
        keys -= holdout
    elif holdout_mode == "only":
        keys &= holdout
    ordered = tuple(sorted(keys))
    return DocSet(benchmark=benchmark, keys=ordered, id=docset_id(ordered), holdout_mode=holdout_mode)


def oracle_dirs_for(cfg: object, benchmark: str) -> list[Path]:
    """Oracle directories that define ``benchmark``'s document set, from a BenchConfig."""
    if benchmark == "script_redlines":
        return [Path(cfg.source_of_truth), *(Path(p) for p in (getattr(cfg, "extra_oracle_dirs", None) or ()))]  # type: ignore[attr-defined]
    if benchmark == "accepted_changes":
        agt = getattr(cfg, "accepted_ground_truth", None)
        return [Path(agt)] if agt else []
    if benchmark == "roundtrip":
        return [ROUNDTRIP_CORPUS]
    visual = getattr(cfg, "visual_oracles", None) or {}
    return [Path(visual[benchmark])] if benchmark in visual else []


def missing_output_failures(
    keys: Iterable[str],
    scores: Mapping[str, float],
    failures: Sequence[Mapping[str, str]],
) -> list[dict[str, str]]:
    """Failure records for documents in the set that neither scored nor failed."""
    seen = set(scores) | {str(f.get("doc", "")) for f in failures}
    return [
        {"doc": k, "stage": MISSING_OUTPUT_STAGE, "error": MISSING_OUTPUT_ERROR}
        for k in sorted(set(keys) - seen)
    ]


def write_docsets(path: Path, docsets: Sequence[DocSet], *, source_dirs: Mapping[str, list[str]]) -> None:
    existing = load_docsets(path) if Path(path).is_file() else {}
    now = datetime.now(UTC).isoformat()
    for d in docsets:
        existing[d.id] = {
            "benchmark": d.benchmark,
            "n": d.n,
            "holdout_mode": d.holdout_mode,
            "source_dirs": list(source_dirs.get(d.id, [])),
            "computed_at": now,
        }
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(existing, indent="\t", sort_keys=True) + "\n")


def load_docsets(path: Path) -> dict[str, dict]:
    if not Path(path).is_file():
        return {}
    data = json.loads(Path(path).read_text())
    return {str(k): dict(v) for k, v in data.items()} if isinstance(data, dict) else {}
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/test_ledger_docset.py -q -n 0`
Expected: `8 passed`. If `test_plain_keys_lowercase_stems` fails because `pipeline.normalize_stem` strips a suffix, keep the test and use `stem.lower()` for the plain kind (the roundtrip candidate matcher `pipeline._index_plain` is the authority: read it and match its key function).

- [ ] **Step 5: Wire the write side**

In `src/neurotic_docx_bench/cli.py`, add a helper above `_emit_and_gate_benchmark`:

```python
def _docset_for(cfg: BenchConfig, benchmark: BenchmarkName, holdout_mode: str | None) -> docset_mod.DocSet | None:
    """The benchmark's fixed document set for this run's holdout regime, or None when
    the oracle directory is not configured (the line is then emitted without a docset)."""
    dirs = docset_mod.oracle_dirs_for(cfg, benchmark)
    if not any(Path(d).is_dir() for d in dirs):
        return None
    holdout = pipeline.load_holdout(cfg.holdout_list) if cfg.holdout_list and Path(cfg.holdout_list).is_file() else set()
    return docset_mod.benchmark_docset(benchmark, dirs, holdout=holdout, holdout_mode=holdout_mode)
```

with `from neurotic_docx_bench.ledger import docset as docset_mod` among the imports. Inside `_emit_and_gate_benchmark`, before `line = jsonl_emit.build_results_line(...)`:

```python
    docset = _docset_for(cfg, benchmark, holdout_mode)
    failures = list(failures)
    if docset is not None:
        failures.extend(docset_mod.missing_output_failures(docset.keys, scores, failures))
```

and pass `docset_id=docset.id if docset else None` to `build_results_line`. Add the `docset` command after `oracle_manifest_cmd`:

```python
@app.command(name="docset")
def docset_cmd(
    config: Path = typer.Option(Path("bench.yaml"), "--config", "-c"),
    write: bool = typer.Option(False, "--write", help="record every benchmark's document set in results/docsets.json"),
) -> None:
    """Print (and with --write record) the fixed document set of every benchmark."""
    cfg = load_config(config)
    holdout = pipeline.load_holdout(cfg.holdout_list) if cfg.holdout_list and Path(cfg.holdout_list).is_file() else set()
    sets: list[docset_mod.DocSet] = []
    dirs_by_id: dict[str, list[str]] = {}
    for benchmark in BENCHMARKS:
        dirs = docset_mod.oracle_dirs_for(cfg, benchmark)
        if not any(Path(d).is_dir() for d in dirs):
            console.print(f"{benchmark}: no oracle directory configured")
            continue
        d = docset_mod.benchmark_docset(benchmark, dirs, holdout=holdout, holdout_mode="excluded")
        sets.append(d)
        dirs_by_id[d.id] = [str(p) for p in dirs]
        console.print(f"{benchmark}: {d.n} documents, docset {d.id}")
    if write:
        docset_mod.write_docsets(docset_mod.DEFAULT_DOCSETS_PATH, sets, source_dirs=dirs_by_id)
        console.print(f"wrote {docset_mod.DEFAULT_DOCSETS_PATH}")
```

(`load_config` and `BENCHMARKS` are already imported in `cli.py`; confirm with `grep -n "^from\|^import" src/neurotic_docx_bench/cli.py`.)

- [ ] **Step 6: Add a CLI test and run it**

Append to `tests/test_ledger_docset.py`:

```python
def test_docset_command_lists_benchmarks(tmp_path: Path, monkeypatch) -> None:
    from typer.testing import CliRunner
    from neurotic_docx_bench.cli import app

    oracle = _touch(tmp_path / "pdf_redlines_word", "a_b_redline.pdf", "c_d_redline.pdf")
    (tmp_path / "bench.yaml").write_text(
        f"source_of_truth: {oracle}\nscoring: {{dpi: 144}}\nruns: []\n"
    )
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(app, ["docset", "--config", "bench.yaml", "--write"])
    assert result.exit_code == 0, result.output
    assert "script_redlines: 2 documents" in result.output
    assert (tmp_path / "results" / "docsets.json").is_file()
```

Run: `uv run pytest tests/test_ledger_docset.py tests/test_cli.py tests/test_cli_emit.py -q -n 0`
Expected: all pass.

- [ ] **Step 7: Record the current document sets and commit**

```bash
uv run bench docset --write
git add src/neurotic_docx_bench/ledger/docset.py src/neurotic_docx_bench/cli.py tests/test_ledger_docset.py results/docsets.json
git commit -m "feat(itt): fixed document set per benchmark; missing candidate outputs enter at 0"
git push -u origin consolidate/02-failures
```

Expected `bench docset` output on the mac (numbers are what the corpus holds today; script_redlines must be 763 minus the sealed holdout):

```
script_redlines: 7xx documents, docset ...
accepted_changes: 2xx documents, docset ...
roundtrip: 166 documents, docset ...
visual_rendering: 205 documents, docset ...
visual_redlines: 232 documents, docset ...
visual_accepted_changes: 166 documents, docset ...
```

Open PR 2: "itt: failed documents counted once; fixed denominators".

---

## PR 3: renderer, hardware and speed provenance

```bash
git checkout -b consolidate/03-provenance consolidate/02-failures
```

### Task 6: Renderer identity and hardware on every emitted line

**Files:**
- Create: `src/neurotic_docx_bench/hardware.py`
- Modify: `src/neurotic_docx_bench/cli.py` (`_renderer_id`, emission)
- Test: `tests/test_hardware.py`

- [ ] **Step 1: Write the failing tests**

```python
"""Hardware fingerprint and renderer identity: pure, cheap, always present."""

from __future__ import annotations

from neurotic_docx_bench import hardware
from neurotic_docx_bench.config import RunConfig


def test_hardware_info_has_the_fields_the_tables_print() -> None:
    info = hardware.hardware_info()
    assert set(info) >= {"system", "release", "machine", "cpu", "cores", "ram_gb", "python"}
    assert isinstance(info["cores"], int) and info["cores"] >= 1
    assert isinstance(info["ram_gb"], float) and info["ram_gb"] > 0
    assert info["cpu"]  # never empty: falls back to platform.machine()


def test_hardware_info_is_json_serializable() -> None:
    import json
    json.dumps(hardware.hardware_info())


def test_renderer_id_for_each_render_backend(monkeypatch) -> None:
    monkeypatch.setattr(hardware, "soffice_version", lambda: "26.2.4.2")
    assert hardware.renderer_id(RunConfig(name="x", render="soffice")) == "soffice-26.2.4.2"
    assert hardware.renderer_id(RunConfig(name="x", render="playwright", package="superdoc@2.18.0")) == "playwright:superdoc@2.18.0"
    assert hardware.renderer_id(RunConfig(name="x", render="passthrough")) == "passthrough"
    assert hardware.renderer_id(RunConfig(name="x", render="word")) == "word"


def test_renderer_id_soffice_unknown_version(monkeypatch) -> None:
    monkeypatch.setattr(hardware, "soffice_version", lambda: None)
    assert hardware.renderer_id(RunConfig(name="x", render="soffice")) == "soffice-unknown"
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_hardware.py -q -n 0`
Expected: `ModuleNotFoundError: No module named 'neurotic_docx_bench.hardware'`.

- [ ] **Step 3: Write the module**

`src/neurotic_docx_bench/hardware.py`:

```python
"""Machine and renderer identity stamped on every emitted result line.

Speed numbers without a machine are not comparable; fidelity numbers without a
renderer version are not reproducible. Both are cheap to record and were absent.
"""

from __future__ import annotations

import os
import platform
import subprocess

from neurotic_docx_bench.config import RunConfig


def soffice_version() -> str | None:
    """LibreOffice version string, via the canary's parser; None when not installed."""
    from neurotic_docx_bench import canary

    try:
        return canary.current_soffice_version()
    except (OSError, RuntimeError):
        return None


def _cpu_brand() -> str:
    system = platform.system()
    try:
        if system == "Darwin":
            out = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True, timeout=5,
            )
            if out.returncode == 0 and out.stdout.strip():
                return out.stdout.strip()
        elif system == "Linux":
            with open("/proc/cpuinfo", encoding="utf-8") as fh:
                for line in fh:
                    if line.lower().startswith("model name"):
                        return line.split(":", 1)[1].strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return platform.processor() or platform.machine()


def _ram_gb() -> float:
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        return round(pages * page_size / 2**30, 1)
    except (ValueError, OSError, AttributeError):
        return 0.0


def hardware_info() -> dict[str, object]:
    return {
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "cpu": _cpu_brand(),
        "cores": os.cpu_count() or 1,
        "ram_gb": _ram_gb() or 0.1,
        "python": platform.python_version(),
    }


def renderer_id(rc: RunConfig) -> str:
    if rc.render == "soffice":
        return f"soffice-{soffice_version() or 'unknown'}"
    if rc.render == "playwright":
        return f"playwright:{rc.package or rc.name}"
    return rc.render
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/test_hardware.py -q -n 0`
Expected: `4 passed`.

- [ ] **Step 5: Wire emission**

In `cli._emit_and_gate_benchmark`, pass to `build_results_line`:

```python
        tool_id=_registry_tool_id(rc),
        configuration=_registry_configuration(rc),
        renderer_id=hardware.renderer_id(rc),
        hardware=hardware.hardware_info(),
```

with two tiny helpers next to `_docset_for`:

```python
def _registry_entry(rc: RunConfig):
    from neurotic_docx_bench.ledger.registry import DEFAULT_REGISTRY_PATH, load_registry

    if not DEFAULT_REGISTRY_PATH.is_file():
        return None
    return load_registry(DEFAULT_REGISTRY_PATH).resolve_bench(
        vendor=rc.vendor or rc.name, run_name=rc.name, render=rc.render,
    )


def _registry_tool_id(rc: RunConfig) -> str | None:
    entry = _registry_entry(rc)
    return entry.id if entry else None


def _registry_configuration(rc: RunConfig) -> str | None:
    entry = _registry_entry(rc)
    return entry.configuration if entry else None
```

and `from neurotic_docx_bench import hardware` in the imports.

- [ ] **Step 6: Run the CLI emit tests and commit**

Run: `uv run pytest tests/test_cli_emit.py tests/test_emit_jsonl.py tests/test_gate_snapshot.py -q -n 0`
Expected: pass.

```bash
uv run ruff check src tests && uv run ruff format src tests && uv run ty check src
git add src/neurotic_docx_bench/hardware.py src/neurotic_docx_bench/cli.py tests/test_hardware.py
git commit -m "feat(provenance): renderer id, hardware and registry tool id on every emitted line"
```

---

### Task 7: Tool version and hardware on speed rows (TypeScript) and `SpeedRow` loader

**Files:**
- Create: `scripts/lib/provenance.ts`
- Create: `scripts/lib/provenance.test.ts`
- Modify: `scripts/redline_speed_bench.ts` and `scripts/speed-bench.ts` (each row gains `tool_version` and `hardware`)
- Modify: `src/neurotic_docx_bench/ledger/rows.py` (add `SpeedRow`, `load_speed_rows`)
- Test: `tests/test_ledger_rows.py` (append)

- [ ] **Step 1: Write the failing vitest**

`scripts/lib/provenance.test.ts`:

```ts
import { mkdtempSync, mkdirSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { hardwareInfo, toolVersionForDist } from "./provenance.ts";

describe("toolVersionForDist", () => {
	it("matches the Python pin shape: <label>@<12 hex>[+git.<sha>]", () => {
		const dist = mkdtempSync(join(tmpdir(), "dist-"));
		writeFileSync(join(dist, "package.json"), JSON.stringify({ version: "0.2.0" }));
		mkdirSync(join(dist, "pkg"));
		writeFileSync(join(dist, "pkg", "a.js"), "console.log(1)\n");
		writeFileSync(join(dist, "ENGINE_COMMIT.txt"), "ebf1a7996df49f99fb40f4f67713e61cfd19c731\n");
		const pin = toolVersionForDist(dist);
		expect(pin).toMatch(/^0\.2\.0@[0-9a-f]{12}\+git\.ebf1a7996df49f99fb40f4f67713e61cfd19c731$/);
	});

	it("ENGINE_*.txt files never change the hash", () => {
		const dist = mkdtempSync(join(tmpdir(), "dist-"));
		writeFileSync(join(dist, "a.js"), "x");
		const before = toolVersionForDist(dist);
		writeFileSync(join(dist, "ENGINE_NOTE.txt"), "hello");
		expect(toolVersionForDist(dist)).toBe(before);
	});

	it("returns null for a missing directory", () => {
		expect(toolVersionForDist("/nonexistent/dist")).toBeNull();
	});
});

describe("hardwareInfo", () => {
	it("carries the fields the tables print", () => {
		const h = hardwareInfo();
		expect(h.cores).toBeGreaterThan(0);
		expect(h.ram_gb).toBeGreaterThan(0);
		expect(typeof h.cpu).toBe("string");
		expect(h.system).toBe(process.platform);
	});
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `bunx vitest run scripts/lib/provenance.test.ts`
Expected: `Failed to resolve import "./provenance.ts"`.

- [ ] **Step 3: Write the module**

`scripts/lib/provenance.ts`:

```ts
/**
 * Provenance for speed rows: the same pin shape the Python side writes
 * (tool_updater.resolve_local_version) and a machine fingerprint.
 */
import { createHash } from "node:crypto";
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { cpus, platform, release, totalmem, arch } from "node:os";
import { join, relative } from "node:path";

export interface HardwareInfo {
	system: string;
	release: string;
	machine: string;
	cpu: string;
	cores: number;
	ram_gb: number;
	node: string;
}

function walk(dir: string, out: string[]): void {
	for (const ent of readdirSync(dir, { withFileTypes: true })) {
		const p = join(dir, ent.name);
		if (ent.isDirectory()) walk(p, out);
		else if (ent.isFile()) out.push(p);
	}
}

/** `<label>@<sha256[:12]>[+git.<sha>]` over (relpath, bytes) of every file in the dist. */
export function toolVersionForDist(dist: string): string | null {
	if (!existsSync(dist) || !statSync(dist).isDirectory()) return null;
	let label = dist.split("/").filter(Boolean).at(-1) ?? "dist";
	const pkg = join(dist, "package.json");
	if (existsSync(pkg)) {
		try {
			const v = (JSON.parse(readFileSync(pkg, "utf8")) as { version?: string }).version;
			if (v) label = String(v);
		} catch {
			/* keep directory name */
		}
	}
	const files: string[] = [];
	walk(dist, files);
	files.sort((a, b) => (relative(dist, a) < relative(dist, b) ? -1 : 1));
	const h = createHash("sha256");
	for (const f of files) {
		const rel = relative(dist, f).split("\\").join("/");
		const base = rel.split("/").at(-1) ?? rel;
		if (base.startsWith("ENGINE_") && base.endsWith(".txt")) continue;
		h.update(rel);
		h.update(readFileSync(f));
	}
	let pin = `${label}@${h.digest("hex").slice(0, 12)}`;
	const commitFile = join(dist, "ENGINE_COMMIT.txt");
	if (existsSync(commitFile)) {
		const commit = readFileSync(commitFile, "utf8").trim();
		if (commit) pin += `+git.${commit}`;
	}
	return pin;
}

export function hardwareInfo(): HardwareInfo {
	const list = cpus();
	return {
		system: platform(),
		release: release(),
		machine: arch(),
		cpu: list[0]?.model ?? arch(),
		cores: list.length || 1,
		ram_gb: Math.round((totalmem() / 2 ** 30) * 10) / 10,
		node: process.version,
	};
}
```

Note: Python sorts with `sorted(p for p in dist.rglob("*") if p.is_file())` (path order); the TS sorts by relative path string. Both are deterministic per side; cross-language equality is not required (the Python pin is what fidelity lines carry, the TS pin what speed lines carry; the report joins on `tool_id`, and shows both pins).

- [ ] **Step 4: Run the vitest**

Run: `bunx vitest run scripts/lib/provenance.test.ts`
Expected: `4 passed`.

- [ ] **Step 5: Stamp the rows in both speed scripts**

In `scripts/redline_speed_bench.ts`, find where a result row object is assembled for output (the object with keys `kind`, `tool`, `engine`, `dist`, `runtime`, `run_ts`, ... `throughput_per_s`; locate with `grep -n "throughput_per_s" scripts/redline_speed_bench.ts`). Add two properties to that object:

```ts
		tool_version: dist ? toolVersionForDist(dist) : null,
		hardware: hardwareInfo(),
```

with `import { hardwareInfo, toolVersionForDist } from "./lib/provenance.ts";` at the top. `dist` is the per-method dist path already carried in the row as `dist`; when the method has none (npm-installed docxodus), read the installed version instead:

```ts
function npmVersion(pkg: string): string | null {
	try {
		return (JSON.parse(readFileSync(new URL(`../node_modules/${pkg}/package.json`, import.meta.url), "utf8")) as { version?: string }).version ?? null;
	} catch {
		return null;
	}
}
```

and use `tool_version: dist ? toolVersionForDist(dist) : npmVersion(packageNameForMethod(method))` where `packageNameForMethod` maps `docxodus` to `"docxodus"` and `superdoc` to `"@superdoc-dev/sdk"` (add the small map next to the existing method table). Same two properties in `scripts/speed-bench.ts` rows.

- [ ] **Step 6: Add the `SpeedRow` loader (Python) with its tests**

Append to `tests/test_ledger_rows.py`:

```python
def _speed_line(**over) -> dict:
    base = {
        "schema": 1, "kind": "speed_redlines", "tool": "jubarte-rust-inproc", "runtime": "rust",
        "run_ts": "2026-08-15T10:00:00Z", "fixture_count": 1000, "pair_count": 5000,
        "n": 5000, "failures": 0, "unit": "ms_per_redline",
        "mean": 25.34, "median": 6.2, "p95": 110.76, "throughput_per_s": 39.5,
        "tool_version": "jubarte-rust@17ea47e9a0d7+git.bf3d07d",
        "hardware": {"cpu": "Apple M3", "cores": 12},
    }
    base.update(over)
    return base


def test_speed_row_maps_tool_and_inproc(tmp_path: Path, registry) -> None:
    import yaml as _yaml
    doc = _yaml.safe_load((tmp_path / "reg.yaml").read_text())
    doc["tools"].append({"id": "jubarte-rust", "vendor": "jubarte", "display": "jubarte-rust", "role": "generator",
                         "engine": "jubarte-redlines", "affiliated": True, "speed_tools": ["jubarte-rust"]})
    (tmp_path / "reg2.yaml").write_text(_yaml.safe_dump(doc))
    reg2 = load_registry(tmp_path / "reg2.yaml")
    row = rws.speed_row_from_line(_speed_line(), reg2)
    assert row is not None
    assert row.tool_id == "jubarte-rust" and row.inproc is True and row.kind == "large"
    assert row.pin.display == "jubarte-rust@17ea47e9a0d7+git.bf3d07d"
    assert row.median_ms == 6.2 and row.fixture_count == 1000 and row.n == 5000
    assert row.hardware == {"cpu": "Apple M3", "cores": 12}


def test_speed_row_without_version_is_unpinned(registry, tmp_path: Path) -> None:
    import yaml as _yaml
    doc = _yaml.safe_load((tmp_path / "reg.yaml").read_text())
    doc["tools"].append({"id": "docxodus-csharp", "vendor": "docxodus", "display": "docxodus (C#)", "role": "generator",
                         "engine": "docxodus", "speed_tools": ["docxodus-csharp"]})
    (tmp_path / "reg2.yaml").write_text(_yaml.safe_dump(doc))
    reg2 = load_registry(tmp_path / "reg2.yaml")
    row = rws.speed_row_from_line(_speed_line(tool="docxodus-csharp", tool_version=None, hardware=None, kind="speed"), reg2)
    assert row is not None and row.pin.pinned is False and row.kind == "micro" and row.hardware is None


def test_speed_row_rejects_other_units_and_errors(registry) -> None:
    assert rws.speed_row_from_line(_speed_line(unit="ms_per_render"), registry) is None
    assert rws.speed_row_from_line(_speed_line(error="boom", median=None), registry) is None


def test_load_speed_rows_reads_jsonl_and_summaries(tmp_path: Path, registry) -> None:
    import yaml as _yaml
    doc = _yaml.safe_load((tmp_path / "reg.yaml").read_text())
    doc["tools"].append({"id": "jubarte-rust", "vendor": "jubarte", "display": "jubarte-rust", "role": "generator",
                         "engine": "jubarte-redlines", "speed_tools": ["jubarte-rust"]})
    (tmp_path / "reg2.yaml").write_text(_yaml.safe_dump(doc))
    reg2 = load_registry(tmp_path / "reg2.yaml")
    (tmp_path / "speed.jsonl").write_text(json.dumps(_speed_line()) + "\n")
    summary_dir = tmp_path / "redline_speed_bench" / "run1"
    summary_dir.mkdir(parents=True)
    (summary_dir / "summary.json").write_text(json.dumps({
        "runTs": "2026-08-16T10:00:00Z", "fixtures": 200, "pairs": 500,
        "rows": [dict(_speed_line(kind="redline_speed_bench", fixture_count=None, pair_count=None))],
    }))
    rows, unmapped = rws.load_speed_rows(tmp_path / "speed.jsonl", tmp_path / "redline_speed_bench", reg2)
    assert unmapped == []
    assert sorted((r.fixture_count, r.pair_count) for r in rows) == [(200, 500), (1000, 5000)]
```

Add to `src/neurotic_docx_bench/ledger/rows.py`:

```python
class SpeedRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: str
    display: str
    affiliated: bool
    kind: Literal["large", "micro"]
    inproc: bool
    runtime: str
    pin: ToolPin
    timestamp: datetime
    fixture_count: int | None
    pair_count: int | None
    n: int
    failures: int
    median_ms: float
    mean_ms: float
    p95_ms: float | None
    hardware: dict[str, object] | None = None
    source_path: str = ""


def speed_row_from_line(data: dict, registry: Registry, *, source_path: str = "") -> SpeedRow | None:
    if str(data.get("unit") or "ms_per_redline") != "ms_per_redline":
        return None
    if data.get("error") and data.get("median") is None:
        return None
    kind_raw = str(data.get("kind") or "speed")
    kind: Literal["large", "micro"] = "large" if kind_raw in {"speed_redlines", "redline_speed_bench"} else "micro"
    tool = str(data.get("tool") or data.get("engine") or "")
    entry, inproc = registry.resolve_speed(tool)
    if entry is None or not tool:
        return None
    n = int(_num(data.get("n")))
    if n <= 0:
        return None
    fixture = data.get("fixture_count", data.get("fixture_target"))
    pair = data.get("pair_count")
    return SpeedRow(
        tool_id=entry.id,
        display=entry.display,
        affiliated=entry.affiliated,
        kind=kind,
        inproc=inproc,
        runtime=str(data.get("runtime") or ""),
        pin=ToolPin.parse(data.get("tool_version")),
        timestamp=_timestamp(data),
        fixture_count=int(_num(fixture)) if fixture is not None else None,
        pair_count=int(_num(pair)) if pair is not None else None,
        n=n,
        failures=int(_num(data.get("failures"))),
        median_ms=_num(data.get("median")),
        mean_ms=_num(data.get("mean")),
        p95_ms=_num(data["p95"]) if data.get("p95") is not None else None,
        hardware=data.get("hardware") if isinstance(data.get("hardware"), dict) else None,
        source_path=source_path,
    )


def load_speed_rows(
    speed_jsonl: Path, summaries_root: Path, registry: Registry,
) -> tuple[list[SpeedRow], list[dict]]:
    rows: list[SpeedRow] = []
    unmapped: list[dict] = []

    def ingest(data: dict, source: str, fixtures: object = None, pairs: object = None) -> None:
        data = dict(data)
        if data.get("fixture_count") is None and fixtures is not None:
            data["fixture_count"] = fixtures
        if data.get("pair_count") is None and pairs is not None:
            data["pair_count"] = pairs
        row = speed_row_from_line(data, registry, source_path=source)
        if row is None:
            if data.get("tool") and registry.resolve_speed(str(data["tool"]))[0] is None:
                unmapped.append({"tool": data.get("tool"), "source": source})
            return
        rows.append(row)

    if Path(speed_jsonl).is_file():
        with Path(speed_jsonl).open(encoding="utf-8") as fh:
            for raw in fh:
                if raw.strip():
                    try:
                        ingest(json.loads(raw), str(speed_jsonl))
                    except json.JSONDecodeError:
                        continue
    if Path(summaries_root).is_dir():
        for summary in sorted(Path(summaries_root).rglob("summary.json")):
            try:
                payload = json.loads(summary.read_text())
            except (json.JSONDecodeError, OSError):
                continue
            for raw in payload.get("rows") or []:
                if isinstance(raw, dict):
                    if not raw.get("kind"):
                        raw = {**raw, "kind": "speed_redlines"}
                    if not raw.get("run_ts") and payload.get("runTs"):
                        raw = {**raw, "run_ts": payload["runTs"]}
                    ingest(raw, str(summary), payload.get("fixtures"), payload.get("pairs"))
    return rows, unmapped
```

- [ ] **Step 7: Run everything touched and commit**

Run: `uv run pytest tests/test_ledger_rows.py -q -n 0 && bunx vitest run scripts/lib/provenance.test.ts scripts/redline_scoreboard.test.ts && bun run typecheck`
Expected: pytest 14 passed; vitest green; tsc clean.

```bash
git add scripts/lib/provenance.ts scripts/lib/provenance.test.ts scripts/redline_speed_bench.ts scripts/speed-bench.ts src/neurotic_docx_bench/ledger/rows.py tests/test_ledger_rows.py
git commit -m "feat(speed): stamp tool_version and hardware on speed rows; SpeedRow loader"
git push -u origin consolidate/03-provenance
```

Open PR 3: "provenance: renderer, hardware, speed pins".

---

## PR 4: one ranking policy, uncertainty, one generator

```bash
git checkout -b consolidate/04-report consolidate/03-provenance
```

### Task 8: Ranking policy as pure functions

**Files:**
- Create: `src/neurotic_docx_bench/ledger/policy.py`
- Test: `tests/test_ledger_policy.py`

- [ ] **Step 1: Write the failing tests**

```python
"""One policy for every tool: eligibility, comparability groups, latest eligible run, ranks."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import yaml

from neurotic_docx_bench.ledger import policy as pol
from neurotic_docx_bench.ledger.pins import ToolPin
from neurotic_docx_bench.ledger.registry import load_registry
from neurotic_docx_bench.ledger.rows import ResultRow

T0 = datetime(2026, 8, 1, tzinfo=UTC)


@pytest.fixture
def registry(tmp_path: Path):
    doc = {"schema_version": 1, "tools": [
        {"id": "a", "vendor": "a", "display": "A", "role": "generator", "engine": "a", "bench_vendors": ["a"]},
        {"id": "b", "vendor": "b", "display": "B", "role": "generator", "engine": "b", "bench_vendors": ["b"], "affiliated": True},
        {"id": "old", "vendor": "old", "display": "Old", "role": "generator", "engine": "old", "bench_vendors": ["old"], "status": "retired"},
        {"id": "cal", "vendor": "bench", "display": "oracle", "role": "calibration", "engine": "pipeline", "bench_vendors": ["cal"]},
        {"id": "na", "vendor": "na", "display": "NA", "role": "converter", "engine": "na", "not_applicable": ["script_redlines"]},
    ]}
    p = tmp_path / "reg.yaml"
    p.write_text(yaml.safe_dump(doc))
    return load_registry(p)


def row(tool: str, *, median: float, mean: float | None = None, n: int = 3, days: int = 0,
        docset: str | None = "d1", renderer: str | None = "soffice-26", scores: dict | None = None,
        holdout: str | None = "excluded", pin: str = "1.0", benchmark: str = "script_redlines",
        affiliated: bool = False, crev: str | None = "rev1") -> ResultRow:
    scores = scores if scores is not None else {f"doc{i}": median for i in range(n)}
    return ResultRow(
        source="bench", id_run=f"run-{tool}-{days}", tool_id=tool, display=tool.upper(), affiliated=affiliated,
        benchmark=benchmark, pin=ToolPin.parse(pin), timestamp=T0 + timedelta(days=days),
        corpus_revision=crev, docset_id=docset, renderer_id=renderer, scorer="pagefair-v2",
        n_scored=len(scores), n_failed_docs=0, n_failure_events=0, itt_n=len(scores),
        itt_mean=mean if mean is not None else median, itt_median=median, mean=mean if mean is not None else median,
        median=median, exact_100=0, scores=scores, holdout_mode=holdout,
    )


def test_group_key_uses_docset_then_corpus_revision_then_unstamped() -> None:
    assert pol.group_key(row("a", median=1)).docset == "d1"
    assert pol.group_key(row("a", median=1, docset=None)).docset == "rev1"
    assert pol.group_key(row("a", median=1, docset=None, crev=None)).docset == "unstamped"
    assert pol.group_key(row("a", median=1, renderer=None)).renderer == "unknown"


def test_expected_n_prefers_recorded_docset_size() -> None:
    rows = [row("a", median=1, n=3), row("b", median=1, n=5)]
    assert pol.expected_n(rows, {"d1": {"n": 4}}) == 4
    assert pol.expected_n(rows, {}) == 5


def test_eligibility_reasons(registry) -> None:
    ok = pol.eligibility(row("a", median=1, n=3), expected=3, retractions=[], registry=registry)
    assert ok.eligible and ok.reasons == ()
    legacy = pol.eligibility(row("a", median=1, n=3, crev=None, docset=None), expected=3, retractions=[], registry=registry)
    assert not legacy.eligible and "legacy provenance" in legacy.reasons
    short = pol.eligibility(row("a", median=1, n=2), expected=3, retractions=[], registry=registry)
    assert not short.eligible and "incomplete: 2 of 3 documents" in short.reasons
    hold = pol.eligibility(row("a", median=1, holdout="only"), expected=3, retractions=[], registry=registry)
    assert "holdout-only run" in hold.reasons
    retired = pol.eligibility(row("old", median=1), expected=3, retractions=[], registry=registry)
    assert "retired tool" in retired.reasons
    r = pol.Retraction(id_run="run-a-0", reason="harness bug", retracted_at=T0, by="arthur")
    gone = pol.eligibility(row("a", median=1), expected=3, retractions=[r], registry=registry)
    assert "retracted: harness bug" in gone.reasons


def test_headline_takes_latest_eligible_run_per_tool_not_the_best(registry) -> None:
    rows = [
        row("a", median=95, days=0),       # older, better
        row("a", median=80, days=5),       # latest: this one is shown
        row("b", median=90, days=1, affiliated=True),
    ]
    tables = pol.select_headline(rows, registry=registry, retractions=[], docsets={"d1": {"n": 3}}, tie_fn=lambda x, y: False)
    t = tables["script_redlines"]
    assert [(r.row.tool_id, r.row.itt_median, r.rank) for r in t.rows] == [("b", 90, 1), ("a", 80, 2)]


def test_headline_current_group_is_the_one_with_the_newest_eligible_row(registry) -> None:
    rows = [row("a", median=99, days=0, docset="d0"), row("a", median=70, days=9, docset="d1"), row("b", median=60, days=8, docset="d1")]
    tables = pol.select_headline(rows, registry=registry, retractions=[], docsets={"d0": {"n": 3}, "d1": {"n": 3}}, tie_fn=lambda x, y: False)
    t = tables["script_redlines"]
    assert t.group.docset == "d1"
    assert [r.row.tool_id for r in t.rows] == ["a", "b"]
    assert [h.docset for h in t.history_groups] == ["d0"]


def test_retracted_run_falls_back_to_previous_run(registry) -> None:
    rows = [row("a", median=95, days=0), row("a", median=10, days=5)]
    r = pol.Retraction(id_run="run-a-5", reason="broken harness", retracted_at=T0, by="arthur")
    t = pol.select_headline(rows, registry=registry, retractions=[r], docsets={"d1": {"n": 3}}, tie_fn=lambda x, y: False)["script_redlines"]
    assert [(x.row.id_run, x.row.itt_median) for x in t.rows] == [("run-a-0", 95)]
    assert [(e.row.id_run, e.verdict.reasons) for e in t.excluded] == [("run-a-5", ("retracted: broken harness",))]


def test_ties_share_a_rank(registry) -> None:
    rows = [row("a", median=91.4, days=1), row("b", median=91.1, days=1)]
    t = pol.select_headline(rows, registry=registry, retractions=[], docsets={"d1": {"n": 3}}, tie_fn=lambda x, y: True)["script_redlines"]
    assert [(r.rank, r.tied_with_previous) for r in t.rows] == [(1, False), (1, True)]


def test_calibration_and_not_applicable_are_listed_not_ranked(registry) -> None:
    rows = [row("a", median=80), row("cal", median=100)]
    t = pol.select_headline(rows, registry=registry, retractions=[], docsets={"d1": {"n": 3}}, tie_fn=lambda x, y: False)["script_redlines"]
    assert [r.row.tool_id for r in t.rows] == ["a"]
    assert [c.tool_id for c in t.calibration] == ["cal"]
    assert [e.id for e in t.not_applicable] == ["na"]


def test_load_retractions_round_trip(tmp_path: Path) -> None:
    p = tmp_path / "retractions.jsonl"
    r = pol.Retraction(id_run="x", benchmark="roundtrip", reason="r", retracted_at=T0, by="me")
    pol.append_retraction(p, r)
    assert pol.load_retractions(p) == [r]
    assert pol.load_retractions(tmp_path / "missing.jsonl") == []


def test_speed_headline_requires_pin_and_canonical_fixture_count(registry, tmp_path: Path) -> None:
    from neurotic_docx_bench.ledger.rows import SpeedRow
    doc = yaml.safe_load((tmp_path / "reg.yaml").read_text())
    doc["tools"][0]["speed_tools"] = ["a"]
    doc["tools"][1]["speed_tools"] = ["b"]
    (tmp_path / "reg2.yaml").write_text(yaml.safe_dump(doc))
    reg2 = load_registry(tmp_path / "reg2.yaml")

    def srow(tool, *, median, pinned=True, fixtures=1000, days=0, inproc=False, kind="large"):
        return SpeedRow(tool_id=tool, display=tool.upper(), affiliated=False, kind=kind, inproc=inproc, runtime="x",
                        pin=ToolPin.parse("1.0" if pinned else None), timestamp=T0 + timedelta(days=days),
                        fixture_count=fixtures, pair_count=5000 if fixtures == 1000 else 50, n=5000, failures=0,
                        median_ms=median, mean_ms=median, p95_ms=None)

    rows = [srow("a", median=6.0), srow("a", median=9.0, inproc=True), srow("b", median=5.0, pinned=False), srow("b", median=7.0, fixtures=50)]
    t = pol.select_speed_headline(rows, registry=reg2)
    assert [(r.row.tool_id, r.row.inproc, r.rank) for r in t.large] == [("a", False, 1), ("a", True, 2)]
    assert sorted(e.verdict.reasons[0] for e in t.excluded) == ["incomplete: 50 of 1000 fixtures", "unpinned speed row"]
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_ledger_policy.py -q -n 0`
Expected: `ModuleNotFoundError: No module named 'neurotic_docx_bench.ledger.policy'`.

- [ ] **Step 3: Write the module**

`src/neurotic_docx_bench/ledger/policy.py`:

```python
"""The ranking policy, written once, applied to every tool.

- A row is *eligible* when it is stamped (corpus_revision + per-doc scores), complete
  (its ITT n equals the document set size), not a holdout-only run, not retracted,
  from an active tool, and not a calibration row.
- Rows compare only inside one *group*: (benchmark, lens, document set, renderer,
  scorer). The *current* group of a benchmark is the one holding the newest eligible
  row.
- The headline shows one row per tool: the latest eligible run in the current group.
  There is no best-of-N over runs and no best pin; that is what history is for.
- Rank ties come from ``tie_fn`` (Task 9: the paired bootstrap interval of the median
  difference includes 0).
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from neurotic_docx_bench.ledger.registry import Registry, ToolEntry
from neurotic_docx_bench.ledger.rows import ResultRow, SpeedRow

DEFAULT_RETRACTIONS_PATH = Path("results/retractions.jsonl")
CANONICAL_SPEED_FIXTURES = 1000
MIN_MICRO_N = 30


class Retraction(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id_run: str
    benchmark: str | None = None
    reason: str
    retracted_at: datetime
    by: str


def load_retractions(path: Path) -> list[Retraction]:
    if not Path(path).is_file():
        return []
    out: list[Retraction] = []
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        if raw.strip():
            out.append(Retraction.model_validate_json(raw))
    return out


def append_retraction(path: Path, retraction: Retraction) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("a", encoding="utf-8") as fh:
        fh.write(retraction.model_dump_json() + "\n")


def find_retraction(row: ResultRow, retractions: Sequence[Retraction]) -> Retraction | None:
    for r in retractions:
        if r.id_run == row.id_run and (r.benchmark is None or r.benchmark == row.benchmark):
            return r
    return None


class GroupKey(BaseModel):
    model_config = ConfigDict(frozen=True)

    benchmark: str
    lens: str
    docset: str
    renderer: str
    scorer: str


def group_key(row: ResultRow) -> GroupKey:
    return GroupKey(
        benchmark=row.benchmark,
        lens=row.lens,
        docset=row.docset_id or row.corpus_revision or "unstamped",
        renderer=row.renderer_id or (f"legacy-{row.render}" if row.render else "unknown"),
        scorer=row.scorer,
    )


def expected_n(rows: Sequence[ResultRow], docsets: Mapping[str, Mapping[str, object]]) -> int:
    for r in rows:
        if r.docset_id and r.docset_id in docsets:
            n = docsets[r.docset_id].get("n")
            if isinstance(n, int) and n > 0:
                return n
    stamped = [r.itt_n for r in rows if r.provenance == "stamped"]
    return max(stamped) if stamped else max((r.itt_n for r in rows), default=0)


class Verdict(BaseModel):
    model_config = ConfigDict(frozen=True)

    eligible: bool
    reasons: tuple[str, ...] = ()


def eligibility(
    row: ResultRow, *, expected: int, retractions: Sequence[Retraction], registry: Registry,
) -> Verdict:
    reasons: list[str] = []
    entry = registry.by_id(row.tool_id)
    if row.provenance != "stamped":
        reasons.append("legacy provenance")
    if row.holdout_mode == "only":
        reasons.append("holdout-only run")
    if expected and row.itt_n != expected:
        reasons.append(f"incomplete: {row.itt_n} of {expected} documents")
    if entry.status == "retired":
        reasons.append("retired tool")
    if not entry.applies_to(row.benchmark):
        reasons.append("not applicable")
    if entry.role == "calibration":
        reasons.append("calibration row")
    retraction = find_retraction(row, retractions)
    if retraction is not None:
        reasons.append(f"retracted: {retraction.reason}")
    return Verdict(eligible=not reasons, reasons=tuple(reasons))


class RankedRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    row: ResultRow
    rank: int
    tied_with_previous: bool = False


class ExcludedRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    row: ResultRow
    verdict: Verdict


class HeadlineTable(BaseModel):
    model_config = ConfigDict(frozen=True)

    benchmark: str
    group: GroupKey | None
    expected_n: int
    rows: list[RankedRow]
    calibration: list[ResultRow]
    excluded: list[ExcludedRow]
    not_applicable: list[ToolEntry]
    history_groups: list[GroupKey]


TieFn = Callable[[ResultRow, ResultRow], bool]


def _latest_per_tool(rows: Sequence[ResultRow]) -> list[ResultRow]:
    latest: dict[str, ResultRow] = {}
    for r in sorted(rows, key=lambda x: x.timestamp):
        latest[r.tool_id] = r
    return list(latest.values())


def rank_rows(rows: Sequence[ResultRow], tie_fn: TieFn) -> list[RankedRow]:
    ordered = sorted(rows, key=lambda r: (-r.itt_median, -r.itt_mean, r.display))
    out: list[RankedRow] = []
    for i, r in enumerate(ordered):
        if i == 0:
            out.append(RankedRow(row=r, rank=1))
            continue
        prev = out[-1]
        tied = tie_fn(prev.row, r)
        out.append(RankedRow(row=r, rank=prev.rank if tied else i + 1, tied_with_previous=tied))
    return out


def select_headline(
    rows: Sequence[ResultRow],
    *,
    registry: Registry,
    retractions: Sequence[Retraction],
    docsets: Mapping[str, Mapping[str, object]],
    tie_fn: TieFn,
) -> dict[str, HeadlineTable]:
    by_bench: dict[str, list[ResultRow]] = {}
    for r in rows:
        by_bench.setdefault(r.benchmark, []).append(r)

    tables: dict[str, HeadlineTable] = {}
    for benchmark, bench_rows in sorted(by_bench.items()):
        groups: dict[GroupKey, list[ResultRow]] = {}
        for r in bench_rows:
            groups.setdefault(group_key(r), []).append(r)
        verdicts: dict[str, Verdict] = {}
        expected_by_group: dict[GroupKey, int] = {}
        for g, members in groups.items():
            exp = expected_n(members, docsets)
            expected_by_group[g] = exp
            for r in members:
                verdicts[r.id_run + "|" + r.benchmark] = eligibility(
                    r, expected=exp, retractions=retractions, registry=registry,
                )

        def verdict(r: ResultRow) -> Verdict:
            return verdicts[r.id_run + "|" + r.benchmark]

        eligible = [r for r in bench_rows if verdict(r).eligible]
        if not eligible:
            tables[benchmark] = HeadlineTable(
                benchmark=benchmark, group=None, expected_n=0, rows=[], calibration=[],
                excluded=[ExcludedRow(row=r, verdict=verdict(r)) for r in _latest_per_tool(bench_rows)],
                not_applicable=[t for t in registry.tools if not t.applies_to(benchmark)],
                history_groups=sorted(groups, key=lambda g: g.docset),
            )
            continue
        newest = max(eligible, key=lambda r: r.timestamp)
        current = group_key(newest)
        members = groups[current]
        ranked = rank_rows(_latest_per_tool([r for r in members if verdict(r).eligible]), tie_fn)
        calibration = _latest_per_tool([
            r for r in members
            if registry.by_id(r.tool_id).role == "calibration" and r.provenance == "stamped"
        ])
        shown = {r.row.id_run for r in ranked} | {c.id_run for c in calibration}
        excluded = [
            ExcludedRow(row=r, verdict=verdict(r))
            for r in _latest_per_tool([m for m in members if not verdict(m).eligible])
            if r.id_run not in shown and registry.by_id(r.tool_id).role != "calibration"
        ]
        tables[benchmark] = HeadlineTable(
            benchmark=benchmark,
            group=current,
            expected_n=expected_by_group[current],
            rows=ranked,
            calibration=calibration,
            excluded=excluded,
            not_applicable=[t for t in registry.tools if not t.applies_to(benchmark)],
            history_groups=sorted((g for g in groups if g != current), key=lambda g: g.docset),
        )
    return tables


# ---- speed ------------------------------------------------------------------


class RankedSpeed(BaseModel):
    model_config = ConfigDict(frozen=True)

    row: SpeedRow
    rank: int


class ExcludedSpeed(BaseModel):
    model_config = ConfigDict(frozen=True)

    row: SpeedRow
    verdict: Verdict


class SpeedHeadline(BaseModel):
    model_config = ConfigDict(frozen=True)

    large: list[RankedSpeed]
    micro: list[RankedSpeed]
    excluded: list[ExcludedSpeed]


def speed_eligibility(row: SpeedRow, registry: Registry) -> Verdict:
    reasons: list[str] = []
    entry = registry.by_id(row.tool_id)
    if not row.pin.pinned:
        reasons.append("unpinned speed row")
    if entry.status == "retired":
        reasons.append("retired tool")
    if row.kind == "large" and (row.fixture_count or 0) != CANONICAL_SPEED_FIXTURES:
        reasons.append(f"incomplete: {row.fixture_count or 0} of {CANONICAL_SPEED_FIXTURES} fixtures")
    if row.kind == "micro" and row.n < MIN_MICRO_N:
        reasons.append(f"too few samples: {row.n} of {MIN_MICRO_N}")
    return Verdict(eligible=not reasons, reasons=tuple(reasons))


def select_speed_headline(rows: Sequence[SpeedRow], *, registry: Registry) -> SpeedHeadline:
    excluded: list[ExcludedSpeed] = []
    tables: dict[str, list[SpeedRow]] = {"large": [], "micro": []}
    latest: dict[tuple[str, str, bool], SpeedRow] = {}
    for r in sorted(rows, key=lambda x: x.timestamp):
        v = speed_eligibility(r, registry)
        if not v.eligible:
            excluded.append(ExcludedSpeed(row=r, verdict=v))
            continue
        latest[(r.kind, r.tool_id, r.inproc)] = r
    for (kind, _tool, _inproc), r in latest.items():
        tables[kind].append(r)
    out: dict[str, list[RankedSpeed]] = {}
    for kind, members in tables.items():
        ordered = sorted(members, key=lambda r: (r.median_ms, r.display))
        out[kind] = [RankedSpeed(row=r, rank=i + 1) for i, r in enumerate(ordered)]
    # Keep only the latest excluded row per (kind, tool, inproc) so the note stays short.
    last_excluded: dict[tuple[str, str, bool], ExcludedSpeed] = {}
    for e in excluded:
        last_excluded[(e.row.kind, e.row.tool_id, e.row.inproc)] = e
    return SpeedHeadline(large=out["large"], micro=out["micro"], excluded=list(last_excluded.values()))


def load_docsets_json(path: Path) -> dict[str, dict]:
    if not Path(path).is_file():
        return {}
    data = json.loads(Path(path).read_text())
    return {str(k): dict(v) for k, v in data.items()} if isinstance(data, dict) else {}
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/test_ledger_policy.py -q -n 0`
Expected: `10 passed`.

- [ ] **Step 5: Commit**

```bash
uv run ruff check src tests && uv run ruff format src tests && uv run ty check src
git add src/neurotic_docx_bench/ledger/policy.py tests/test_ledger_policy.py
git commit -m "feat(report): one ranking policy: eligibility, comparability groups, latest eligible run per tool"
```

---

### Task 9: Bootstrap uncertainty (per-row and paired)

**Files:**
- Create: `src/neurotic_docx_bench/ledger/stats.py`
- Test: `tests/test_ledger_stats.py`

- [ ] **Step 1: Write the failing tests**

```python
"""Percentile bootstrap on per-document scores; paired on shared documents."""

from __future__ import annotations

import pytest

from neurotic_docx_bench.ledger import stats as st


def test_median_ci_contains_the_median_and_is_deterministic() -> None:
    values = [float(v) for v in range(0, 101)]
    lo, hi = st.bootstrap_median_ci(values, reps=500, seed=1)
    assert lo <= 50.0 <= hi
    assert st.bootstrap_median_ci(values, reps=500, seed=1) == (lo, hi)


def test_median_ci_degenerates_for_tiny_samples() -> None:
    assert st.bootstrap_median_ci([1.0, 2.0], reps=100) == (1.0, 2.0)
    assert st.bootstrap_median_ci([], reps=100) is None


def test_paired_diff_on_shared_docs_only() -> None:
    a = {f"d{i}": 60.0 + i for i in range(40)}
    b = {f"d{i}": 50.0 + i for i in range(40)}
    b["only_b"] = 1.0
    d = st.paired_median_diff(a, b, reps=500, seed=7)
    assert d is not None
    assert d.n == 40 and d.median_delta == 10.0
    assert d.ci_low > 0 and d.ci_high >= d.ci_low
    assert (d.wins, d.losses, d.ties) == (40, 0, 0)


def test_paired_diff_identical_tools_straddles_zero() -> None:
    a = {f"d{i}": float(i % 7) for i in range(60)}
    d = st.paired_median_diff(a, dict(a), reps=500, seed=3)
    assert d is not None and d.ci_low <= 0.0 <= d.ci_high and d.ties == 60


def test_paired_diff_requires_min_shared_docs() -> None:
    a = {f"d{i}": 1.0 for i in range(10)}
    assert st.paired_median_diff(a, a, reps=100) is None


def test_tie_when_interval_includes_zero() -> None:
    a = {f"d{i}": float(i % 7) for i in range(60)}
    b = {k: v + 0.01 * (i % 2) for i, (k, v) in enumerate(a.items())}
    assert st.tie_by_paired_bootstrap(a, b, reps=300, seed=2) is True
    far = {k: v + 30.0 for k, v in a.items()}
    assert st.tie_by_paired_bootstrap(a, far, reps=300, seed=2) is False
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_ledger_stats.py -q -n 0`
Expected: `ModuleNotFoundError: No module named 'neurotic_docx_bench.ledger.stats'`.

- [ ] **Step 3: Write the module**

`src/neurotic_docx_bench/ledger/stats.py`:

```python
"""Uncertainty for ranked tables.

Every vendor scores the same documents, so comparisons are paired: the statistic is
the median of per-document deltas on the shared document set, with a percentile
bootstrap interval (B resamples of the delta vector with replacement, fixed seed).
Two adjacent rows tie when that interval includes 0. Per-row intervals are the
percentile bootstrap of the row's own median. Deterministic by construction.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
from pydantic import BaseModel, ConfigDict

DEFAULT_REPS = 2000
DEFAULT_SEED = 42
MIN_PAIRED_DOCS = 20


class PairedDiff(BaseModel):
    model_config = ConfigDict(frozen=True)

    n: int
    median_delta: float
    ci_low: float
    ci_high: float
    wins: int
    losses: int
    ties: int


def bootstrap_median_ci(
    values: Sequence[float], *, reps: int = DEFAULT_REPS, seed: int = DEFAULT_SEED, alpha: float = 0.05,
) -> tuple[float, float] | None:
    arr = np.asarray(list(values), dtype=float)
    if arr.size == 0:
        return None
    if arr.size < 3:
        return (float(arr.min()), float(arr.max()))
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, arr.size, size=(reps, arr.size))
    medians = np.median(arr[idx], axis=1)
    lo, hi = np.quantile(medians, [alpha / 2, 1 - alpha / 2])
    return (round(float(lo), 2), round(float(hi), 2))


def paired_median_diff(
    a: Mapping[str, float], b: Mapping[str, float], *,
    reps: int = DEFAULT_REPS, seed: int = DEFAULT_SEED, alpha: float = 0.05,
) -> PairedDiff | None:
    shared = sorted(set(a) & set(b))
    if len(shared) < MIN_PAIRED_DOCS:
        return None
    deltas = np.asarray([float(a[k]) - float(b[k]) for k in shared], dtype=float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, deltas.size, size=(reps, deltas.size))
    medians = np.median(deltas[idx], axis=1)
    lo, hi = np.quantile(medians, [alpha / 2, 1 - alpha / 2])
    eps = 1e-9
    return PairedDiff(
        n=int(deltas.size),
        median_delta=round(float(np.median(deltas)), 4),
        ci_low=round(float(lo), 4),
        ci_high=round(float(hi), 4),
        wins=int((deltas > eps).sum()),
        losses=int((deltas < -eps).sum()),
        ties=int((np.abs(deltas) <= eps).sum()),
    )


def tie_by_paired_bootstrap(
    a: Mapping[str, float], b: Mapping[str, float], *, reps: int = DEFAULT_REPS, seed: int = DEFAULT_SEED,
) -> bool:
    d = paired_median_diff(a, b, reps=reps, seed=seed)
    if d is None:
        return False
    return d.ci_low <= 0.0 <= d.ci_high
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/test_ledger_stats.py -q -n 0`
Expected: `6 passed`.

- [ ] **Step 5: Commit**

```bash
uv run ruff check src tests && uv run ruff format src tests && uv run ty check src
git add src/neurotic_docx_bench/ledger/stats.py tests/test_ledger_stats.py
git commit -m "feat(report): paired bootstrap intervals and rank ties"
```

---

### Task 10: Markdown tables, the build, and `bench report`

**Files:**
- Create: `src/neurotic_docx_bench/ledger/tables.py`
- Create: `src/neurotic_docx_bench/ledger/build.py`
- Modify: `src/neurotic_docx_bench/cli.py` (new `report` command)
- Modify: `README.md` (add `<!-- VENDORS-START -->` / `<!-- VENDORS-END -->` around the vendor table)
- Test: `tests/test_ledger_tables.py`, `tests/test_ledger_build.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_ledger_tables.py`:

```python
"""Markdown rendering states the policy, the group, and the uncertainty on the table itself."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from neurotic_docx_bench.ledger import policy as pol
from neurotic_docx_bench.ledger import tables as tb
from neurotic_docx_bench.ledger.pins import ToolPin
from neurotic_docx_bench.ledger.registry import load_registry
from neurotic_docx_bench.ledger.rows import ResultRow, SpeedRow

T0 = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)


@pytest.fixture
def registry(tmp_path: Path):
    doc = {"schema_version": 1, "tools": [
        {"id": "a", "vendor": "a", "display": "acme", "role": "generator", "engine": "a", "bench_vendors": ["a"], "speed_tools": ["a"]},
        {"id": "b", "vendor": "b", "display": "jubarte-x", "role": "generator", "engine": "b", "bench_vendors": ["b"], "affiliated": True},
        {"id": "cal", "vendor": "bench", "display": "oracle DOCX (identity)", "role": "calibration", "engine": "pipeline", "bench_vendors": ["cal"]},
        {"id": "na", "vendor": "na", "display": "doxx", "role": "converter", "engine": "na", "not_applicable": ["script_redlines"], "note": "no PDF export"},
    ]}
    p = tmp_path / "reg.yaml"
    p.write_text(yaml.safe_dump(doc))
    return load_registry(p)


def _row(tool, display, median, *, affiliated=False, n=30, pin="1.2.3", docset="d1") -> ResultRow:
    scores = {f"doc{i}": median + (i % 3) - 1 for i in range(n)}
    return ResultRow(
        source="bench", id_run=f"run-{tool}", tool_id=tool, display=display, affiliated=affiliated,
        benchmark="script_redlines", pin=ToolPin.parse(pin), timestamp=T0, corpus_revision="rev",
        docset_id=docset, renderer_id="soffice-26.2.4.2", scorer="pagefair-v2", n_scored=n,
        n_failed_docs=2, n_failure_events=3, itt_n=n + 2, itt_mean=median - 1, itt_median=median,
        mean=median, median=median, exact_100=1, scores=scores, holdout_mode="excluded",
    )


def _table(registry):
    rows = [_row("a", "acme", 80.0), _row("b", "jubarte-x", 90.0, affiliated=True), _row("cal", "oracle DOCX (identity)", 100.0)]
    return pol.select_headline(rows, registry=registry, retractions=[], docsets={"d1": {"n": 32}}, tie_fn=lambda x, y: False)["script_redlines"]


def test_fidelity_table_layout(registry) -> None:
    md = tb.fidelity_table(_table(registry), row_ci={"run-a": (78.0, 82.0), "run-b": (88.5, 91.0)})
    assert md.startswith("### script_redlines")
    assert "Document set `d1` (32 documents)" in md
    assert "renderer `soffice-26.2.4.2`" in md and "scorer `pagefair-v2`" in md
    assert "| 1 | jubarte-x †" in md
    assert "| 2 | acme |" in md
    assert "[88.50, 91.00]" in md
    assert "| 30 | 2 |" in md          # Docs, Failed
    assert "oracle DOCX (identity)" in md and "Calibration" in md
    assert "Not applicable" in md and "doxx" in md and "no PDF export" in md
    assert "author-affiliated" in md


def test_tied_rank_is_marked(registry) -> None:
    rows = [_row("a", "acme", 90.0), _row("b", "jubarte-x", 90.3, affiliated=True)]
    t = pol.select_headline(rows, registry=registry, retractions=[], docsets={"d1": {"n": 32}}, tie_fn=lambda x, y: True)["script_redlines"]
    md = tb.fidelity_table(t, row_ci={})
    assert "| 1 | jubarte-x †" in md and "| 1= | acme |" in md


def test_excluded_rows_listed_with_reasons(registry) -> None:
    rows = [_row("a", "acme", 80.0), _row("b", "jubarte-x", 90.0, n=10)]
    t = pol.select_headline(rows, registry=registry, retractions=[], docsets={"d1": {"n": 32}}, tie_fn=lambda x, y: False)["script_redlines"]
    md = tb.fidelity_table(t, row_ci={})
    assert "Not ranked" in md and "jubarte-x" in md and "incomplete: 12 of 32 documents" in md


def test_empty_table_says_so(registry) -> None:
    t = pol.select_headline([_row("a", "acme", 80.0, n=5)], registry=registry, retractions=[], docsets={"d1": {"n": 32}}, tie_fn=lambda x, y: False)["script_redlines"]
    md = tb.fidelity_table(t, row_ci={})
    assert "No eligible rows" in md and "incomplete: 7 of 32 documents" in md


def test_speed_table_layout(registry) -> None:
    srow = SpeedRow(tool_id="a", display="acme", affiliated=False, kind="large", inproc=True, runtime="rust",
                    pin=ToolPin.parse("x@abcdefabcdef"), timestamp=T0, fixture_count=1000, pair_count=5000, n=5000,
                    failures=3, median_ms=6.2, mean_ms=25.3, p95_ms=110.8, hardware={"cpu": "Apple M3 Max", "cores": 14})
    h = pol.select_speed_headline([srow], registry=registry)
    md = tb.speed_tables(h)
    assert "### speed_redlines" in md
    assert "| 1 | acme | in-process | rust | x@abcdefabcdef | 2026-09-01 | 1000 | 5000 | 6.20 | 25.30 | 110.80 | 5000 | 3 | Apple M3 Max (14 cores) |" in md


def test_history_table_lists_every_row_with_verdicts(registry) -> None:
    rows = [_row("a", "acme", 80.0), _row("a", "acme", 70.0, n=5, pin="1.0.0")]
    md = tb.history_section(rows, registry=registry, retractions=[], docsets={"d1": {"n": 32}})
    assert "## History" in md and "1.0.0" in md and "incomplete: 7 of 32 documents" in md and "eligible" in md


def test_methodology_mentions_weights_and_oracles() -> None:
    md = tb.methodology_section(noise_sigma=1e-14, lo_version="26.2.4.2")
    for needle in ("SSIM", "0.7", "0.3", "intent-to-treat", "LibreOffice", "Word", "paired bootstrap", "author"):
        assert needle in md, needle
```

`tests/test_ledger_build.py`:

```python
"""bench report: every view from the stores, idempotent, refuses unmapped lines."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from neurotic_docx_bench.cli import app
from neurotic_docx_bench.ledger import build as bd

README = "# repo\n\nintro\n\n<!-- VENDORS-START -->\nold\n<!-- VENDORS-END -->\n\ntail\n"


def _line(vendor: str, median: float, ts: str, *, n: int = 25, version: str = "1.0", benchmark: str = "script_redlines") -> dict:
    scores = {f"doc{i}": median for i in range(n)}
    return {
        "id_run": f"run-{vendor}-{ts}", "vendor": vendor, "benchmark": benchmark, "n_docs": n,
        "overall_mean": median, "overall_median": median, "exact_100": 0, "scores": scores, "failures": [],
        "n_failures": 0, "itt_n_docs": n, "itt_mean": median, "itt_median": median,
        "tool_version": version, "timestamp": ts, "corpus_revision": "rev1", "scorer": "pagefair-v2",
        "holdout_mode": "excluded", "docset_id": "dset1", "renderer_id": "soffice-26.2.4.2",
        "environment_config": {"runs": [{"name": vendor, "render": "soffice"}]},
    }


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    (tmp_path / "results").mkdir()
    (tmp_path / "bench.registry.yaml").write_text(yaml.safe_dump({"schema_version": 1, "tools": [
        {"id": "a", "vendor": "a", "display": "acme", "role": "generator", "engine": "a", "run_names": ["a"], "bench_vendors": ["a"], "speed_tools": ["a"], "url": "https://example.com/a"},
        {"id": "b", "vendor": "b", "display": "bravo", "role": "generator", "engine": "b", "run_names": ["b"], "bench_vendors": ["b"], "affiliated": True},
    ]}))
    (tmp_path / "results" / "bench.jsonl").write_text(
        json.dumps(_line("a", 80.0, "2026-09-01T00:00:00+00:00")) + "\n" +
        json.dumps(_line("b", 90.0, "2026-09-02T00:00:00+00:00")) + "\n"
    )
    (tmp_path / "results" / "docsets.json").write_text(json.dumps({"dset1": {"benchmark": "script_redlines", "n": 25}}))
    (tmp_path / "results" / "speed.jsonl").write_text(json.dumps({
        "kind": "speed_redlines", "tool": "a", "runtime": "rust", "run_ts": "2026-09-01T00:00:00Z",
        "fixture_count": 1000, "pair_count": 5000, "n": 5000, "failures": 0, "unit": "ms_per_redline",
        "mean": 20.0, "median": 6.0, "p95": 100.0, "tool_version": "1.0", "hardware": {"cpu": "x", "cores": 8},
    }) + "\n")
    (tmp_path / "README.md").write_text(README)
    (tmp_path / "RESULTS.md").write_text("stale\n")
    return tmp_path


def test_build_produces_all_views(repo: Path) -> None:
    bundle = bd.build(repo, now=datetime(2026, 9, 27, tzinfo=UTC))
    assert "### script_redlines" in bundle.results_md
    assert "| 1 | bravo †" in bundle.results_md and "| 2 | acme |" in bundle.results_md
    assert "### speed_redlines" in bundle.results_md
    assert "## History" in bundle.detailed_md and "## Paired comparisons" in bundle.detailed_md
    assert "| acme |" in bundle.readme_vendor_table and "https://example.com/a" in bundle.readme_vendor_table
    assert "Generated 2026-09-27" in bundle.results_md


def test_write_replaces_readme_block_and_is_idempotent(repo: Path) -> None:
    now = datetime(2026, 9, 27, tzinfo=UTC)
    written = bd.write(repo, bd.build(repo, now=now))
    assert {p.name for p in written} == {"RESULTS.md", "RESULTS_DETAILED.md", "README.md"}
    readme = (repo / "README.md").read_text()
    assert "old" not in readme and readme.startswith("# repo\n\nintro") and readme.endswith("tail\n")
    first = (repo / "RESULTS.md").read_text()
    bd.write(repo, bd.build(repo, now=now))
    assert (repo / "RESULTS.md").read_text() == first


def test_unmapped_line_is_an_error(repo: Path) -> None:
    with (repo / "results" / "bench.jsonl").open("a") as fh:
        fh.write(json.dumps(_line("ghost", 50.0, "2026-09-03T00:00:00+00:00")) + "\n")
    with pytest.raises(ValueError, match="ghost"):
        bd.build(repo)


def test_readme_without_markers_is_an_error(repo: Path) -> None:
    (repo / "README.md").write_text("no markers\n")
    with pytest.raises(ValueError, match="VENDORS-START"):
        bd.write(repo, bd.build(repo))


def test_cli_report_and_check(repo: Path, monkeypatch) -> None:
    monkeypatch.chdir(repo)
    r = CliRunner().invoke(app, ["report"])
    assert r.exit_code == 0, r.output
    assert "RESULTS.md" in r.output
    r = CliRunner().invoke(app, ["report", "--check"])
    assert r.exit_code == 0, r.output
    (repo / "RESULTS.md").write_text("drift\n")
    r = CliRunner().invoke(app, ["report", "--check"])
    assert r.exit_code == 1
    assert "RESULTS.md" in r.output
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_ledger_tables.py tests/test_ledger_build.py -q -n 0`
Expected: `ModuleNotFoundError: No module named 'neurotic_docx_bench.ledger.tables'`.

- [ ] **Step 3: Write `tables.py`**

```python
"""Markdown rendering. Every table states its own policy, group and uncertainty."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime

from neurotic_docx_bench.ledger import policy as pol
from neurotic_docx_bench.ledger import stats as st
from neurotic_docx_bench.ledger.registry import Registry
from neurotic_docx_bench.ledger.rows import ResultRow, SpeedRow
from neurotic_docx_bench.score import ScoreWeights

AFFILIATED_MARK = "†"

TITLES: dict[str, str] = {
    "script_redlines": "script_redlines: redline markup vs Word",
    "accepted_changes": "accepted_changes: accept all changes, match the final document",
    "roundtrip": "roundtrip: self-diff must not invent noise",
    "visual_rendering": "visual_rendering: editor render of the plain DOCX",
    "visual_redlines": "visual_redlines: editor render of the redline DOCX",
    "visual_accepted_changes": "visual_accepted_changes: editor render of the accepted DOCX",
    "docx_to_pdf": "docx_to_pdf: accepted and randomized redline DOCX to PDF vs Word export",
    "docx_to_pdf_no_redline_docs": "docx_to_pdf_no_redline_docs: source DOCX to PDF vs Word export",
    "docxide_metrics": "docxide_metrics: source DOCX to PDF under docxide-pdf's own metrics",
}

ORACLE_NOTES: dict[str, str] = {
    "script_redlines": "Oracle: LibreOffice render of Word's tracked-change DOCX; candidates are rendered by the same LibreOffice build, so 100 means pixel-identical to Word's DOCX as LibreOffice draws it.",
    "accepted_changes": "Oracle: LibreOffice render of Word's accepted DOCX; the candidate is the tool's own redline with every change accepted.",
    "roundtrip": "Oracle: LibreOffice render of the unchanged source; the candidate is the tool's roundtrip output.",
    "visual_rendering": "Oracle: Word's own PDF export of the source; the candidate is a Playwright capture of the vendor editor.",
    "visual_redlines": "Oracle: Word's own PDF export of the redline; the candidate is a Playwright capture of the vendor editor loading Word's DOCX.",
    "visual_accepted_changes": "Oracle: Word's own PDF export of the accepted DOCX; the candidate is a Playwright capture of the vendor editor.",
    "docx_to_pdf": "Oracle: SHA-pinned Word-export PDFs; the candidate is the converter's PDF.",
    "docx_to_pdf_no_redline_docs": "Oracle: SHA-pinned Word-export PDFs of the source; the candidate is the converter's PDF.",
    "docxide_metrics": "Same inputs and oracles as docx_to_pdf_no_redline_docs, scored with docxide-pdf's Jaccard, SSIM and text-boundary metrics at 150 DPI.",
}


def fmt(x: float) -> str:
    return f"{x:.2f}"


def fmt_date(ts: datetime) -> str:
    return ts.strftime("%Y-%m-%d")


def md_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    head = "| " + " | ".join(headers) + " |"
    sep = "| " + " | ".join("---" for _ in headers) + " |"
    body = ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join([head, sep, *body])


def _tool_cell(row: ResultRow) -> str:
    return f"{row.display} {AFFILIATED_MARK}" if row.affiliated else row.display


def _rank_cell(r: pol.RankedRow) -> str:
    return f"{r.rank}=" if r.tied_with_previous else str(r.rank)


def _ci_cell(ci: tuple[float, float] | None) -> str:
    return f"[{fmt(ci[0])}, {fmt(ci[1])}]" if ci else "n/a"


def _hardware_cell(hw: Mapping[str, object] | None) -> str:
    if not hw:
        return "unknown"
    cpu = str(hw.get("cpu") or hw.get("machine") or "unknown")
    cores = hw.get("cores")
    return f"{cpu} ({cores} cores)" if cores else cpu


def fidelity_table(table: pol.HeadlineTable, *, row_ci: Mapping[str, tuple[float, float] | None]) -> str:
    title = TITLES.get(table.benchmark, table.benchmark)
    out: list[str] = [f"### {title}", ""]
    out.append(ORACLE_NOTES.get(table.benchmark, ""))
    if table.group is None or not table.rows:
        out.append("")
        out.append("No eligible rows for this benchmark yet.")
    else:
        g = table.group
        out.append(
            f"Document set `{g.docset}` ({table.expected_n} documents), renderer `{g.renderer}`, "
            f"scorer `{g.scorer}`. One row per tool: its latest eligible run. Sorted by ITT median, "
            "then ITT mean. Failed documents score 0 (intent-to-treat); Mean and Median are over scored "
            "documents only. 95% CI is a percentile bootstrap of the ITT median (2000 resamples, seed 42). "
            "An equal rank (`n=`) means the paired bootstrap interval of the median difference to the row "
            f"above includes 0. {AFFILIATED_MARK} marks an author-affiliated tool; the same rules apply to it.",
        )
        out.append("")
        headers = ["Rank", "Tool", "Pin", "Run", "Docs", "Failed", "ITT Mean", "ITT Median", "95% CI", "Mean", "Median", "Perfect (100)"]
        body = [
            [
                _rank_cell(r), _tool_cell(r.row), r.row.pin.display, fmt_date(r.row.timestamp),
                str(r.row.n_scored), str(r.row.n_failed_docs), fmt(r.row.itt_mean), fmt(r.row.itt_median),
                _ci_cell(row_ci.get(r.row.id_run)), fmt(r.row.mean), fmt(r.row.median), str(r.row.exact_100),
            ]
            for r in table.rows
        ]
        out.append(md_table(headers, body))
    if table.calibration:
        out.append("")
        out.append("Calibration rows (never ranked; the pipeline's own anchors):")
        out.append("")
        out.append(md_table(
            ["Row", "Pin", "Run", "Docs", "Failed", "ITT Mean", "ITT Median", "Perfect (100)"],
            [[c.display, c.pin.display, fmt_date(c.timestamp), str(c.n_scored), str(c.n_failed_docs), fmt(c.itt_mean), fmt(c.itt_median), str(c.exact_100)] for c in table.calibration],
        ))
    if table.excluded:
        out.append("")
        out.append("Not ranked in this group (latest run per tool, with the reason):")
        out.append("")
        for e in table.excluded:
            out.append(f"- {_tool_cell(e.row)} {e.row.pin.display} ({fmt_date(e.row.timestamp)}): {'; '.join(e.verdict.reasons)}")
    if table.not_applicable:
        out.append("")
        out.append("Not applicable: " + "; ".join(f"{t.display} ({t.note})" if t.note else t.display for t in table.not_applicable))
    if table.history_groups:
        out.append("")
        out.append(
            "Other document sets or renderers measured for this benchmark are listed under History in "
            "RESULTS_DETAILED.md: " + ", ".join(f"`{g.docset}`/`{g.renderer}`" for g in table.history_groups),
        )
    return "\n".join(out).rstrip() + "\n"


def _speed_rows(ranked: Sequence[pol.RankedSpeed]) -> list[list[str]]:
    return [
        [
            str(r.rank), (f"{r.row.display} {AFFILIATED_MARK}" if r.row.affiliated else r.row.display),
            "in-process" if r.row.inproc else "cli", r.row.runtime or "unknown", r.row.pin.display, fmt_date(r.row.timestamp),
            str(r.row.fixture_count or "n/a"), str(r.row.pair_count or "n/a"),
            fmt(r.row.median_ms), fmt(r.row.mean_ms), fmt(r.row.p95_ms) if r.row.p95_ms is not None else "n/a",
            str(r.row.n), str(r.row.failures), _hardware_cell(r.row.hardware),
        ]
        for r in ranked
    ]


def speed_tables(h: pol.SpeedHeadline) -> str:
    out = ["### speed_redlines: generation time in ms per redline", ""]
    out.append(
        "Lower is faster. One row per tool and mode: its latest pinned run. Large-N rows rank only at the "
        f"canonical {pol.CANONICAL_SPEED_FIXTURES} fixtures; failures are excluded from the timing and counted "
        "in the Failures column, so read the two together. In-process rows skip process spawn; cli rows include it. "
        "The machine is part of the row because the number means nothing without it.",
    )
    headers = ["Rank", "Tool", "Mode", "Runtime", "Pin", "Run", "Fixtures", "Pairs", "Median ms", "Mean ms", "p95 ms", "n", "Failures", "Machine"]
    out.append("")
    out.append("Large-N:")
    out.append("")
    out.append(md_table(headers, _speed_rows(h.large)) if h.large else "No pinned large-N speed rows yet.")
    out.append("")
    out.append("Microbench (30 to 40 pairs, 3 repetitions):")
    out.append("")
    out.append(md_table(headers, _speed_rows(h.micro)) if h.micro else "No pinned microbench rows yet.")
    if h.excluded:
        out.append("")
        out.append("Not ranked (latest row per tool and mode):")
        out.append("")
        for e in h.excluded:
            out.append(f"- {e.row.display} ({'in-process' if e.row.inproc else 'cli'}, {e.row.kind}, {fmt_date(e.row.timestamp)}): {'; '.join(e.verdict.reasons)}")
    return "\n".join(out).rstrip() + "\n"


def history_section(
    rows: Sequence[ResultRow], *, registry: Registry, retractions: Sequence[pol.Retraction],
    docsets: Mapping[str, Mapping[str, object]],
) -> str:
    out = ["## History", "", "Every row in the store, grouped by benchmark and comparability group, with the eligibility verdict the headline applied. Rows in different groups are different measurements.", ""]
    by_bench: dict[str, list[ResultRow]] = {}
    for r in rows:
        by_bench.setdefault(r.benchmark, []).append(r)
    for benchmark, bench_rows in sorted(by_bench.items()):
        out.append(f"### {benchmark}")
        groups: dict[pol.GroupKey, list[ResultRow]] = {}
        for r in bench_rows:
            groups.setdefault(pol.group_key(r), []).append(r)
        for g, members in sorted(groups.items(), key=lambda kv: max(m.timestamp for m in kv[1]), reverse=True):
            exp = pol.expected_n(members, docsets)
            out.append("")
            out.append(f"Group: document set `{g.docset}`, renderer `{g.renderer}`, scorer `{g.scorer}`, expected {exp} documents.")
            out.append("")
            body = []
            for r in sorted(members, key=lambda m: (m.display, m.timestamp)):
                v = pol.eligibility(r, expected=exp, retractions=retractions, registry=registry)
                body.append([
                    _tool_cell(r), r.pin.display, fmt_date(r.timestamp), str(r.n_scored), str(r.n_failed_docs),
                    str(r.itt_n), fmt(r.itt_median) + ("~" if r.itt_approx else ""), fmt(r.itt_mean) + ("~" if r.itt_approx else ""),
                    "eligible" if v.eligible else "; ".join(v.reasons), r.id_run,
                ])
            out.append(md_table(["Tool", "Pin", "Run", "Docs", "Failed", "ITT n", "ITT Median", "ITT Mean", "Verdict", "id_run"], body))
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def paired_section(tables: Mapping[str, pol.HeadlineTable]) -> str:
    out = ["## Paired comparisons", "", "Per-document deltas on the documents both tools scored, inside the headline group. `win/loss/tie` counts documents where the first tool scores higher, lower, or equal. The interval is a percentile bootstrap of the median delta (2000 resamples, seed 42); it includes 0 when the two tools are not distinguishable on this corpus.", ""]
    any_rows = False
    for benchmark, t in sorted(tables.items()):
        ranked = [r.row for r in t.rows if r.row.scores]
        if len(ranked) < 2:
            continue
        body = []
        for i, a in enumerate(ranked):
            for b in ranked[i + 1:]:
                d = st.paired_median_diff(a.scores, b.scores)
                if d is None:
                    continue
                body.append([_tool_cell(a), _tool_cell(b), str(d.n), f"{d.wins}/{d.losses}/{d.ties}", f"{d.median_delta:+.2f}", f"[{d.ci_low:+.2f}, {d.ci_high:+.2f}]"])
        if body:
            any_rows = True
            out.append(f"### {benchmark}")
            out.append("")
            out.append(md_table(["Tool A", "Tool B", "Docs", "win/loss/tie", "Median delta", "95% CI"], body))
            out.append("")
    if not any_rows:
        out.append("No benchmark has two ranked rows with per-document scores yet.")
    return "\n".join(out).rstrip() + "\n"


def methodology_section(*, noise_sigma: float | None, lo_version: str | None) -> str:
    w = ScoreWeights()
    noise = (
        f"Re-rendering the same DOCX with the same LibreOffice build ({lo_version}) gives a score standard deviation of {noise_sigma:.1e} (results/noise_floor.json)."
        if noise_sigma is not None and lo_version else "Noise floor not recorded; run `bench noise-floor`."
    )
    return "\n".join([
        "## Methodology",
        "",
        "Scoring. Each page pair is rasterized at 144 DPI and scored 0 to 100 as a weighted sum lifted verbatim from superdoc-visual-benchmarks: "
        f"SSIM full {w.ssim_full:g}, SSIM small {w.ssim_small:g}, ink F1 {w.ink_f1:g}, edge IoU {w.edge_iou:g}, colour {w.color_sim:g}, blob {w.blob_sim:g}. "
        "A document scores 0.7 times its page mean plus 0.3 times its worst page. For script_redlines, accepted_changes and roundtrip the ranked score is `pagefair-v2`: pages present on only one side enter at 0, ink-weighted. The visual_* benchmarks rank on the raw score because cross-engine repagination is expected there. SuperDoc, whose benchmark the formula comes from, is itself a ranked vendor; the parity tests keep the formula byte-identical to upstream.",
        "",
        "Oracles. The redline benchmarks compare LibreOffice's render of the candidate DOCX to LibreOffice's render of Word's DOCX. The docx_to_pdf and visual_* benchmarks compare to Word's own PDF export. A tool can score 100 on the first family and well below 100 on the second, because the second also measures the renderer's distance from Word. "
        + noise,
        "",
        "Denominators. Every benchmark has a fixed document set (`results/docsets.json`); a document with no candidate output enters at 0 (intent-to-treat). Documents named by a non-fatal stage warning but scored keep their score and are not counted as failed.",
        "",
        "Selection. One row per tool: its latest eligible run in the current comparability group. There is no best-of-N over runs and no best pin. A run that is wrong for a reason unrelated to the tool is retracted with a stated reason in `results/retractions.jsonl` and listed as such.",
        "",
        "Uncertainty. Per-row intervals are a percentile bootstrap of the ITT median. Adjacent rows tie when the paired bootstrap interval of their median difference includes 0.",
        "",
        "Disclosure. The benchmark is maintained by the author of the Jubarte tools. Those rows are marked and follow the same rules as every other row.",
        "",
    ])


def vendor_table(registry: Registry) -> str:
    rows = []
    for t in registry.tools:
        if t.status != "active" or t.role == "calibration":
            continue
        rows.append([
            f"[{t.display}]({t.url})" if t.url else t.display,
            t.role,
            t.engine,
            "yes" if t.affiliated else "",
            t.note or "",
        ])
    return md_table(["Tool", "Role", "Engine", "Author-affiliated", "Note"], rows) + "\n"
```

- [ ] **Step 4: Write `build.py`**

```python
"""Build every published view from the stores. The only writer of RESULTS.md,
RESULTS_DETAILED.md and the README vendor block."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from neurotic_docx_bench.ledger import policy as pol
from neurotic_docx_bench.ledger import rows as rws
from neurotic_docx_bench.ledger import stats as st
from neurotic_docx_bench.ledger import tables as tb
from neurotic_docx_bench.ledger.registry import DEFAULT_REGISTRY_PATH, load_registry

VENDORS_START = "<!-- VENDORS-START -->"
VENDORS_END = "<!-- VENDORS-END -->"
GENERATED_NOTE = "<!-- generated by `uv run bench report`; do not edit by hand -->"


class Bundle(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    results_md: str
    detailed_md: str
    readme_vendor_table: str


def _noise_floor(root: Path) -> tuple[float | None, str | None]:
    p = root / "results" / "noise_floor.json"
    if not p.is_file():
        return None, None
    try:
        data = json.loads(p.read_text())
        return float(data.get("sigma")), (str(data["lo_version"]) if data.get("lo_version") else None)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None, None


def build(root: Path, *, now: datetime | None = None) -> Bundle:
    root = Path(root)
    now = now or datetime.now(UTC)
    registry = load_registry(root / DEFAULT_REGISTRY_PATH)
    rows, unmapped = rws.load_bench_rows(root / "results" / "bench.jsonl", registry)
    if unmapped:
        names = sorted({f"{u['vendor']}/{u['run_name']}" for u in unmapped})
        raise ValueError(f"results/bench.jsonl has lines the registry cannot map: {names}")
    retractions = pol.load_retractions(root / pol.DEFAULT_RETRACTIONS_PATH)
    docsets = pol.load_docsets_json(root / "results" / "docsets.json")
    tie_fn = lambda a, b: st.tie_by_paired_bootstrap(a.scores, b.scores)  # noqa: E731
    tables = pol.select_headline(rows, registry=registry, retractions=retractions, docsets=docsets, tie_fn=tie_fn)
    speed_rows, _ = rws.load_speed_rows(root / "results" / "speed.jsonl", root / "results" / "redline_speed_bench", registry)
    speed = pol.select_speed_headline(speed_rows, registry=registry)
    row_ci: dict[str, tuple[float, float] | None] = {}
    for t in tables.values():
        for r in t.rows:
            row_ci[r.row.id_run] = st.bootstrap_median_ci(list(r.row.scores.values())) if r.row.scores else None

    stamp = f"Generated {now.strftime('%Y-%m-%d %H:%M UTC')} from `results/bench.jsonl`, `results/speed.jsonl`, `results/redline_speed_bench/**/summary.json`."
    ordered = [b for b in tb.TITLES if b in tables]
    results_parts = [GENERATED_NOTE, "# Benchmark results", "", stamp, "", "Compare rows only within one table. Full history, paired comparisons and methodology: [RESULTS_DETAILED.md](RESULTS_DETAILED.md).", ""]
    for b in ordered:
        results_parts.append(tb.fidelity_table(tables[b], row_ci=row_ci))
    results_parts.append(tb.speed_tables(speed))
    sigma, lo = _noise_floor(root)
    detailed_parts = [GENERATED_NOTE, "# Benchmark results, detailed", "", stamp, ""]
    for b in ordered:
        detailed_parts.append(tb.fidelity_table(tables[b], row_ci=row_ci))
    detailed_parts.append(tb.speed_tables(speed))
    detailed_parts.append(tb.paired_section(tables))
    detailed_parts.append(tb.history_section(rows, registry=registry, retractions=retractions, docsets=docsets))
    detailed_parts.append(tb.methodology_section(noise_sigma=sigma, lo_version=lo))
    return Bundle(
        results_md="\n".join(results_parts).rstrip() + "\n",
        detailed_md="\n".join(detailed_parts).rstrip() + "\n",
        readme_vendor_table=tb.vendor_table(registry),
    )


def _replace_block(text: str, start: str, end: str, body: str) -> str:
    i, j = text.find(start), text.find(end)
    if i == -1 or j == -1 or j < i:
        raise ValueError(f"README.md must contain {start} and {end} in that order")
    return text[: i + len(start)] + "\n" + body.rstrip() + "\n" + text[j:]


def render_files(root: Path, bundle: Bundle) -> dict[Path, str]:
    root = Path(root)
    readme = (root / "README.md").read_text(encoding="utf-8")
    return {
        root / "RESULTS.md": bundle.results_md,
        root / "RESULTS_DETAILED.md": bundle.detailed_md,
        root / "README.md": _replace_block(readme, VENDORS_START, VENDORS_END, bundle.readme_vendor_table),
    }


def write(root: Path, bundle: Bundle) -> list[Path]:
    written: list[Path] = []
    for path, text in render_files(root, bundle).items():
        path.write_text(text, encoding="utf-8")
        written.append(path)
    return written


def changed_files(root: Path, bundle: Bundle) -> list[Path]:
    out: list[Path] = []
    for path, text in render_files(root, bundle).items():
        current = path.read_text(encoding="utf-8") if path.is_file() else ""
        if current != text:
            out.append(path)
    return out
```

Note on determinism for `--check`: the generated stamp carries the build time, so `changed_files` must compare with the stamp line removed. Implement it as: strip lines starting with `Generated ` from both sides before comparing. Add that to `changed_files`:

```python
def _without_stamp(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if not line.startswith("Generated "))
```

and compare `_without_stamp(current) != _without_stamp(text)`.

- [ ] **Step 5: Add the CLI command**

In `cli.py` after `docset_cmd`:

```python
@app.command(name="report")
def report_cmd(
    root: Path = typer.Option(Path("."), "--root", help="repository root"),
    check: bool = typer.Option(False, "--check", help="exit 1 when the published views are stale"),
) -> None:
    """Regenerate RESULTS.md, RESULTS_DETAILED.md and the README vendor table from the stores."""
    from neurotic_docx_bench.ledger import build as ledger_build

    bundle = ledger_build.build(root)
    if check:
        stale = ledger_build.changed_files(root, bundle)
        for p in stale:
            console.print(f"stale: {p}")
        if stale:
            raise typer.Exit(code=1)
        console.print("published views are current")
        return
    for p in ledger_build.write(root, bundle):
        console.print(f"wrote {p}")
```

- [ ] **Step 6: Add the README markers**

In `README.md`, wrap the existing vendor table (the block starting `| Vendor | What runs | Pin | Role |` through the `docxide-pdf` row) with `<!-- VENDORS-START -->` on the line before and `<!-- VENDORS-END -->` on the line after. The generator replaces what is between the markers on the first `bench report`.

- [ ] **Step 7: Run the tests**

Run: `uv run pytest tests/test_ledger_tables.py tests/test_ledger_build.py -q -n 0`
Expected: `13 passed`.

- [ ] **Step 8: Generate the real views once, read them, commit**

```bash
uv run bench report
git diff --stat
```

Expected: `RESULTS.md`, `RESULTS_DETAILED.md`, `README.md` changed. Read `RESULTS.md` end to end. Check these facts against the step-3 findings before committing: script_redlines headline has one row per tool; jubarte-rust shows the Sep 26 run (75.83 median) not the Aug 13 one; docxodus shows 9.8.0 once; every row's `Docs + Failed` equals the group's document count; "Not ranked" lists the legacy and incomplete rows with reasons; the speed headline is empty or lists only pinned rows.

```bash
uv run ruff check src tests && uv run ruff format src tests && uv run ty check src
git add src/neurotic_docx_bench/ledger/tables.py src/neurotic_docx_bench/ledger/build.py src/neurotic_docx_bench/cli.py README.md RESULTS.md RESULTS_DETAILED.md tests/test_ledger_tables.py tests/test_ledger_build.py
git commit -m "feat(report): bench report renders every published view from one policy"
git push -u origin consolidate/04-report
```

Open PR 4: "report: one generator, one policy, intervals".

---

## PR 5: converter tracks join the store

```bash
git checkout -b consolidate/05-converters consolidate/04-report
```

### Task 11: `results/converters.jsonl` as the converter store; `--update-readme` removed

**Files:**
- Create: `src/neurotic_docx_bench/ledger/converters.py`
- Modify: `src/neurotic_docx_bench/ledger/rows.py` (`extra` field, `row_from_converter_line`, `load_converter_rows`)
- Modify: `src/neurotic_docx_bench/ledger/build.py` (include converter rows)
- Modify: `src/neurotic_docx_bench/ledger/tables.py` (extra-metric columns)
- Modify: `src/neurotic_docx_bench/cli.py:566-705` (append to the store; drop `--update-readme`; new `ingest-converter-reports`)
- Modify: `src/neurotic_docx_bench/docx_to_pdf.py:774-789`, `src/neurotic_docx_bench/docxide_metrics.py:319-332` (delete the README writers)
- Test: `tests/test_ledger_converters.py`; adjust `tests/test_docx_to_pdf.py`, `tests/test_docx_to_pdf_no_redline_docs.py`, `tests/test_docxide_metrics_parity.py` where they call the deleted writers (assert the store append instead)

- [ ] **Step 1: Write the failing tests**

`tests/test_ledger_converters.py`:

```python
"""Converter reports become store lines; the table is built from the store, never from the last run."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from neurotic_docx_bench.ledger import converters as cv
from neurotic_docx_bench.ledger import rows as rws
from neurotic_docx_bench.ledger.registry import load_registry


def _report(track: str = "docx_to_pdf") -> dict:
    return {
        "generated_at": "2026-08-16T19:50:57+00:00", "n": 3, "oracle": "microsoft_word", "track": track,
        "stems": ["s1", "s2", "s3"],
        "tools": {
            "jubarte": {"version": "jubarte 0.7.0", "itt_n": 3, "n_scored": 3, "failures": 0, "mean": 60.0, "median": 62.0,
                        "perfects": 0, "per_doc": {"s1": {"score": 60.0}, "s2": {"score": 62.0}, "s3": {"score": 58.0}}},
            "doxx": {"version": "doxx 0.1.4", "itt_n": 3, "n_scored": 0, "failures": 3, "mean": 0.0, "median": 0.0,
                     "perfects": 0, "per_doc": {"s1": {"error": "x"}, "s2": {"error": "x"}, "s3": {"error": "x"}}},
        },
    }


def _docxide_report() -> dict:
    return {
        "generated_at": "2026-09-05T07:30:17+00:00", "n": 2, "oracle": "microsoft_word", "track": "docxide_metrics", "dpi": 150,
        "stems": ["s1", "s2"],
        "tools": {"jubarte": {
            "version": "jubarte 0.8.0", "itt_n": 2, "n_scored": 2, "failures": 0,
            "metrics": {"jaccard": {"mean": 53.1, "median": 43.5}, "ssim": {"mean": 72.8, "median": 89.0}, "text_boundary": {"mean": 87.6, "median": 100.0}},
            "per_doc": {"s1": {"jaccard": 40.0, "ssim": 80.0, "text_boundary": 100.0}, "s2": {"jaccard": 47.0, "ssim": 98.0, "text_boundary": 100.0}},
        }},
    }


def test_lines_from_docx_to_pdf_report() -> None:
    lines = cv.lines_from_report(_report(), hardware={"cpu": "x"}, report_path="results/r.json")
    assert [(l["tool"], l["lens"], l["itt_n"], l["n_scored"], l["failures"]) for l in lines] == [
        ("jubarte", "pixel", 3, 3, 0), ("doxx", "pixel", 3, 0, 3),
    ]
    j = lines[0]
    assert j["scores"] == {"s1": 60.0, "s2": 62.0, "s3": 58.0}
    assert j["docset_id"] == cv.stems_docset_id(["s3", "s1", "s2"])
    assert j["timestamp"] == "2026-08-16T19:50:57+00:00" and j["hardware"] == {"cpu": "x"}
    assert j["id_run"] and j["report_path"] == "results/r.json"
    assert lines[1]["scores"] == {}


def test_lines_from_docxide_report_rank_on_jaccard_and_carry_extras() -> None:
    (line,) = cv.lines_from_report(_docxide_report(), hardware=None, report_path="")
    assert line["lens"] == "jaccard" and line["scorer"] == "docxide-150dpi"
    assert line["scores"] == {"s1": 40.0, "s2": 47.0}
    assert line["extra"] == {"ssim": {"mean": 72.8, "median": 89.0}, "text_boundary": {"mean": 87.6, "median": 100.0}}


def test_append_report_writes_jsonl(tmp_path: Path) -> None:
    p = tmp_path / "converters.jsonl"
    cv.append_report(p, _report(), hardware=None, report_path="r.json")
    cv.append_report(p, _docxide_report(), hardware=None, report_path="d.json")
    assert len(p.read_text().splitlines()) == 3


@pytest.fixture
def registry(tmp_path: Path):
    doc = {"schema_version": 1, "tools": [
        {"id": "jubarte-pdf", "vendor": "jubarte", "display": "jubarte", "role": "converter", "engine": "jubarte-redlines", "affiliated": True, "converter_tools": ["jubarte"]},
        {"id": "doxx", "vendor": "doxx", "display": "doxx", "role": "converter", "engine": "doxx", "converter_tools": ["doxx"], "not_applicable": ["docx_to_pdf"]},
    ]}
    p = tmp_path / "reg.yaml"
    p.write_text(yaml.safe_dump(doc))
    return load_registry(p)


def test_converter_rows_load_with_tool_ids(tmp_path: Path, registry) -> None:
    p = tmp_path / "converters.jsonl"
    cv.append_report(p, _report(), hardware=None, report_path="r.json")
    rows, unmapped = rws.load_converter_rows(p, registry)
    assert unmapped == []
    assert [(r.tool_id, r.benchmark, r.itt_n, r.n_failed_docs, r.provenance) for r in rows] == [
        ("jubarte-pdf", "docx_to_pdf", 3, 0, "stamped"), ("doxx", "docx_to_pdf", 3, 3, "stamped"),
    ]
    assert rows[0].renderer_id == "oracle:microsoft_word" and rows[0].docset_id
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_ledger_converters.py -q -n 0`
Expected: `ModuleNotFoundError: No module named 'neurotic_docx_bench.ledger.converters'`.

- [ ] **Step 3: Write `converters.py`**

```python
"""Converter reports (docx_to_pdf, docx_to_pdf_no_redline_docs, docxide_metrics) become
append-only store lines, one per (report, tool), so the tables come from the store and
not from whichever JSON the last run wrote."""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Iterable, Mapping
from pathlib import Path

DEFAULT_CONVERTERS_PATH = Path("results/converters.jsonl")
DOCXIDE_TRACK = "docxide_metrics"
DOCXIDE_PRIMARY = "jaccard"
DOCXIDE_SCORER = "docxide-150dpi"


def stems_docset_id(stems: Iterable[str]) -> str:
    return hashlib.sha256("\n".join(sorted(set(stems))).encode("utf-8")).hexdigest()[:12]


def _pixel_scores(per_doc: Mapping[str, object]) -> dict[str, float]:
    out: dict[str, float] = {}
    for stem, entry in per_doc.items():
        if isinstance(entry, Mapping) and isinstance(entry.get("score"), (int, float)):
            out[str(stem)] = float(entry["score"])
    return out


def _lens_scores(per_doc: Mapping[str, object], lens: str) -> dict[str, float]:
    return {
        str(stem): float(entry[lens])
        for stem, entry in per_doc.items()
        if isinstance(entry, Mapping) and isinstance(entry.get(lens), (int, float))
    }


def lines_from_report(report: Mapping[str, object], *, hardware: Mapping[str, object] | None, report_path: str) -> list[dict]:
    track = str(report.get("track") or "")
    stems = [str(s) for s in (report.get("stems") or [])]
    docset = stems_docset_id(stems) if stems else None
    ts = str(report.get("generated_at") or "")
    lines: list[dict] = []
    for tool, data in (report.get("tools") or {}).items():
        if not isinstance(data, Mapping):
            continue
        per_doc = data.get("per_doc") if isinstance(data.get("per_doc"), Mapping) else {}
        if track == DOCXIDE_TRACK:
            metrics = data.get("metrics") if isinstance(data.get("metrics"), Mapping) else {}
            primary = metrics.get(DOCXIDE_PRIMARY) if isinstance(metrics.get(DOCXIDE_PRIMARY), Mapping) else {}
            lens, scorer = DOCXIDE_PRIMARY, DOCXIDE_SCORER
            scores = _lens_scores(per_doc, DOCXIDE_PRIMARY)
            mean, median = float(primary.get("mean", 0.0)), float(primary.get("median", 0.0))
            extra = {k: {"mean": float(v.get("mean", 0.0)), "median": float(v.get("median", 0.0))}
                     for k, v in metrics.items() if k != DOCXIDE_PRIMARY and isinstance(v, Mapping)}
        else:
            lens, scorer = "pixel", "v1"
            scores = _pixel_scores(per_doc)
            mean, median = float(data.get("mean", 0.0)), float(data.get("median", 0.0))
            extra = {}
        lines.append({
            "source": "converter",
            "id_run": str(uuid.uuid7()),
            "track": track,
            "tool": str(tool),
            "version": data.get("version"),
            "timestamp": ts,
            "oracle": str(report.get("oracle") or ""),
            "dpi": report.get("dpi"),
            "docset_id": docset,
            "lens": lens,
            "scorer": scorer,
            "itt_n": int(data.get("itt_n") or 0),
            "n_scored": int(data.get("n_scored") or len(scores)),
            "failures": int(data.get("failures") or 0),
            "mean": mean,
            "median": median,
            "perfects": int(data.get("perfects") or 0),
            "scores": scores,
            "extra": extra,
            "hardware": dict(hardware) if hardware else None,
            "report_path": report_path,
        })
    return lines


def append_report(path: Path, report: Mapping[str, object], *, hardware: Mapping[str, object] | None, report_path: str) -> int:
    lines = lines_from_report(report, hardware=hardware, report_path=report_path)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("a", encoding="utf-8") as fh:
        for line in lines:
            fh.write(json.dumps(line) + "\n")
    return len(lines)
```

- [ ] **Step 4: Extend `rows.py`**

Add `extra: dict[str, dict[str, float]] = {}` to `ResultRow`, then:

```python
def row_from_converter_line(data: dict, registry: Registry) -> ResultRow | None:
    tool = str(data.get("tool") or "")
    entry = registry.resolve_converter(tool)
    track = str(data.get("track") or "")
    if entry is None or not track:
        return None
    scores = {str(k): _num(v) for k, v in (data.get("scores") or {}).items()}
    itt_n = int(_num(data.get("itt_n")))
    n_scored = int(_num(data.get("n_scored")))
    n_failed = max(itt_n - n_scored, 0)
    return ResultRow(
        source="converter",
        id_run=str(data.get("id_run") or ""),
        tool_id=entry.id,
        display=entry.display,
        affiliated=entry.affiliated,
        benchmark=track,
        lens=str(data.get("lens") or "pixel"),
        pin=ToolPin.parse(data.get("version")),
        timestamp=_timestamp(data),
        corpus_revision=str(data.get("docset_id") or "") or None,
        docset_id=str(data.get("docset_id") or "") or None,
        renderer_id=f"oracle:{data.get('oracle') or 'unknown'}",
        scorer=str(data.get("scorer") or "v1"),
        n_scored=n_scored,
        n_failed_docs=n_failed,
        n_failure_events=int(_num(data.get("failures"))),
        itt_n=itt_n,
        itt_mean=_num(data.get("mean")),
        itt_median=_num(data.get("median")),
        itt_approx=False,
        mean=_num(data.get("mean")),
        median=_num(data.get("median")),
        exact_100=int(_num(data.get("perfects"))),
        scores=scores,
        hardware=data.get("hardware") if isinstance(data.get("hardware"), dict) else None,
        extra={str(k): {str(m): _num(x) for m, x in v.items()} for k, v in (data.get("extra") or {}).items() if isinstance(v, dict)},
    )


def load_converter_rows(path: Path, registry: Registry) -> tuple[list[ResultRow], list[dict]]:
    rows: list[ResultRow] = []
    unmapped: list[dict] = []
    if not Path(path).is_file():
        return rows, unmapped
    with Path(path).open(encoding="utf-8") as fh:
        for raw in fh:
            if not raw.strip():
                continue
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            row = row_from_converter_line(data, registry)
            if row is None:
                unmapped.append({"tool": data.get("tool"), "track": data.get("track"), "id_run": data.get("id_run")})
                continue
            rows.append(row)
    return rows, unmapped
```

Converter rows count as stamped because `corpus_revision` is set to the stems hash and scores are present when the converter produced output. A converter with zero scored documents (doxx) has empty `scores`; `provenance` would read "legacy". Change the `provenance` property so a converter row is stamped when `docset_id` is set: `if self.docset_id and (self.scores or self.n_scored == 0) and not self.itt_approx: return "stamped"` and keep the bench rule for bench rows.

- [ ] **Step 5: Wire the build and the tables**

In `build.py::build`, after loading bench rows:

```python
    conv_rows, conv_unmapped = rws.load_converter_rows(root / "results" / "converters.jsonl", registry)
    if conv_unmapped:
        raise ValueError(f"results/converters.jsonl has tools the registry cannot map: {sorted({u['tool'] for u in conv_unmapped})}")
    rows = rows + conv_rows
```

In `tables.fidelity_table`, when any ranked row has `extra`, append one column per extra metric named `f"{metric} median"` with `fmt(row.extra[metric]['median'])` (or `n/a`), so the docxide table keeps SSIM and text-boundary next to Jaccard.

- [ ] **Step 6: Write side and CLI**

In `cli.py::docx_to_pdf_eval` and `docxide_metrics_eval`: delete the `update_readme` option and its branch; after the report JSON is written, add:

```python
    from neurotic_docx_bench.ledger import converters as conv
    n = conv.append_report(conv.DEFAULT_CONVERTERS_PATH, report, hardware=hardware.hardware_info(), report_path=str(json_out))
    console.print(f"appended {n} line(s) to {conv.DEFAULT_CONVERTERS_PATH}")
```

Delete `docx_to_pdf.update_readme_docx_to_pdf` and `render_docx_to_pdf_table` (grep for callers first: `grep -rn "update_readme\|render_docx_to_pdf_table" src tests scripts`), and `docxide_metrics.update_readme`. Add the backfill command:

```python
@app.command(name="ingest-converter-reports")
def ingest_converter_reports(
    reports: list[Path] = typer.Argument(..., help="report JSON files written by docx-to-pdf / docxide-metrics"),
    store: Path = typer.Option(Path("results/converters.jsonl"), "--store"),
) -> None:
    """Backfill results/converters.jsonl from existing report JSON files (one line per tool)."""
    from neurotic_docx_bench.ledger import converters as conv

    total = 0
    for p in reports:
        report = json.loads(Path(p).read_text(encoding="utf-8"))
        total += conv.append_report(store, report, hardware=None, report_path=str(p))
    console.print(f"appended {total} line(s) to {store}")
```

Rewrite the tests that exercised the deleted writers: where a test asserted a README/RESULTS block was rewritten, assert instead that `results/converters.jsonl` (in the test's tmp cwd) gained one line per tool, using `conv.lines_from_report` on the same report. Keep every other assertion.

- [ ] **Step 7: Run tests, backfill, regenerate, commit**

Run: `uv run pytest tests/test_ledger_converters.py tests/test_docx_to_pdf.py tests/test_docx_to_pdf_no_redline_docs.py tests/test_docxide_metrics_parity.py tests/test_ledger_build.py tests/test_cli.py -q -n 0`
Expected: all pass.

```bash
uv run bench ingest-converter-reports results/docx_to_pdf_500.json results/docx_to_pdf_no_redline.json results/docxide_metrics.json
uv run bench report
git add -A src tests results/converters.jsonl RESULTS.md RESULTS_DETAILED.md README.md
git commit -m "feat(converters): converter reports are store lines; tables come from the store"
git push -u origin consolidate/05-converters
```

Expected `RESULTS.md` after this: three converter tables rendered by the same `fidelity_table`, doxx under "Not applicable", pdfitdown's row present with its engine visible in the README vendor table; docxide_metrics lists only jubarte and docxide-pdf until Task 15 runs the other converters.

Open PR 5: "converters: one store for the converter tracks".

---

## PR 6: archive, retractions, and retiring the old generators

```bash
git checkout -b consolidate/06-archive consolidate/05-converters
```

### Task 12: `bench archive` and `bench retract`

**Files:**
- Create: `src/neurotic_docx_bench/ledger/archive.py`
- Modify: `src/neurotic_docx_bench/ledger/rows.py` (`archived` field, `load_bench_rows(..., archived=True)`)
- Modify: `src/neurotic_docx_bench/ledger/policy.py` (reason `archived`)
- Modify: `src/neurotic_docx_bench/ledger/build.py` (history includes `results/archive/*.jsonl`)
- Modify: `src/neurotic_docx_bench/cli.py` (commands)
- Test: `tests/test_ledger_archive.py`

- [ ] **Step 1: Write the failing tests**

```python
"""Archiving moves rows out of the ranked store without losing them; retractions are stated."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import yaml
from typer.testing import CliRunner

from neurotic_docx_bench.cli import app
from neurotic_docx_bench.ledger import archive as ar
from neurotic_docx_bench.ledger import policy as pol
from neurotic_docx_bench.ledger.registry import load_registry


def _line(vendor: str, ts: str, *, crev: str | None = "rev1", scores: bool = True, holdout: str | None = "excluded", id_run: str | None = None) -> dict:
    return {
        "id_run": id_run or f"run-{vendor}-{ts}", "vendor": vendor, "benchmark": "script_redlines", "n_docs": 2,
        "overall_mean": 50.0, "overall_median": 50.0, "exact_100": 0, "scores": {"a": 50.0, "b": 50.0} if scores else {},
        "failures": [], "tool_version": "1.0", "timestamp": ts, "corpus_revision": crev, "holdout_mode": holdout,
        "environment_config": {"runs": [{"name": vendor, "render": "soffice"}]},
    }


def _registry(tmp_path: Path):
    p = tmp_path / "bench.registry.yaml"
    p.write_text(yaml.safe_dump({"schema_version": 1, "tools": [
        {"id": "a", "vendor": "a", "display": "a", "role": "generator", "engine": "a", "run_names": ["a"], "bench_vendors": ["a"]},
    ]}))
    return load_registry(p)


def test_split_store_archives_legacy_holdout_and_retracted(tmp_path: Path) -> None:
    store = tmp_path / "results" / "bench.jsonl"
    store.parent.mkdir()
    lines = [
        _line("a", "2026-07-01T00:00:00+00:00", crev=None),                       # legacy
        _line("a", "2026-08-01T00:00:00+00:00", holdout="only"),                   # holdout-only
        _line("a", "2026-08-02T00:00:00+00:00", id_run="bad"),                     # retracted
        _line("a", "2026-08-03T00:00:00+00:00"),                                   # kept
    ]
    store.write_text("".join(json.dumps(l) + "\n" for l in lines))
    ret = [pol.Retraction(id_run="bad", reason="broken harness", retracted_at=datetime(2026, 8, 4, tzinfo=UTC), by="me")]
    result = ar.split_store(store, tmp_path / "results" / "archive", registry=_registry(tmp_path), retractions=ret,
                            now=datetime(2026, 9, 27, tzinfo=UTC), dry_run=False)
    assert result.kept == 1 and result.archived == 3
    assert len(store.read_text().splitlines()) == 1
    archived = (tmp_path / "results" / "archive" / "bench-2026-09-27.jsonl").read_text().splitlines()
    assert len(archived) == 3
    manifest = (tmp_path / "results" / "archive" / "MANIFEST.md").read_text()
    assert "legacy provenance" in manifest and "holdout-only run" in manifest and "retracted: broken harness" in manifest
    assert json.loads(archived[0])["id_run"] == "run-a-2026-07-01T00:00:00+00:00"


def test_split_store_dry_run_changes_nothing(tmp_path: Path) -> None:
    store = tmp_path / "results" / "bench.jsonl"
    store.parent.mkdir()
    store.write_text(json.dumps(_line("a", "2026-07-01T00:00:00+00:00", crev=None)) + "\n")
    before = store.read_text()
    result = ar.split_store(store, tmp_path / "results" / "archive", registry=_registry(tmp_path), retractions=[],
                            now=datetime(2026, 9, 27, tzinfo=UTC), dry_run=True)
    assert result.archived == 1 and store.read_text() == before and not (tmp_path / "results" / "archive").exists()


def test_retract_command_appends_with_reason(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    r = CliRunner().invoke(app, ["retract", "run-x", "--reason", "harness produced the base document", "--by", "arthur"])
    assert r.exit_code == 0, r.output
    (rec,) = pol.load_retractions(tmp_path / "results" / "retractions.jsonl")
    assert rec.id_run == "run-x" and rec.reason.startswith("harness")
    r = CliRunner().invoke(app, ["retract", "run-y", "--reason", "   ", "--by", "arthur"])
    assert r.exit_code != 0
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_ledger_archive.py -q -n 0`
Expected: `ModuleNotFoundError: No module named 'neurotic_docx_bench.ledger.archive'`.

- [ ] **Step 3: Write the module**

```python
"""Move rows that must never be ranked out of the ranked store, with a manifest."""

from __future__ import annotations

import json
import os
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from neurotic_docx_bench.ledger import policy as pol
from neurotic_docx_bench.ledger import rows as rws
from neurotic_docx_bench.ledger.registry import Registry


class ArchiveResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    kept: int
    archived: int
    archive_path: Path | None
    manifest_path: Path | None


def archive_reasons(data: dict, registry: Registry, retractions: Sequence[pol.Retraction]) -> tuple[str, ...]:
    row = rws.row_from_bench_line(data, registry)
    if row is None:
        return ("unmapped tool",)
    reasons: list[str] = []
    if row.provenance != "stamped":
        reasons.append("legacy provenance")
    if row.holdout_mode == "only":
        reasons.append("holdout-only run")
    r = pol.find_retraction(row, retractions)
    if r is not None:
        reasons.append(f"retracted: {r.reason}")
    return tuple(reasons)


def split_store(
    store: Path, archive_dir: Path, *, registry: Registry, retractions: Sequence[pol.Retraction],
    now: datetime, dry_run: bool,
) -> ArchiveResult:
    kept: list[str] = []
    moved: list[tuple[str, dict, tuple[str, ...]]] = []
    for raw in Path(store).read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        data = json.loads(raw)
        reasons = archive_reasons(data, registry, retractions)
        if reasons:
            moved.append((raw, data, reasons))
        else:
            kept.append(raw)
    if dry_run or not moved:
        return ArchiveResult(kept=len(kept), archived=len(moved), archive_path=None, manifest_path=None)
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_path = archive_dir / f"bench-{now.strftime('%Y-%m-%d')}.jsonl"
    with archive_path.open("a", encoding="utf-8") as fh:
        for raw, _data, _reasons in moved:
            fh.write(raw + "\n")
    manifest_path = archive_dir / "MANIFEST.md"
    header = "" if manifest_path.is_file() else "# Archived rows\n\n| archived on | id_run | vendor | benchmark | run timestamp | reason |\n| --- | --- | --- | --- | --- | --- |\n"
    with manifest_path.open("a", encoding="utf-8") as fh:
        fh.write(header)
        for _raw, data, reasons in moved:
            fh.write(f"| {now.strftime('%Y-%m-%d')} | {data.get('id_run')} | {data.get('vendor')} | {data.get('benchmark')} | {str(data.get('timestamp'))[:19]} | {'; '.join(reasons)} |\n")
    tmp = Path(store).with_suffix(".jsonl.tmp")
    tmp.write_text("".join(line + "\n" for line in kept), encoding="utf-8")
    os.replace(tmp, store)
    return ArchiveResult(kept=len(kept), archived=len(moved), archive_path=archive_path, manifest_path=manifest_path)
```

- [ ] **Step 4: Wire rows, policy, build, CLI**

`rows.py`: add `archived: bool = False` to `ResultRow`; `load_bench_rows(path, registry, *, archived: bool = False)` sets it on every row it returns.

`policy.eligibility`: `if row.archived: reasons.append("archived")`.

`build.build`: after loading the ranked store, also load every `results/archive/*.jsonl` with `archived=True` and pass those rows to `history_section` only (not to `select_headline`).

`cli.py`:

```python
@app.command(name="archive")
def archive_cmd(
    dry_run: bool = typer.Option(False, "--dry-run", help="report what would move, change nothing"),
) -> None:
    """Move legacy, holdout-only and retracted rows from results/bench.jsonl to results/archive/."""
    from neurotic_docx_bench.ledger import archive as ar
    from neurotic_docx_bench.ledger.registry import DEFAULT_REGISTRY_PATH, load_registry

    result = ar.split_store(
        Path("results/bench.jsonl"), Path("results/archive"), registry=load_registry(DEFAULT_REGISTRY_PATH),
        retractions=pol.load_retractions(pol.DEFAULT_RETRACTIONS_PATH), now=datetime.now(UTC), dry_run=dry_run,
    )
    console.print(f"kept {result.kept}, {'would archive' if dry_run else 'archived'} {result.archived}")
    if result.archive_path:
        console.print(f"archive: {result.archive_path}; manifest: {result.manifest_path}")


@app.command(name="retract")
def retract_cmd(
    id_run: str = typer.Argument(..., help="the id_run of the line to retract"),
    reason: str = typer.Option(..., "--reason", help="why the run is not a measurement of the tool"),
    by: str = typer.Option(os.environ.get("USER", "unknown"), "--by"),
    benchmark: str | None = typer.Option(None, "--benchmark", help="limit the retraction to one benchmark of that run"),
) -> None:
    """Record that a run must never be ranked, with the reason stated. Never deletes data."""
    if not reason.strip():
        raise typer.BadParameter("--reason must state why")
    pol.append_retraction(
        pol.DEFAULT_RETRACTIONS_PATH,
        pol.Retraction(id_run=id_run, benchmark=benchmark, reason=reason.strip(), retracted_at=datetime.now(UTC), by=by),
    )
    console.print(f"retracted {id_run}: {reason.strip()}")
```

(with `from neurotic_docx_bench.ledger import policy as pol` in the imports.)

- [ ] **Step 5: Run the tests, retract the known-broken runs, archive, regenerate, commit**

Run: `uv run pytest tests/test_ledger_archive.py tests/test_ledger_build.py -q -n 0`
Expected: pass.

The two runs identified in step 3 as not measuring the tool (same pin, same day, one at the null-baseline level):

```bash
uv run bench retract 019f554e-5e5a-720d-b4a3-d72c21e706b5 --reason "jubarte-final-native run on 2026-07-12 07:50 scored at the null-baseline level across all three benchmarks; the 07:58 run of the same pin is the measurement" --by arthur
uv run bench retract <id_run of jubarte-ast roundtrip 2026-09-11T06:21:19> --benchmark roundtrip --reason "roundtrip at 51.87 mean with the identical pin at 99.19 eight hours later; harness state, not the tool" --by arthur
uv run bench retract <id_run of docxodus 9.0.0 script_redlines 2026-08-04T13:11:19> --reason "docxodus 9.0.0 run with 56 generate failures superseded 80 minutes later by the same pin at 4 failures; see tool_updater docstring on the 9.0.0 pin retraction" --by arthur
```

Find the two missing id_runs with `uv run python -c "import json; [print(r['id_run'], r['vendor'], r['benchmark'], r['timestamp']) for r in map(json.loads, open('results/bench.jsonl')) if r['timestamp'][:13] in ('2026-09-11T06', '2026-08-04T13')]"`. Each retraction states its reason in the ledger; the reasons above are the evidence from the store, and the detailed history shows both runs with the verdict.

```bash
uv run bench archive --dry-run
uv run bench archive
uv run bench report
git add -A src tests results/archive results/retractions.jsonl results/bench.jsonl RESULTS.md RESULTS_DETAILED.md README.md
git commit -m "feat(store): archive legacy and holdout-only rows; retraction ledger with stated reasons"
```

Expected `bench archive --dry-run`: `kept 5x, would archive 4x` (40 unstamped lines plus any holdout-only lines plus the retracted ones).

---

### Task 13: Retire the TypeScript generator, `export-results-md.py`, and `docs/RESULTS.md`

**Files:**
- Delete: `scripts/update-readme-ranking.ts`, `scripts/update-readme-ranking.test.ts`, `scripts/export-results-md.py`, `tests/test_export_results_md.py`, `docs/RESULTS.md`
- Modify: `package.json` (remove `update-readme-ranking`), `README.md` (commands, results section, methodology), `.github/workflows/bench.yml` (call `uv run bench report` where the old scripts ran; add `uv run bench report --check` as a job step)
- Modify: `src/neurotic_docx_bench/ledger/tables.py` (`lens_health_section`), `build.py`
- Test: `tests/test_no_legacy_generators.py`, `tests/test_ledger_tables.py` (append)

- [ ] **Step 1: Port the two behaviours the old exporter had that the new report lacks, test first**

Append to `tests/test_ledger_tables.py`:

```python
def test_lens_health_section_lists_disagreeing_tools(registry) -> None:
    from neurotic_docx_bench.ledger.rows import ResultRow
    r = _row("a", "acme", 80.0)
    r2 = r.model_copy(update={"lens_disagree_rate": 0.12, "n_lens_disagree": 9})
    md = tb.lens_health_section([r2, _row("b", "jubarte-x", 90.0)])
    assert "## Lens health" in md and "acme" in md and "9" in md and "0.12" in md
    assert "jubarte-x" not in md


def test_lens_health_section_absent_when_clean(registry) -> None:
    assert tb.lens_health_section([_row("a", "acme", 80.0)]) == ""
```

Add `n_lens_disagree: int | None = None` and `lens_disagree_rate: float | None = None` to `ResultRow`, read them in `row_from_bench_line`, and implement:

```python
def lens_health_section(rows: Sequence[ResultRow]) -> str:
    flagged = [r for r in rows if (r.n_lens_disagree or 0) > 0]
    if not flagged:
        return ""
    body = [[_tool_cell(r), r.benchmark, r.pin.display, fmt_date(r.timestamp), str(r.n_lens_disagree), f"{r.lens_disagree_rate or 0:.2f}"] for r in sorted(flagged, key=lambda r: -(r.lens_disagree_rate or 0))]
    return "\n".join(["## Lens health", "", "Runs where the pixel lens and the functional lens disagreed on some documents. A bench-health alarm, never a ranking input.", "", md_table(["Tool", "Benchmark", "Pin", "Run", "Docs disagreeing", "Rate"], body)]) + "\n"
```

and append it to `detailed_parts` in `build.build` before the methodology. The holdout-gap section of the old exporter read `results/holdout_gap.json`; check `ls results/holdout_gap*.json`. If the file exists, port `holdout_gap_section` as `tb.holdout_gap_section(path)` with one test that feeds a two-vendor JSON and asserts the gap column; if it does not exist, drop the section and say so in the commit body.

- [ ] **Step 2: Write the guard test**

`tests/test_no_legacy_generators.py`:

```python
"""The published views have exactly one generator."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_legacy_generator_files_are_gone() -> None:
    for rel in ("scripts/update-readme-ranking.ts", "scripts/update-readme-ranking.test.ts", "scripts/export-results-md.py", "docs/RESULTS.md"):
        assert not (ROOT / rel).exists(), rel


def test_package_json_has_no_readme_ranking_script() -> None:
    scripts = json.loads((ROOT / "package.json").read_text())["scripts"]
    assert "update-readme-ranking" not in scripts


def test_readme_points_at_bench_report_only() -> None:
    text = (ROOT / "README.md").read_text()
    for stale in ("export-results-md", "update-readme-ranking", "--update-readme", "docs/RESULTS.md"):
        assert stale not in text, stale
    assert "uv run bench report" in text
```

- [ ] **Step 3: Delete and rewrite**

```bash
git rm scripts/update-readme-ranking.ts scripts/update-readme-ranking.test.ts scripts/export-results-md.py tests/test_export_results_md.py docs/RESULTS.md
```

`package.json`: remove the `"update-readme-ranking"` line. `README.md`: replace the four generation commands with `uv run bench report` and the two-line note "RESULTS.md is the headline view, RESULTS_DETAILED.md holds history, paired comparisons and methodology; both are generated"; fix the Results table row and the "Results visibility" paragraph accordingly; in "Scoring" replace "Page-count mismatch is recorded; only min(pages) is scored." with "Pages present on only one side enter at 0, ink-weighted (`pagefair-v2`), for the three redline benchmarks; visual_* rank on the raw score."; state the scoring weights once (SSIM 40, ink 20, edge 15, colour 15, blob 10; document = 0.7 mean + 0.3 worst page); in the header table change "Redline oracle" to "Word tracked-change DOCX, rendered by LibreOffice 26.2.4.2 for oracle and candidates alike"; remove the "Jubarte families list best and worst pin" sentence and replace with "One row per tool, its latest eligible run; author-affiliated tools are marked and follow the same rules"; delete the hand-written pin table (the generated block replaces it). `.github/workflows/bench.yml`: add a step `uv run bench report --check` after the run step.

- [ ] **Step 4: Run everything, commit**

Run: `uv run pytest -q && bunx vitest run && bun run typecheck && uv run ruff check src tests && uv run ty check src`
Expected: pytest all green (the deleted tests' behaviours live in `tests/test_ledger_*.py`); vitest green with `scripts/redline_scoreboard.test.ts` and `scripts/lib/provenance.test.ts`.

```bash
uv run bench report
git add -A
git commit -m "chore(report): retire the TS ranking script, export-results-md.py and docs/RESULTS.md; README states the policy"
git push -u origin consolidate/06-archive
```

Open PR 6: "store: archive, retractions, one generator".

---

## PR 7: calibration rows

```bash
git checkout -b consolidate/07-calibrate consolidate/06-archive
```

### Task 14: `bench calibrate`: the oracle through the pipeline, and the null baseline, as rows

**Files:**
- Create: `src/neurotic_docx_bench/calibration.py`
- Modify: `src/neurotic_docx_bench/cli.py` (command)
- Test: `tests/test_calibration.py`

The two rows every fidelity table should carry (registry ids `oracle-identity`, `null-baseline`) are produced by feeding two synthetic candidate sets through the normal `bench run` path so they get the same docset, renderer, scorer and hardware stamps as every vendor.

- [ ] **Step 1: Read the pair manifest format**

Run: `head -3 corpus/word_based/centralized_mapping.csv && head -3 corpus/word_based/centralized_mapping_randomized.csv`
Record the column names for the base DOCX, the next DOCX and the pair stem; the helper below uses `base`, `next` and `stem`; rename to match the file.

- [ ] **Step 2: Write the failing tests**

```python
"""Calibration candidates: the oracle DOCX renamed as a candidate, and the base DOCX unchanged."""

from __future__ import annotations

import csv
from pathlib import Path

from neurotic_docx_bench import calibration as cal


def _corpus(tmp_path: Path) -> tuple[Path, Path, Path]:
    src = tmp_path / "docx_source"; src.mkdir()
    red = tmp_path / "docx_redlines_word"; red.mkdir()
    (src / "a.docx").write_bytes(b"A")
    (src / "b.docx").write_bytes(b"B")
    (red / "a_b_word_redline.docx").write_bytes(b"AB")
    mapping = tmp_path / "centralized_mapping.csv"
    with mapping.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["stem", "base", "next"])
        w.writeheader()
        w.writerow({"stem": "a_b", "base": "a.docx", "next": "b.docx"})
    return src, red, mapping


def test_oracle_identity_candidates_are_the_oracle_docx_renamed(tmp_path: Path) -> None:
    src, red, mapping = _corpus(tmp_path)
    out = cal.build_candidates("oracle-identity", mapping=mapping, docx_source=src, docx_redlines=red, out_dir=tmp_path / "out")
    assert sorted(p.name for p in out.iterdir()) == ["a_b_oracle-identity_redline.docx"]
    assert (out / "a_b_oracle-identity_redline.docx").read_bytes() == b"AB"


def test_null_baseline_candidates_are_the_base_docx(tmp_path: Path) -> None:
    src, red, mapping = _corpus(tmp_path)
    out = cal.build_candidates("null-baseline", mapping=mapping, docx_source=src, docx_redlines=red, out_dir=tmp_path / "out")
    assert (out / "a_b_null-baseline_redline.docx").read_bytes() == b"A"


def test_missing_oracle_is_reported_not_silently_skipped(tmp_path: Path) -> None:
    src, red, mapping = _corpus(tmp_path)
    (red / "a_b_word_redline.docx").unlink()
    import pytest
    with pytest.raises(FileNotFoundError, match="a_b"):
        cal.build_candidates("oracle-identity", mapping=mapping, docx_source=src, docx_redlines=red, out_dir=tmp_path / "out")


def test_run_configs_are_unversioned_soffice_docx_runs() -> None:
    rcs = cal.run_configs(Path("x/oracle"), Path("x/null"))
    assert [(r.name, r.vendor, r.render, r.unversioned, r.benchmarks) for r in rcs] == [
        ("oracle-identity", "oracle-identity", "soffice", True, ["script_redlines"]),
        ("null-baseline", "null-baseline", "soffice", True, ["script_redlines"]),
    ]
    assert rcs[0].docx == Path("x/oracle")
```

- [ ] **Step 3: Run to verify they fail**

Run: `uv run pytest tests/test_calibration.py -q -n 0`
Expected: `ModuleNotFoundError: No module named 'neurotic_docx_bench.calibration'`.

- [ ] **Step 4: Write the module**

```python
"""Calibration candidates for the fidelity tables.

- ``oracle-identity``: Word's own redline DOCX, renamed as if a tool produced it. Through
  the candidate pipeline it must score 100 (the renderer is deterministic: see
  results/noise_floor.json). It anchors the top of every table.
- ``null-baseline``: the base DOCX submitted unchanged. It is the score a tool gets for
  doing nothing, the floor every redline tool must beat.
"""

from __future__ import annotations

import csv
import shutil
from pathlib import Path
from typing import Literal

from neurotic_docx_bench.config import RunConfig

Kind = Literal["oracle-identity", "null-baseline"]
_ORACLE_SUFFIXES = ("_word_redline.docx", "_redline.docx")


def _oracle_docx(docx_redlines: Path, stem: str) -> Path:
    for suffix in _ORACLE_SUFFIXES:
        p = docx_redlines / f"{stem}{suffix}"
        if p.is_file():
            return p
    raise FileNotFoundError(f"no oracle redline DOCX for pair {stem} under {docx_redlines}")


def build_candidates(kind: Kind, *, mapping: Path, docx_source: Path, docx_redlines: Path, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    with Path(mapping).open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            stem = row["stem"]
            if kind == "oracle-identity":
                src = _oracle_docx(docx_redlines, stem)
            else:
                src = docx_source / row["base"]
                if not src.is_file():
                    raise FileNotFoundError(f"no base DOCX {row['base']} for pair {stem} under {docx_source}")
            shutil.copyfile(src, out_dir / f"{stem}_{kind}_redline.docx")
    return out_dir


def run_configs(oracle_dir: Path, null_dir: Path) -> list[RunConfig]:
    return [
        RunConfig(name="oracle-identity", render="soffice", docx=oracle_dir, vendor="oracle-identity", benchmarks=["script_redlines"], unversioned=True),
        RunConfig(name="null-baseline", render="soffice", docx=null_dir, vendor="null-baseline", benchmarks=["script_redlines"], unversioned=True),
    ]
```

- [ ] **Step 5: The command**

```python
@app.command(name="calibrate")
def calibrate_cmd(
    config: Path = typer.Option(Path("bench.yaml"), "--config", "-c"),
    out: Path = typer.Option(Path("runs/calibration"), "--out"),
    limit: int | None = typer.Option(None, "--limit"),
) -> None:
    """Emit the oracle-identity and null-baseline rows for script_redlines on the current corpus."""
    from neurotic_docx_bench import calibration as cal

    cfg = load_config(config)
    corpus = Path("corpus/word_based")
    oracle_dir = cal.build_candidates("oracle-identity", mapping=corpus / "centralized_mapping.csv",
                                      docx_source=corpus / "docx_source", docx_redlines=corpus / "docx_redlines_word", out_dir=out / "oracle-identity" / "docx")
    null_dir = cal.build_candidates("null-baseline", mapping=corpus / "centralized_mapping.csv",
                                    docx_source=corpus / "docx_source", docx_redlines=corpus / "docx_redlines_word", out_dir=out / "null-baseline" / "docx")
    cfg = dataclasses.replace(cfg, runs=cal.run_configs(oracle_dir, null_dir))
    _drive_runs(cfg, only=None, limit=limit, emit=True, only_on_change=False, do_gate=False, ...)
```

Fill the `_drive_runs` call with the same keyword arguments `run` passes (read `cli.run` at lines 2004 to 2110 and copy its call verbatim, replacing `cfg`). If `_drive_runs` requires a `config_hash`, pass `provenance.config_hash(config)`. The randomized chain (`centralized_mapping_randomized.csv`, `docx_source_randomized`, `docx_redlines_randomized`) is a second mapping; include it by calling `build_candidates` once per mapping into the same `out_dir` so the candidate set covers the full 763-pair docset.

- [ ] **Step 6: Run the tests, then the command on the mac, then regenerate**

Run: `uv run pytest tests/test_calibration.py -q -n 0`
Expected: `4 passed`.

```bash
uv run bench calibrate --limit 5      # smoke: two lines with n_docs 5, itt_n equal to the docset (missing outputs at 0)
uv run bench retract <the two smoke id_runs> --reason "5-document smoke of the calibration command" --by arthur
uv run bench calibrate
uv run bench report
```

Expected after the full run: `RESULTS.md` script_redlines shows "Calibration rows" with `oracle DOCX (identity)` at ITT mean 100.00, ITT median 100.00, Perfect equal to the document count, and `null baseline` around 50 (`results/null_baseline.json` holds per-document values between 45 and 61). If the oracle row is not 100.00 on every document, stop: the README claim is false for the current pipeline and the cause (fonts, LibreOffice build, `_word_redline` variant preference) is a bug to fix before publishing; open an issue with the failing document keys from `results/detail/`.

```bash
git add -A
git commit -m "feat(calibration): oracle-identity and null-baseline rows through the vendor pipeline"
git push -u origin consolidate/07-calibrate
```

Open PR 7: "calibration rows".

---

## Task 15: Re-run list (compute, on the mac, after PR 7 merges)

These produce the rows the consolidated tables need. Each command appends stamped lines (`docset_id`, `renderer_id`, `hardware`, `tool_id`). Run them in this order; each is safe to repeat. Nothing here changes code.

- [ ] **Step 1: Pins are what `bench.yaml` says**

```bash
bun install --frozen-lockfile && uv sync --frozen
uv run bench oracle-manifest            # must report clean; if not, stop and re-baseline knowingly
uv run bench canary                     # must report ok for LibreOffice 26.2.4.2
uv run bench docset --write
```

- [ ] **Step 2: Generators on the current corpus (fidelity)**

```bash
for run in jubarte-rust jubarte-final-lossless jubarte-final-native jubarte-wasm docxodus folio stemma safe-docx-compare redlines superdoc superdoc-redlines docx-redline-js; do
  uv run bench run --only "$run" || echo "FAILED: $run"
done
```

Expected: one line per (run, benchmark) in `results/bench.jsonl`, every line with `itt_n_docs` equal to the docset size for its benchmark (script_redlines 763 minus holdout, accepted_changes and roundtrip at their recorded sizes). jubarte-rust now has accepted_changes and roundtrip rows on the current docset. A run that fails to generate at all still emits a line with every document at 0 (`n_failed_docs == itt_n`), which is the honest number.

- [ ] **Step 3: Editors at their pinned versions (visual)**

```bash
for run in docxodus-playwright-rendering docxodus-playwright-redlines docxodus-playwright-accepted folio-playwright-rendering folio-playwright-redlines folio-playwright-accepted superdoc-playwright-rendering superdoc-playwright-redlines superdoc-playwright-accepted; do
  uv run bench run --only "$run" || echo "FAILED: $run"
done
```

Expected: `renderer_id` = `playwright:docxodus@12.6.2`, `playwright:@stll/folio-react@0.13.4`, `playwright:superdoc@2.18.0`. The visual tables then hold three editors on one group instead of one.

- [ ] **Step 4: Speed with pins and hardware**

```bash
bun run redline-speed-bench:native
node --import tsx scripts/speed-bench.ts --pairs 30 --reps 3 --out results/speed.jsonl
```

Expected: new rows carry `tool_version` and `hardware`; `bench report` populates the speed headline. Rows that ran at 50 fixtures stay under "Not ranked".

- [ ] **Step 5: Converters, every tool on both tracks and the docxide lens, one jubarte binary**

```bash
JUB=/Users/arthrod/temp/T/jubarte-redlines/target/release/jubarte
$JUB --version                          # record it; the same binary feeds all three commands below
TOOLS="--tool jubarte --tool rdocx --tool office2pdf --tool pdfitdown --tool libreoffice_convert_rust --tool dxpdf --tool docxide-pdf"
uv run bench docx-to-pdf --converter $JUB $TOOLS --track docx_to_pdf --json results/docx_to_pdf.json
uv run bench docx-to-pdf --converter $JUB $TOOLS --track docx_to_pdf_no_redline_docs --json results/docx_to_pdf_no_redline.json
uv run bench docxide-metrics --converter $JUB $TOOLS --json results/docxide_metrics.json
```

Expected: `results/converters.jsonl` gains 7 + 7 + 7 lines; the docxide_metrics table ranks seven converters, not two; jubarte's pin is identical across the three tables. doxx is not in the list on purpose (not applicable, still listed by the registry).

- [ ] **Step 6: Archive, report, commit results**

```bash
uv run bench archive
uv run bench report
uv run bench report --check
git add results RESULTS.md RESULTS_DETAILED.md README.md
git commit -m "results: consolidated re-run on docset $(python3 -c "import json;print(sorted(json.load(open('results/docsets.json')).items())[0][0])")"
git push
```

- [ ] **Step 7: Read the headline once as a stranger would**

Open `RESULTS.md`. For each table confirm: one row per tool; `Docs + Failed` equals the document count in the caption; the CI column is populated; jubarte rows carry the marker; the oracle-identity row reads 100.00; nothing says "legacy"; the speed table names the machine. Anything else is a bug in this plan, not in the data.

---

## Task 16: Verification

- [ ] **Step 1: Coverage on the new package and on the touched modules**

Run: `uv run pytest --cov=src/neurotic_docx_bench/ledger --cov=src/neurotic_docx_bench/hardware.py --cov=src/neurotic_docx_bench/calibration.py --cov=src/neurotic_docx_bench/aggregate.py --cov=src/neurotic_docx_bench/results_schema.py --cov-report=term-missing --cov-branch -q`
Expected: line coverage at or above 90% and branch coverage at or above 85% for `report/` (it is pure logic and fully driven by tests above); at or above 80% / 70% for the rest. Below that, add tests for the uncovered branches the report prints; do not exclude lines.

- [ ] **Step 2: Whole suite, both languages, types, lint**

Run: `uv run pytest -q && bunx vitest run && bun run typecheck && bun run lint && uv run ruff check src tests && uv run ruff format --check src tests && uv run ty check src`
Expected: all green.

- [ ] **Step 3: Store invariants extended**

Append to `tests/test_store_invariants.py` and run:

```python
@needs_store
def test_headline_rows_are_complete_and_one_per_tool() -> None:
    from neurotic_docx_bench.ledger import build as bd
    from neurotic_docx_bench.ledger import policy as pol
    from neurotic_docx_bench.ledger import stats as st
    registry = load_registry(REGISTRY)
    rows, _ = rws.load_bench_rows(BENCH, registry)
    docsets = pol.load_docsets_json(ROOT / "results" / "docsets.json")
    tables = pol.select_headline(rows, registry=registry, retractions=pol.load_retractions(ROOT / pol.DEFAULT_RETRACTIONS_PATH), docsets=docsets, tie_fn=lambda a, b: st.tie_by_paired_bootstrap(a.scores, b.scores))
    for benchmark, t in tables.items():
        ids = [r.row.tool_id for r in t.rows]
        assert len(ids) == len(set(ids)), benchmark
        for r in t.rows:
            assert r.row.n_scored + r.row.n_failed_docs == t.expected_n, (benchmark, r.row.tool_id)
            assert r.row.provenance == "stamped"


@needs_store
def test_published_views_are_current() -> None:
    from typer.testing import CliRunner
    from neurotic_docx_bench.cli import app
    result = CliRunner().invoke(app, ["report", "--check", "--root", str(ROOT)])
    assert result.exit_code == 0, result.output
```

Run: `uv run pytest tests/test_store_invariants.py -q -n 0`
Expected: `4 passed`.

- [ ] **Step 4: Mutation testing on the policy (the module the whole benchmark's honesty depends on)**

```bash
uv add --group dev mutmut
uv run mutmut run --paths-to-mutate src/neurotic_docx_bench/ledger/policy.py --tests-dir tests/ -- -q -n 0 tests/test_ledger_policy.py
uv run mutmut results
```

Expected: mutation score at or above 60%. Survivors that change ranking order or eligibility get a test each.

- [ ] **Step 5: Stacked PRs merge in order**

PR 1 → PR 2 → PR 3 → PR 4 → PR 5 → PR 6 → PR 7, each rebased on the previous merge. After PR 7 merges, run Task 15 on `main`.

---

## Coverage of the step-1 findings

| Finding | Where it is fixed | Or why not |
| --- | --- | --- |
| 1 Docs + Failures ≠ ITT | Tasks 3, 4 (`n_failed_docs`), invariant tests | |
| 2 identical rows under two labels | Tasks 5, 8 (docset groups), Task 12 (archive), Task 13 (no legacy tables) | |
| 3 same commit, different scores | Task 2 (`same_commit`), Task 15 re-runs both bindings on one docset; history shows both | root cause is dist provenance already fixed upstream in `resolve_local_version` |
| 4 one pin, two families | Task 1 registry (`configuration`), Task 6 (`tool_id`, `configuration` on the line), Task 12 retraction of the null-level run | |
| 5 sanity-word at 70 | Task 14 calibration rows replace it; sanity-word retired in the registry | |
| 6 jubarte 0.7.0 vs 0.8.0 across converter tables | Task 15 step 5 (one binary), tables show the pin | |
| 7 undocumented tie-break | Task 8 sort key, Task 10 caption | |
| 8, 10 README pins stale, docxodus one pin for two roles | Task 1 registry, Task 10 generated vendor block, Task 13 hand-written table deleted | |
| 9 undefined vendor names, three naming layers | Task 1 registry with `run_names`, `speed_tools`, `converter_tools`; Task 3 invariant refuses unmapped lines | |
| 11 version string schema drift | Task 2 `ToolPin.display` | strings in the store are not rewritten |
| 12 speed rows without version, hardware, mixed N | Task 7, Task 8 speed eligibility | |
| 13 four views, three toolchains | Tasks 10, 11, 13 | `runs/<run>/report.html` stays as the per-run visual report |
| 14 no dates, ids, hardware | Tasks 6, 10 (Run column, Machine column, history `id_run`) | |
| 15 vendor-specific ITT | Task 5 docset + missing-output failures | |
| 16 ranked incomparable rows | Task 8 groups; history is never ranked | |
| 17 best/worst and best-of-N | Task 8 (latest eligible run), Task 12 retractions with reasons | |
| 18 min(pages) | Already `pagefair-v2`; Task 13 README correction | |
| 19 failure policy differs in speed | Task 8 speed eligibility, Task 10 caption; D4 | timing still excludes failures; the count is in the row |
| 20 chained denominator | Task 5 (accepted/roundtrip docsets from oracle dirs, missing at 0) | |
| 21 oracle semantics under one headline | Task 10 `ORACLE_NOTES`, Task 13 README; D2 renderer axis | |
| 22 roundtrip two operations | not changed: the store carries `run_name`; a `configuration` per roundtrip mode can be added in the registry when the two paths are separated | deferred, stated |
| 23 unexplained sub-corpus sizes, missing jubarte-rust coverage | Task 5 `results/docsets.json`, Task 15 step 2 | |
| 24 undisclosed scoring formula and dependency | Task 10 methodology, Task 13 README | |
| 25 no uncertainty | Task 9, Task 10 CI column and paired section | |
| 26 second scorer on 2 of 8, corpus publishes 3 renderers | Task 15 step 5; renderer corpus publication is a separate decision (D5 scope) | deferred, stated |
| 27 doxx ranked, pdfitdown duplicate | Task 1 `not_applicable`, engine shown; Task 10 | |
| 28 docx_to_pdf naming and "randomized" undefined | Task 10 titles and oracle notes | file names unchanged |
| 29 760 floor contradictions | Task 8 completeness replaces the floor | |
| 30 gate threshold unstated | Task 13 README: gate described as CI tooling with `eps = max(1e-4, 3 sigma)` from `noise_floor.py` | |
| 31 Perfect (100) undefined | Task 13 README: "within 1e-6 of 100 (`aggregate.compute_aggregate`)" | |

## Self-review notes

- Spec coverage: every finding above maps to a task or an explicit deferral.
- Placeholders: none; every code step carries its code, every command its expected output. Two spots read the repository before writing (Task 5 step 4 on `_index_plain`, Task 14 step 1 on the CSV header) and say what to do with what they find.
- Names used across tasks: `ResultRow`, `SpeedRow`, `ToolPin`, `Registry`, `ToolEntry`, `DocSet`, `HeadlineTable`, `RankedRow`, `ExcludedRow`, `SpeedHeadline`, `Retraction`, `Bundle`; functions `load_registry`, `row_from_bench_line`, `load_bench_rows`, `speed_row_from_line`, `load_speed_rows`, `row_from_converter_line`, `load_converter_rows`, `benchmark_docset`, `missing_output_failures`, `select_headline`, `select_speed_headline`, `eligibility`, `group_key`, `expected_n`, `bootstrap_median_ci`, `paired_median_diff`, `tie_by_paired_bootstrap`, `fidelity_table`, `speed_tables`, `history_section`, `paired_section`, `methodology_section`, `vendor_table`, `lens_health_section`, `build`, `write`, `changed_files`, `split_store`, `append_retraction`, `load_retractions`, `lines_from_report`, `append_report`, `build_candidates`, `run_configs`, `hardware_info`, `renderer_id`, `failed_doc_keys`. Each is defined in exactly one task before it is used.


## Deviations from the plan as written (implementation record, 2026-09-27)

Each item names what the plan said, what was done instead, and why. Nothing below changes a decision D1 to D6.

1. Package name. The plan's `neurotic_docx_bench.report` package collides with the existing module `src/neurotic_docx_bench/report.py` (the parity-locked scoring core that `__init__.py` imports). The package is `neurotic_docx_bench.ledger`; the plan text was renamed to match. The CLI command is still `bench report`.
2. Plan location. `docs/superpowers/plans/` is gitignored in this repository, so the plan lives at `docs/plans/2026-09-27-benchmark-consolidation.md`.
3. Task 5 gained `ledger.docset.restrict_to_docset`. The emitter restricts scores, per-document rows and failures to the benchmark's document set before counting, and prints one warning naming the dropped keys. Without it a candidate directory containing files outside the oracle set would inflate `itt_n` past the docset size and the row would read as "incomplete" against itself.
4. Row identity and uncertainty. One `id_run` spans up to three benchmarks, so confidence intervals, ties and paired statistics are keyed by `ResultRow.key` (`id_run|benchmark`), not by `id_run`. All three are computed on the ITT pool (`ResultRow.itt_scores()`: scored documents plus failed documents at 0.0), not on scored documents only; `failed_docs` is carried on the row for that purpose. The first real `bench report` exposed both: the previous keying collided across benchmarks and the previous pool understated the interval of every row with failures.
5. `HeadlineTable.docset_recorded`. Stamped rows that predate PR 2 carry `corpus_revision` but no `docset_id`, so their group's document set is not in `results/docsets.json`. When that is the case the table caption says the document set was inferred from the rows' `itt_n` (the maximum over stamped rows). This disappears once Task 15 re-runs the generators.
6. Retractions: none recorded, and `results/retractions.jsonl` does not exist yet (`load_retractions` treats a missing file as empty). The three retractions the plan listed do not hold once the registry is applied: the 2026-07-12 07:50 run is run name `jubarte-final-native`, which the registry maps to the jubarte (ast) configuration, so it is a different tool row and not a duplicate of the lossless run; the other two are earlier runs of the same pin and are superseded by later runs under the latest-eligible-run policy, which needs no retraction to ignore them. `bench retract` is in place for the cases that do need one.
7. `holdout_gap_section` was ported from the deleted `scripts/export-results-md.py` into `ledger/tables.py` (it reads the raw store, not `ResultRow`, because it needs the holdout-only rows that the row loader marks ineligible) and renders in `RESULTS_DETAILED.md`. `tests/test_holdout.py` was rewritten against the ledger helpers (`_ledger_registry`, `_ranked_rows`, `_stamped`); `tests/test_compact_results.py` was kept and ported to a `_headline_markdown` helper.
8. Speed headline is empty on today's store. None of the 139 speed rows carries a pin because the `tool_version` column did not exist before PR 3, so `select_speed_headline` lists every tool under exclusions ("unpinned speed row") until the two speed benches are re-run (Task 15 steps 3 and 4).
9. Task 16 went further than written. `hardware.py` takes its OS boundaries as parameters (`system`, `cpuinfo`, `run`) so every branch is exercised without patching (67% to 100%). Mutation testing ran on `ledger/policy.py` with mutmut 3.8 from a copy outside the repository (mutmut writes a `mutants/` directory): the first pass killed 330 of 392 and the survivors pointed at ten missing assertions (expected_n fallbacks, exact reason strings, the mean tie-break in `rank_rows`, retraction scoping to one benchmark, the `legacy-<render>` group key, `history_groups` order, calibration rows absent from `excluded`, a no-eligible benchmark not stopping the loop, speed reasons for retired, micro and unsized rows, `load_docsets_json` on a real file). After adding them and deleting a dead `shown` set in `select_headline`, 392 of 401 are killed; the nine survivors are file-I/O flags (`mkdir` arguments, `open` mode, `encoding`) and one equivalent mutant. Ledger package coverage: 95% line with 34 partial branches of 388.
10. Task 15 was not run. It needs the mac (LibreOffice, Word, Playwright, bun, the vendor binaries); the exact command list is in Task 15 and repeated in the hand-off message.
11. Git mechanics. `git commit` and `git status` time out over the mounted checkout (index refresh of 10,599 files), so commits were made with plumbing (`git add`, `write-tree`, `commit-tree`, `update-ref`) under the author Arthur Rodrigues. Nothing was pushed. The stack is based on `bench/latest-competitors-0926` at 962fb8e0 (one commit past `origin/bench/latest-competitors-0926`), not on `main`; PR 1 targets that branch or `main` after it merges.
12. TypeScript verification. `scripts/lib/provenance.test.ts` was checked with `tsc` and a `node --experimental-strip-types` smoke run; vitest, oxlint and tsx could not load in the Linux VM (mac-built native bindings). Run `bunx vitest run scripts/lib/provenance.test.ts` on the mac before opening PR 3.
13. Full suite. Twelve to thirteen failures are identical on the baseline commit and this branch (Playwright, Word, bun-dependent, ratchet, superdoc_pins, cli_driver, tool_updater): environment, not regressions.
