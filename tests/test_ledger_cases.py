"""The cases release — adapter, emitter, the release-views flow (Plan 3b, #119).

Spec: docs/plans/2026-11-02-plan3b-cases-speed.md; survey:
docs/plans/reviews/plan3b-survey.md. The release contract is `bench_ops.models`
(the bench-ops dependency): Case, CaseShard, CasesIndex, engines_from_cases,
validate_bundle, shard_path, dumps_compact.

bench-ops is not a venv dependency (#134): it is a PEP 723 inline dependency of
scripts/release_views.py. This module skips under a plain `uv run pytest` and
runs under the overlay that provides it.
"""

from __future__ import annotations

import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

pytest.importorskip(
    "bench_ops",
    reason=(
        "bench-ops is a PEP 723 inline dependency of scripts/release_views.py, not a "
        "venv dependency (#134); run: uv run --with 'bench-ops @ git+https://github.com/"
        "arthrod/bench-ops@6478817465f67726c1450dbeaf090a9fa7ca44b2' pytest -q "
        "tests/test_ledger_cases.py tests/test_ledger_speed.py tests/test_ledger_cases_ref.py"
    ),
)

from neurotic_docx_bench.ledger import build as bd
from neurotic_docx_bench.ledger import cases as cases_emit
from neurotic_docx_bench.ledger import cases_adapter
from test_ledger_build import repo as _ledger_repo  # noqa: F401  the fake-repo fixture, shared with test_ledger_build

from bench_ops.models import (
    Case,
    CaseShard,
    CasesIndex,
    Engine,
    MetricDiagnostics,
    ShardRef,
    dumps_compact,
    shard_path,
    validate_bundle,
)

REPO = Path(__file__).resolve().parents[1]
T0 = datetime(2026, 11, 2, 12, 0, tzinfo=UTC)

# The public R2 base every published page/PDF URL resolves against (survey §1.1).
ASSETS_BASE = "https://pub-92c80eda1059428394970066c8500eda.r2.dev/"

# The published case populations (survey "Group populations", re-counted from the
# live inline DATA on 2026-11-02). The adapter must reproduce them exactly.
PUBLISHED_CONVERSION_GROUPS = {
    "cases": 76,
    "corpus/clean": 977,
    "corpus/tracking_without_comments": 476,
    "corpus/with_comments_clean": 62,
    "corpus/with_comments_tracking": 145,
    "new": 74,
    "samples": 5,
    "scraped": 53,
    "v1/clean": 2478,
    "v1/tracking_without_comments": 237,
    "v1/with_comments_clean": 112,
    "v1/with_comments_tracking": 98,
    "wordcraft1014/convert": 400,
}
PUBLISHED_REDLINE_GROUPS = {
    "accepted/tracking_without_comments": 5,
    "ar/accept_all": 400,
    "ar/reject_all": 400,
    "redlines/tracking_without_comments": 902,
    "redlines/with_comments_clean": 2,
    "redlines/with_comments_tracking": 112,
    "rejected/tracking_without_comments": 8,
    "wordcraft1014/compare": 400,
}

# Families the stores cannot derive (yet), pinned family by family (survey §1.1 "Can
# ndb emit the case contract today?": no canonical store under results/ holds the
# page/PDF asset trees, the shown-page vectors, per-case SSIM, the reference-app
# notes, the display version strings or the cohort `dropped` curation). They reach
# the release only through the adapter-produced legacy_cases input. When a family's
# assets return to the stores this set must shrink with them — the acceptance test
# below fails until it does.
ADAPTER_ONLY_FAMILIES = frozenset(
    {("conversion", g) for g in PUBLISHED_CONVERSION_GROUPS}
    | {("redline", g) for g in PUBLISHED_REDLINE_GROUPS}
)


# ---- helpers ---------------------------------------------------------------------------


LEGACY_SITE_REF = "archive/gh-pages-2026-11-02"
"""The frozen legacy gh-pages site the adapter reads (610bc447). gh-pages itself
became the bench-viewer build on 2026-11-03 and carries no inline DATA (#150)."""
LEGACY_SITE_FILES = ("index.html", "redlines/index.html", "redlines/cases.json")
_LEGACY_CACHE: dict[str, Path | None] = {}


def _is_legacy_site(p: Path) -> bool:
    """A directory holding the old viewers: both pages carry the inline ``const DATA``."""
    pages = (p / "index.html", p / "redlines" / "index.html")
    return all(f.is_file() and "const DATA = " in f.read_text(encoding="utf-8") for f in pages)


def _legacy_site_from_git(tmp_root: Path) -> Path | None:
    """Materialise the legacy pages from LEGACY_SITE_REF (local, then origin/)."""
    for ref in (LEGACY_SITE_REF, f"origin/{LEGACY_SITE_REF}"):
        out = tmp_root / ref.replace("/", "_")
        try:
            for name in LEGACY_SITE_FILES:
                blob = subprocess.run(
                    ["git", "-C", str(REPO), "show", f"{ref}:{name}"],
                    capture_output=True,
                    check=True,
                    timeout=60,
                ).stdout
                (out / name).parent.mkdir(parents=True, exist_ok=True)
                (out / name).write_bytes(blob)
        except (OSError, subprocess.SubprocessError):
            continue
        if _is_legacy_site(out):
            return out
    return None


def _site_dir(tmp_root: Path | None = None) -> Path | None:
    """The legacy published site: NDB_SITE_DIR, <repo>/site, or the registered
    gh-pages worktree when it still holds the old viewers, else the pages of
    LEGACY_SITE_REF. None when this machine has none of them (test skips)."""
    env = os.environ.get("NDB_SITE_DIR")
    if env:
        p = Path(env)
        return p if _is_legacy_site(p) else None
    cand = REPO / "site"
    if _is_legacy_site(cand):
        return cand
    try:
        out = subprocess.run(
            ["git", "-C", str(REPO), "worktree", "list", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        out = ""
    for block in out.split("\n\n"):
        if "refs/heads/gh-pages" in block:
            for line in block.splitlines():
                if line.startswith("worktree "):
                    p = Path(line[len("worktree ") :])
                    if _is_legacy_site(p):
                        return p
    key = str(tmp_root)
    if key not in _LEGACY_CACHE:
        import tempfile

        root = tmp_root or Path(tempfile.mkdtemp(prefix="ndb-legacy-site-"))
        _LEGACY_CACHE[key] = _legacy_site_from_git(root)
    return _LEGACY_CACHE[key]


def test_site_dir_never_returns_a_non_legacy_site(tmp_path: Path, monkeypatch) -> None:
    """A gh-pages copy without the inline DATA (the bench-viewer build) is not the
    adapter's source: NDB_SITE_DIR pointing at one yields None, not a crash (#150)."""
    new = tmp_path / "new"
    (new / "redlines").mkdir(parents=True)
    (new / "index.html").write_text("<script type=module src=js/app.js></script>", encoding="utf-8")
    (new / "redlines" / "index.html").write_text("<script type=module></script>", encoding="utf-8")
    monkeypatch.setenv("NDB_SITE_DIR", str(new))
    assert _site_dir() is None


def test_legacy_site_comes_from_the_archive_branch(tmp_path: Path) -> None:
    """With no legacy worktree, the pages are read from LEGACY_SITE_REF (#150)."""
    try:
        subprocess.run(
            ["git", "-C", str(REPO), "rev-parse", "--verify", "-q", f"origin/{LEGACY_SITE_REF}"],
            capture_output=True,
            check=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        pytest.skip(f"{LEGACY_SITE_REF} is not fetched here")
    site = _legacy_site_from_git(tmp_path)
    assert site is not None and _is_legacy_site(site)


def _published_html(engines: list[list[str]], cases: list[dict]) -> str:
    """A gh-pages-shaped page: the case browser's inline ``const ENGINES/DATA``."""
    return (
        "<!doctype html><html><head><title>cases</title></head><body>\n"
        "<script>\n"
        f"const ENGINES = {json.dumps(engines)};\n"
        f"const DATA = {json.dumps(cases)};\n"
        "</script>\n</body></html>\n"
    )


def _stable_dumps(index: CasesIndex) -> str:
    """dumps_compact with the emission clock pinned, so two runs compare."""
    return dumps_compact(index.model_copy(update={"generated": T0}))


def _counts(index: CasesIndex, shards: list[CaseShard]) -> dict[tuple[str, str], int]:
    return {(s.kind, s.group): len(s.cases) for s in shards}


def _diff_cases(want: Case, got: Case | None) -> list[str]:
    """Per-field differences between the adapter's case and the emitter's, so a
    RED/GREEN failure says exactly which fields are missing or wrong."""
    if got is None:
        return ["<case missing>"]
    a, b = want.model_dump(mode="json"), got.model_dump(mode="json")
    keys = sorted(set(a) | set(b))
    return [f"{k}: adapter={a.get(k)!r} emitter={b.get(k)!r}" for k in keys if a.get(k) != b.get(k)]


# ---- the one-time adapter: from_published(html_or_json_path) ---------------------------


def test_adapter_reads_inline_html_and_rewrites_asset_urls(tmp_path: Path) -> None:
    """site/index.html: inline DATA with absolute R2 URLs becomes kind=conversion
    cases with ~/ paths relative to the discovered assets_base."""
    page = tmp_path / "site" / "index.html"
    page.parent.mkdir(parents=True)
    page.write_text(
        _published_html(
            [["reference", "Word"], ["jubarte", "jubarte"]],
            [
                {
                    "group": "v1/clean",
                    "case": "00163e55a0",
                    "pages": {
                        "reference": [ASSETS_BASE + "d2p_v1/v1/clean/00163e55a0/reference/page_001.webp"],
                        "jubarte": [None],
                    },
                    "page_counts": {"reference": 1, "jubarte": 0},
                    "scores": {"jubarte": {"pixel": 71.52493617107378, "jaccard": None}},
                    "times": {"jubarte": 0.219},
                    "versions": {"reference": "Word", "jubarte": "jubarte 0.14.0"},
                    "dropped": ["ghost-1.0"],
                    "reference_app": "Microsoft Word",
                    "pdfs": {"reference": ASSETS_BASE + "d2p_v1/v1/clean/00163e55a0/reference/pages.pdf"},
                    "errors": {"jubarte": "exit 1"},
                    "metric_diagnostics": {
                        "jubarte": {
                            "ref_pages": 1,
                            "pages": 1,
                            "scored_pages": 0,
                            "max_break_drift": -3,
                        }
                    },
                    "shown": [1],
                    "stem": "clean__00163e55a0_7d35102e1569471281c726baa1f9e9cc31e56e839f337972",
                    "set": "v1",
                }
            ],
        ),
        encoding="utf-8",
    )
    index, shards = cases_adapter.from_published(page)
    assert index.assets_base == ASSETS_BASE
    assert _counts(index, shards) == {("conversion", "v1/clean"): 1}
    case = shards[0].cases[0]
    assert case.kind == "conversion"
    assert case.pages == {
        "reference": ["~/d2p_v1/v1/clean/00163e55a0/reference/page_001.webp"],
        "jubarte": [None],
    }
    assert case.pdfs == {"reference": "~/d2p_v1/v1/clean/00163e55a0/reference/pages.pdf"}
    assert case.scores["jubarte"]["jaccard"] is None  # upstream nulls stay null
    assert case.metric_diagnostics["jubarte"].max_break_drift == -3  # signed
    assert case.errors == {"jubarte": "exit 1"}
    index.validate_shard(shards[0])


def test_adapter_marks_a_redlines_page_by_its_path(tmp_path: Path) -> None:
    """A page under a redlines/ path component imports as kind=redline (the kind
    is the source page, never inferred from group spelling)."""
    page = tmp_path / "site" / "redlines" / "index.html"
    page.parent.mkdir(parents=True)
    page.write_text(
        _published_html(
            [["reference", "Word"], ["jubarte-rust", "jubarte"]],
            [
                {
                    "group": "redlines/tracking_without_comments",
                    "case": "aec80553e5",
                    "pages": {
                        "reference": [ASSETS_BASE + "renew1030/redlines/tracking_without_comments/aec80553e5/reference/page_001.webp"],
                        "jubarte-rust": [None, None],
                    },
                    "page_counts": {"reference": 1, "jubarte-rust": 0},
                    "scores": {"jubarte-rust": {"pixel": 0.0}},
                    "times": {},
                    "versions": {"reference": "Word 16.114 compare", "jubarte-rust": "0.12.0 (release)"},
                    "dropped": ["docxodus"],
                    "reference_app": "macOS Version 26.6.2 (Build 25G83) Quartz PDFContext",
                    "sets": "word_based_0926",
                }
            ],
        ),
        encoding="utf-8",
    )
    index, shards = cases_adapter.from_published(page)
    assert _counts(index, shards) == {("redline", "redlines/tracking_without_comments"): 1}
    case = shards[0].cases[0]
    assert case.kind == "redline"
    assert case.sets == "word_based_0926"
    assert case.pages["jubarte-rust"] == [None, None]
    index.validate_shard(shards[0])


def test_adapter_reads_the_law_data_json_form(tmp_path: Path) -> None:
    """The benchmarks.law form — {base, cases} with ~/ paths — imports unchanged."""
    p = tmp_path / "site" / "redlines" / "data.json"
    p.parent.mkdir(parents=True)
    p.write_text(
        json.dumps(
            {
                "base": ASSETS_BASE,
                "cases": [
                    {
                        "group": "ar/accept_all",
                        "case": "pair_one__vs__pair_two_redline_9ec4fe3616",
                        "pages": {
                            "reference": ["~/renew1030/ar/accept_all/pair_one__vs__pair_two_redline_9ec4fe3616/reference/page_001.webp"]
                        },
                        "page_counts": {"reference": 1},
                        "scores": {},
                        "times": {},
                        "versions": {
                            "reference": "Microsoft Word for Mac accept/reject",
                            "stemma-0.5.0": "stemma 0.5.0",
                            "wordcraft": "wordcraft",
                        },
                        "dropped": [],
                        "reference_app": "Microsoft Word for Mac",
                        "pair": None,
                        "not_applicable": ["stemma-0.5.0"],
                        "unavailable": ["wordcraft"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    index, shards = cases_adapter.from_published(p)
    assert index.assets_base == ASSETS_BASE
    assert _counts(index, shards) == {("redline", "ar/accept_all"): 1}
    case = shards[0].cases[0]
    assert case.not_applicable == ["stemma-0.5.0"]
    assert case.unavailable == ["wordcraft"]
    index.validate_shard(shards[0])


def test_adapter_index_covers_engines_used_only_in_dropped(tmp_path: Path) -> None:
    """The real published data drops engine keys the page's ENGINES never
    declares (jubarte-093 & co): the index must still list them, or
    validate_shard refuses the shard."""
    page = tmp_path / "site" / "index.html"
    page.parent.mkdir(parents=True)
    page.write_text(
        _published_html(
            [["reference", "Word"], ["jubarte", "jubarte"]],
            [
                {
                    "group": "samples",
                    "case": "s1",
                    "pages": {"reference": [ASSETS_BASE + "x/samples/s1/reference/page_001.webp"]},
                    "page_counts": {"reference": 1},
                    "scores": {},
                    "times": {},
                    "versions": {"reference": "Word"},
                    "dropped": ["jubarte", "jubarte-093", "ghost-1.0"],
                    "reference_app": "Microsoft Word",
                }
            ],
        ),
        encoding="utf-8",
    )
    index, shards = cases_adapter.from_published(page)
    keys = {e.key for e in index.engines}
    assert {"reference", "jubarte", "jubarte-093", "ghost-1.0"} <= keys
    for e in index.engines:
        assert isinstance(e, Engine) and e.label  # every entry carries a display label
    index.validate_shard(shards[0])


def test_adapter_output_is_deterministic(tmp_path: Path) -> None:
    """Two imports of the same page agree byte-for-byte (modulo the emission
    clock), and every shard survives a dumps_compact round trip unchanged."""
    case = {
        "group": "v1/clean",
        "case": "00163e55a0",
        "pages": {"reference": [ASSETS_BASE + "d2p_v1/v1/clean/00163e55a0/reference/page_001.webp"]},
        "page_counts": {"reference": 1},
        "scores": {},
        "times": {},
        "versions": {"reference": "Word"},
        "dropped": [],
        "reference_app": "Microsoft Word",
        "shown": [1],
        "stem": "clean__00163e55a0_7d35",
        "pair": None,
    }
    page = tmp_path / "site" / "index.html"
    page.parent.mkdir(parents=True)
    page.write_text(_published_html([["reference", "Word"]], [case]), encoding="utf-8")
    i1, s1 = cases_adapter.from_published(page)
    i2, s2 = cases_adapter.from_published(page)
    assert i1.generated.tzinfo is not None  # naive timestamps are rejected by the contract
    assert _stable_dumps(i1) == _stable_dumps(i2)
    assert [dumps_compact(s) for s in s1] == [dumps_compact(s) for s in s2]
    for shard in s1:
        text = dumps_compact(shard)
        assert dumps_compact(CaseShard.model_validate_json(text)) == text


def test_adapter_imports_today_published_pages() -> None:
    """The real gh-pages pages: every case validates, the shard counts equal the
    published counts, and the compact round trip is byte-stable."""
    site = _site_dir()
    if site is None:
        pytest.skip("no published gh-pages site on this machine (set NDB_SITE_DIR)")
    conv_index, conv_shards = cases_adapter.from_published(site / "index.html")
    red_index, red_shards = cases_adapter.from_published(site / "redlines" / "index.html")
    assert dict(_counts(conv_index, conv_shards)) == {
        ("conversion", g): n for g, n in PUBLISHED_CONVERSION_GROUPS.items()
    }
    assert dict(_counts(red_index, red_shards)) == {
        ("redline", g): n for g, n in PUBLISHED_REDLINE_GROUPS.items()
    }
    seen: set[tuple[str, str, str]] = set()
    for index, shards in ((conv_index, conv_shards), (red_index, red_shards)):
        validate_bundle(index, shards)
        for shard in shards:
            index.validate_shard(shard)
            text = dumps_compact(shard)
            assert dumps_compact(CaseShard.model_validate_json(text)) == text
            for case in shard.cases:
                assert isinstance(case, Case)
                key = (case.kind, case.group, case.case)
                assert key not in seen, f"duplicate case identity {key}"
                seen.add(key)
    assert len(seen) == 5193 + 2229
    # the redline jubarte lane is disambiguated from the conversion one: labels
    # stay unique when the two kinds share one index (engines_from_cases)
    red_labels = {e.key: e.label for e in red_index.engines}
    assert red_labels["jubarte-rust"] == "jubarte (rust)"
    assert len({e.label for e in red_index.engines}) == len(red_index.engines)
    # the published pixel epsilon: values above 100 exist and must validate
    above = [
        v
        for _, shards in ((conv_index, conv_shards), (red_index, red_shards))
        for s in shards
        for c in s.cases
        for m in c.scores.values()
        for v in m.values()
        if v is not None and v > 100
    ]
    assert above and all(v <= 100.000001 for v in above)


# ---- the emitter: ledger.cases.emit(root) ----------------------------------------------
#
# The synthetic fixture mirrors the two store families the survey names, at
# minimal scale, with their real on-disk shapes:
#
#   * conversion, results/docx_to_pdf_v1_89/{full,soffice_full}.json — the
#     report JSONs site_1028/prepare.py::v1() reads (stems carry the state
#     prefix; tools carry version/per_doc/convert_seconds), plus the family's
#     local asset tree under assets/ (the WebP/PDF trees the run dirs held
#     before upload_r2.py moved them to the R2 prefix d2p_v1/v1);
#   * redline, results/redlines_0929_split/scores.jsonl — the per-pair `rows`
#     store with versions.json, plus its asset tree (R2 prefix renew1030/ar).
#
# Everything the emitter cannot know from these inputs (the historical cohort
# families, per-case `dropped` curation) is pinned by the integration test
# below instead: emitter == adapter, per field.

_V1_STEM_A = "clean__00163e55a0_7d35102e1569471281c726baa1f9e9cc31e56e839f337972"
_V1_STEM_B = "clean__0048ba31dd_000be19a055234f8e79ec0baadc41d2a49050b2bea2a60654"
_AR_PAIR = (
    "00da16e738_heading_4_style_demo_id_paraid_overflow_2__vs__"
    "82928b2e05_heading_4_style_demo_id_paraid_overflow_redline_9ec4fe3616"
)


def _write_v1_assets(root: Path) -> None:
    base = root / "results" / "docx_to_pdf_v1_89" / "assets"
    for case_id in ("00163e55a0", "0048ba31dd"):
        for engine in ("reference", "docxodus", "jubarte", "libreoffice"):
            d = base / "clean" / case_id / engine
            d.mkdir(parents=True)
            (d / "page_001.webp").write_bytes(b"webp")
            (d / "pages.pdf").write_bytes(b"pdf")


def _write_cases_sources(root: Path) -> None:
    """The synthetic stores the emitter reads (shapes verified against the real
    results/ tree, 2026-11-02)."""
    v1 = root / "results" / "docx_to_pdf_v1_89"
    v1.mkdir(parents=True)
    _write_v1_assets(root)
    (v1 / "full.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-10-05T00:00:00Z",
                "n": 2,
                "oracle": "microsoft_word",
                "scorer_backend": "numpy",
                "track": "corpus/word:list",
                "stems": [_V1_STEM_A, _V1_STEM_B],
                "tools": {
                    "docxodus": {
                        "tool": "docxodus",
                        "version": "docxodus 14.2.0",
                        "n_scored": 2,
                        "per_doc": {_V1_STEM_A: 37.79113331316735, _V1_STEM_B: 88.0},
                        "convert_seconds": {_V1_STEM_A: 7.709, _V1_STEM_B: 9.5},
                        "failures": 0,
                        "generate_failures": [],
                        "aggregate": {"n": 2, "mean": 62.9, "median": 62.9, "min": 37.8, "max": 88.0},
                    },
                    "jubarte": {
                        "tool": "jubarte",
                        "version": "jubarte 0.14.0",
                        "n_scored": 2,
                        "per_doc": {_V1_STEM_A: 71.52493617107378, _V1_STEM_B: 95.5},
                        "convert_seconds": {_V1_STEM_A: 0.219, _V1_STEM_B: 0.3},
                        "failures": 0,
                        "generate_failures": [],
                        "aggregate": {"n": 2, "mean": 83.5, "median": 83.5, "min": 71.5, "max": 95.5},
                    },
                },
                "warnings": [],
            }
        ),
        encoding="utf-8",
    )
    (v1 / "soffice_full.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-10-05T00:00:00Z",
                "n": 2,
                "oracle": "microsoft_word",
                "scorer_backend": "numpy",
                "track": "corpus/word:list",
                "stems": [_V1_STEM_A, _V1_STEM_B],
                "tools": {
                    "soffice": {
                        "tool": "soffice",
                        "version": "LibreOffice 26.8.1.1",
                        "n_scored": 2,
                        "per_doc": {_V1_STEM_A: 39.35687355503542, _V1_STEM_B: 91.25},
                        "failures": 0,
                        "generate_failures": [],
                        "aggregate": {"n": 2, "mean": 65.3, "median": 65.3, "min": 39.4, "max": 91.3},
                    }
                },
                "warnings": [],
            }
        ),
        encoding="utf-8",
    )
    split = root / "results" / "redlines_0929_split"
    ar_assets = split / "assets" / "accept_all" / _AR_PAIR
    for engine in ("reference", "jubarte-rust"):
        d = ar_assets / engine
        d.mkdir(parents=True)
        (d / "page_001.webp").write_bytes(b"webp")
        (d / "pages.pdf").write_bytes(b"pdf")
    (split / "scores.jsonl").write_text(
        json.dumps(
            {
                "track": "redlines_0929_split",
                "tool": "jubarte-rust",
                "action": "accept_all",
                "pairs": 1,
                "scored": 1,
                "timestamp": "2026-09-29T00:00:00Z",
                "scorer_backend": "numpy",
                "itt_mean": 100.00000000000003,
                "itt_median": 100.00000000000003,
                "overall": {
                    "n": 1,
                    "mean": 100.00000000000003,
                    "median": 100.00000000000003,
                    "exact_100": 1,
                    "at_least_90": 1,
                    "below_50": 0,
                },
                "ink_jaccard": {"n": 1, "mean": 1.0, "median": 1.0},
                "text_boundary": {"n": 1, "mean": 1.0, "median": 1.0},
                "missing": [],
                "rows": {
                    _AR_PAIR: {
                        "average_score": 100.00000000000003,
                        "ink_jaccard": 1.0,
                        "text_boundary": 1.0,
                        "max_break_drift": 0,
                        "page_count": 1,
                        "page_count_oracle": 1,
                        "page_count_candidate": 1,
                        "page_count_mismatch": False,
                    }
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (split / "versions.json").write_text(
        json.dumps({"jubarte-rust": "jubarte 0.14.0"}), encoding="utf-8"
    )


def _expected_conversion_case(case_id: str, docxodus: float, jubarte: float, soffice: float,
                              docxodus_s: float, jubarte_s: float, stem: str) -> Case:
    return Case(
        kind="conversion",
        group="v1/clean",
        case=case_id,
        pages={
            e: [f"~/d2p_v1/v1/clean/{case_id}/{e}/page_001.webp"]
            for e in ("reference", "docxodus", "jubarte", "libreoffice")
        },
        page_counts={e: 1 for e in ("reference", "docxodus", "jubarte", "libreoffice")},
        scores={
            "docxodus": {"pixel": docxodus},
            "jubarte": {"pixel": jubarte},
            "libreoffice": {"pixel": soffice},
        },
        times={"docxodus": docxodus_s, "jubarte": jubarte_s},
        versions={
            "reference": "Word",
            "docxodus": "docxodus 14.2.0",
            "jubarte": "jubarte 0.14.0",
            "libreoffice": "LibreOffice 26.8.1.1",
        },
        dropped=[],
        reference_app="Microsoft Word",
        pdfs={
            e: f"~/d2p_v1/v1/clean/{case_id}/{e}/pages.pdf"
            for e in ("reference", "docxodus", "jubarte", "libreoffice")
        },
        shown=[1],
        stem=stem,
        set="v1",
    )


def _expected_ar_case() -> Case:
    return Case(
        kind="redline",
        group="ar/accept_all",
        case=_AR_PAIR,
        pages={
            e: [f"~/renew1030/ar/accept_all/{_AR_PAIR}/{e}/page_001.webp"]
            for e in ("reference", "jubarte-rust")
        },
        page_counts={"reference": 1, "jubarte-rust": 1},
        scores={
            "jubarte-rust": {"pixel": 100.00000000000003, "jaccard": 100.0, "text_boundary": 100.0}
        },
        times={},
        versions={"reference": "Microsoft Word for Mac accept/reject", "jubarte-rust": "jubarte 0.14.0"},
        dropped=[],
        reference_app="Microsoft Word for Mac",
        pdfs={
            e: f"~/renew1030/ar/accept_all/{_AR_PAIR}/{e}/pages.pdf"
            for e in ("reference", "jubarte-rust")
        },
        metric_diagnostics={
            "jubarte-rust": MetricDiagnostics(
                ref_pages=1, pages=1, scored_pages=1, max_break_drift=0
            )
        },
        shown=[1],
    )


def test_emit_builds_cases_from_the_synthetic_stores(tmp_path: Path) -> None:
    _write_cases_sources(tmp_path)
    _index, shards = cases_emit.emit(tmp_path)
    by_key = {(s.kind, s.group): s for s in shards}
    assert set(by_key) == {("conversion", "v1/clean"), ("redline", "ar/accept_all")}
    conv = by_key[("conversion", "v1/clean")].cases
    assert [c.case for c in conv] == ["00163e55a0", "0048ba31dd"]  # sorted by case id
    want_a = _expected_conversion_case(
        "00163e55a0", 37.79113331316735, 71.52493617107378, 39.35687355503542,
        7.709, 0.219, _V1_STEM_A,
    )
    want_b = _expected_conversion_case(
        "0048ba31dd", 88.0, 95.5, 91.25, 9.5, 0.3, _V1_STEM_B,
    )
    for want, got in zip((want_a, want_b), conv, strict=True):
        diffs = _diff_cases(want, got)
        assert not diffs, f"conversion case {got.case if got else want.case}: {diffs}"
    ar = by_key[("redline", "ar/accept_all")].cases
    assert len(ar) == 1
    diffs = _diff_cases(_expected_ar_case(), ar[0])
    assert not diffs, f"redline case {_AR_PAIR}: {diffs}"


def test_emit_index_registers_and_cross_checks_every_shard(tmp_path: Path) -> None:
    _write_cases_sources(tmp_path)
    index, shards = cases_emit.emit(tmp_path)
    assert index.assets_base == ASSETS_BASE
    assert index.repo  # producer repository identity
    assert index.version  # contract schema version
    assert index.generated.tzinfo is not None  # naive timestamps are rejected
    assert index.groups == [
        ShardRef(kind="conversion", group="v1/clean", count=2, path=shard_path("conversion", "v1/clean")),
        ShardRef(kind="redline", group="ar/accept_all", count=1, path=shard_path("redline", "ar/accept_all")),
    ]
    # the release layout the index promises: one shard file per group, its path
    # always shard_path() ("/" becomes "--", reversible where "_" is not)
    for ref in index.groups:
        assert ref.path == shard_path(ref.kind, ref.group)
    assert [g.path for g in index.groups] == [
        "cases/conversion/v1--clean.json",
        "cases/redline/ar--accept_all.json",
    ]
    # engines_from_cases: the union of every lane key the data uses, sorted,
    # each with a unique display label
    assert [e.key for e in index.engines] == sorted(
        {"reference", "docxodus", "jubarte", "libreoffice", "jubarte-rust"}
    )
    labels = {e.key: e.label for e in index.engines}
    assert len(set(labels.values())) == len(labels)
    assert labels["jubarte-rust"] == "jubarte (rust)"  # not "jubarte" — the conversion lane owns that label
    for shard in shards:  # registration, count and engine-key cross-checks pass
        index.validate_shard(shard)
    validate_bundle(index, shards)  # and the whole bundle cross-checks in one call


def test_emit_is_deterministic(tmp_path: Path) -> None:
    _write_cases_sources(tmp_path)
    i1, s1 = cases_emit.emit(tmp_path)
    i2, s2 = cases_emit.emit(tmp_path)
    assert _stable_dumps(i1) == _stable_dumps(i2)
    assert sorted(map(dumps_compact, s1)) == sorted(map(dumps_compact, s2))


def test_emit_matches_the_published_adapter_for_every_case() -> None:
    """The acceptance test (Plan 3b), split the way the stores allow today.

    Every family the stores emit on their own must equal the adapter's case byte
    for byte; the families the stores cannot derive are pinned here by name
    (ADAPTER_ONLY_FAMILIES) and reach the release only through the adapter-produced
    legacy_cases input — so the merged release still equals the published data for
    every case, with the adapter as the documented source for the rest."""
    site = _site_dir()
    if site is None:
        pytest.skip("no published gh-pages site on this machine (set NDB_SITE_DIR)")
    _, conv_shards = cases_adapter.from_published(site / "index.html")
    _, red_shards = cases_adapter.from_published(site / "redlines" / "index.html")
    adapter: dict[tuple[str, str, str], Case] = {}
    for shards in (conv_shards, red_shards):
        for shard in shards:
            for case in shard.cases:
                adapter[(case.kind, case.group, case.case)] = case
    # what the stores emit on their own, without the legacy input
    _, store_shards = cases_emit.from_stores(REPO)
    store_families = {(s.kind, s.group) for s in store_shards}
    assert store_families <= {
        (c.kind, c.group) for c in adapter.values()
    }, "the stores emit a family the published pages do not carry"
    have = {(c.kind, c.group, c.case): c for s in store_shards for c in s.cases}
    missing: list[str] = []
    diffs: list[str] = []
    for key, case in adapter.items():
        if (case.kind, case.group) not in store_families:
            continue  # adapter-only: covered through the legacy_cases input
        got = have.get(key)
        if got is None:
            missing.append("/".join(key))
            continue
        for d in _diff_cases(case, got):
            diffs.append(f"{key[0]}/{key[1]}/{key[2]}: {d}")
    report = "\n".join(missing[:10] + diffs[:40])
    assert not missing and not diffs, (
        f"{len(missing)} case(s) missing, {len(diffs)} field difference(s) "
        f"across {sorted(store_families)}:\n{report}"
    )
    adapter_only = {(c.kind, c.group) for c in adapter.values()} - store_families
    assert adapter_only == ADAPTER_ONLY_FAMILIES, (
        f"the adapter-only families changed: "
        f"+{sorted(adapter_only - ADAPTER_ONLY_FAMILIES)} "
        f"-{sorted(ADAPTER_ONLY_FAMILIES - adapter_only)}; update ADAPTER_ONLY_FAMILIES "
        "only together with the store coverage it documents"
    )
    # the merged release (what `scripts/release_views.py` writes) still covers every published
    # case exactly: emitted families from the stores, the rest from the legacy input
    if not cases_emit.legacy_path(REPO).is_file():
        pytest.skip("the adapter-produced legacy_cases input is absent; produce it once")
    _, merged = cases_emit.emit(REPO)
    merged_have = {(c.kind, c.group, c.case): c for s in merged for c in s.cases}
    missing = ["/".join(k) for k in adapter if k not in merged_have]
    diffs = [
        f"{k[0]}/{k[1]}/{k[2]}: {d}"
        for k, case in adapter.items()
        if k in merged_have
        for d in _diff_cases(case, merged_have[k])
    ]
    assert not missing and not diffs and len(merged_have) == len(adapter), (
        f"merged release: {len(missing)} missing, {len(diffs)} differing of "
        f"{len(adapter)} published cases\n" + "\n".join(missing[:10] + diffs[:40])
    )


# ---- the release-views flow writes results/release/ and --check covers it -------------


def _write_speed_sources(root: Path) -> None:
    """A minimal results/speed_10k (the shapes test_ledger_speed.py pins in
    detail) so the release-views flow has both release sources on the fake repo."""
    base = root / "results" / "speed_10k"
    per_pair = base / "redlines" / "per_pair"
    per_pair.mkdir(parents=True)
    (per_pair / "alpha.jsonl").write_text(
        "".join(
            json.dumps(r) + "\n"
            for r in (
                {"key": "p1", "category": "grid", "ok": True, "ms": 10.0, "out_bytes": 1},
                {"key": "p2", "category": "grid", "ok": True, "ms": 20.0, "out_bytes": 1},
                {"key": "p3", "category": "identity", "ok": True, "ms": 30.0, "out_bytes": 1},
                {"key": "p4", "category": "word_compare", "ok": True, "ms": 40.0, "out_bytes": 1},
            )
        ),
        encoding="utf-8",
    )
    (base / "redlines" / "NOTES.md").write_text(
        "# Redline speed run, notes\n\n## Heading\n\nA paragraph.\n\n- bullet one\n- bullet two\n",
        encoding="utf-8",
    )
    (base / "pairs_10k.csv").write_text(
        "key,base,next,category,base_bytes,next_bytes,base_state,next_state\n"
        "p1,a.docx,b.docx,grid,100,100,clean,clean\n"
        "p2,a.docx,b.docx,grid,200,200,clean,clean\n"
        "p3,a.docx,b.docx,identity,300,300,clean,clean\n"
        "p4,a.docx,b.docx,word_compare,400,400,clean,clean\n",
        encoding="utf-8",
    )


@pytest.fixture
def repo_with_release_sources(_ledger_repo: Path) -> Path:  # noqa: F811  fixture parameter
    """The test_ledger_build fake repo plus the synthetic cases and speed sources
    the release-views flow needs to write the release bundle."""
    _write_cases_sources(_ledger_repo)
    _write_speed_sources(_ledger_repo)
    return _ledger_repo


def test_release_views_write_the_release_files(repo_with_release_sources: Path) -> None:
    """ledger.build.run_release_views — the shared body scripts/release_views.py
    runs — is the only writer of results/release/ since `bench report` stopped
    writing it (#134)."""
    said: list[str] = []
    assert bd.run_release_views(repo_with_release_sources, echo=said.append) == 0
    index_path = repo_with_release_sources / "results" / "release" / "cases" / "index.json"
    assert index_path.is_file(), "the release views must write results/release/cases/index.json"
    index = CasesIndex.model_validate_json(index_path.read_text(encoding="utf-8"))
    shard_paths: list[Path] = []
    for ref in index.groups:
        shard_path = repo_with_release_sources / "results" / "release" / ref.path
        assert shard_path.is_file(), f"the release views must write {ref.path}"
        shard = CaseShard.model_validate_json(shard_path.read_text(encoding="utf-8"))
        index.validate_shard(shard)
        assert len(shard.cases) == ref.count
        shard_paths.append(shard_path)
    speed_path = repo_with_release_sources / "results" / "release" / "speed.json"
    assert speed_path.is_file(), "the release views must write results/release/speed.json"
    # the written bytes are the contract's compact serialization: parsing a file
    # and re-dumping it reproduces the file byte for byte
    for path in (index_path, speed_path, shard_paths[0]):
        text = path.read_text(encoding="utf-8")
        parsed = json.loads(text)
        assert json.dumps(parsed, sort_keys=True, separators=(",", ":"), ensure_ascii=False) == text.strip(), (
            f"{path.name} must be compact JSON with sorted keys"
        )


def test_release_views_check_covers_the_release_files(repo_with_release_sources: Path) -> None:
    said: list[str] = []
    assert bd.run_release_views(repo_with_release_sources, echo=said.append) == 0
    ok: list[str] = []
    assert bd.run_release_views(repo_with_release_sources, check=True, echo=ok.append) == 0
    index_path = repo_with_release_sources / "results" / "release" / "cases" / "index.json"
    shard_path = (
        repo_with_release_sources
        / "results"
        / "release"
        / "cases"
        / "redline"
        / "ar--accept_all.json"
    )
    assert shard_path.is_file(), f"the release views must write {shard_path.name} for --check to cover"
    for stale in (index_path, shard_path):
        original = stale.read_text(encoding="utf-8")
        stale.write_text('{"tampered":true}\n', encoding="utf-8")
        lines: list[str] = []
        assert bd.run_release_views(repo_with_release_sources, check=True, echo=lines.append) == 1, (
            f"--check must flag a tampered {stale.name}"
        )
        assert str(stale.relative_to(repo_with_release_sources)) in " ".join(lines)
        stale.write_text(original, encoding="utf-8")
    missing: list[str] = []
    assert bd.run_release_views(repo_with_release_sources, check=True, echo=missing.append) == 0  # restored: current again


def test_the_script_runs_the_shared_flow(repo_with_release_sources: Path) -> None:
    """scripts/release_views.py is a thin argparse front over the shared body;
    through `uv run` its PEP 723 block supplies the bench-ops the venv lacks."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "release_views", REPO / "scripts" / "release_views.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    assert module.main(["--root", str(repo_with_release_sources)]) == 0
    release = repo_with_release_sources / "results" / "release"
    assert (release / "cases" / "index.json").is_file()
    assert module.main(["--root", str(repo_with_release_sources), "--check"]) == 0

    speed = release / "speed.json"
    speed.write_text('{"tampered":true}\n', encoding="utf-8")
    assert module.main(["--root", str(repo_with_release_sources), "--check"]) == 1


def test_results_release_is_git_ignored() -> None:
    """results/release/ is not committed: the case shards are ~22 MB and HF is
    their record (Plan 3b). The repo's .gitignore must cover them."""
    for rel in (
        "results/release/cases/index.json",
        "results/release/cases/conversion/v1_clean.json",
        "results/release/speed.json",
    ):
        r = subprocess.run(
            ["git", "-C", str(REPO), "check-ignore", "-q", rel],
            capture_output=True,
            check=False,
            timeout=30,
        )
        assert r.returncode == 0, f"{rel} is not git-ignored"
