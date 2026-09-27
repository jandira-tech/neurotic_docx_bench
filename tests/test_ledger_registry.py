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
    doc = _minimal(
        run_names=["jubarte-final-lossless"],
        bench_vendors=["jubarte"],
        id="jubarte-lossless",
    )
    doc["tools"].append(
        {
            "id": "jubarte-ast",
            "vendor": "jubarte",
            "display": "jubarte (ast)",
            "role": "generator",
            "engine": "jubarte-final",
            "run_names": ["jubarte-final-native"],
            "bench_vendors": ["jubarte-ast"],
        }
    )
    r = reg.load_registry(_write(tmp_path, doc))
    # Old lines: vendor "jubarte" + run name "jubarte-final-native" must land on jubarte-ast.
    hit = r.resolve_bench(
        vendor="jubarte", run_name="jubarte-final-native", render="soffice"
    )
    assert hit is not None and hit.id == "jubarte-ast"
    # Vendor fallback when the run name is unknown.
    hit = r.resolve_bench(vendor="jubarte", run_name="something-else", render="soffice")
    assert hit is not None and hit.id == "jubarte-lossless"


def test_resolve_bench_playwright_falls_back_to_editor_entry(tmp_path: Path) -> None:
    doc = _minimal(id="docxodus", bench_vendors=["docxodus"], run_names=["docxodus"])
    doc["tools"].append(
        {
            "id": "docxodus-viewer",
            "vendor": "docxodus",
            "display": "docxodus (viewer)",
            "role": "editor",
            "engine": "react-docxodus-viewer",
            "run_names": ["docxodus-playwright-rendering"],
            "bench_vendors": ["docxodus"],
        }
    )
    r = reg.load_registry(_write(tmp_path, doc))
    hit = r.resolve_bench(
        vendor="docxodus", run_name="legacy-harness", render="playwright"
    )
    assert hit is not None and hit.id == "docxodus-viewer"
    hit = r.resolve_bench(
        vendor="docxodus", run_name="legacy-harness", render="soffice"
    )
    assert hit is not None and hit.id == "docxodus"


def test_resolve_speed_strips_inproc_suffix(tmp_path: Path) -> None:
    doc = _minimal(
        id="jubarte-rust", speed_tools=["jubarte-rust"], bench_vendors=["jubarte-rust"]
    )
    r = reg.load_registry(_write(tmp_path, doc))
    entry, inproc = r.resolve_speed("jubarte-rust-inproc")
    assert entry is not None and entry.id == "jubarte-rust" and inproc is True
    entry, inproc = r.resolve_speed("jubarte-rust")
    assert entry is not None and inproc is False
    assert r.resolve_speed("nobody") == (None, False)


def test_resolve_converter(tmp_path: Path) -> None:
    doc = _minimal(
        id="pdfitdown",
        role="converter",
        engine="office2pdf",
        converter_tools=["pdfitdown"],
    )
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
        if r.resolve_bench(
            vendor=run.get("vendor") or run["name"],
            run_name=run["name"],
            render=run.get("render", "soffice"),
        )
        is None
    ]
    assert missing == [], f"bench.yaml runs with no registry entry: {missing}"


@pytest.mark.skipif(not REGISTRY_PATH.is_file(), reason="bench.registry.yaml absent")
def test_committed_registry_marks_author_tools() -> None:
    r = reg.load_registry(REGISTRY_PATH)
    affiliated = sorted(t.id for t in r.tools if t.affiliated)
    assert {
        "jubarte-lossless",
        "jubarte-ast",
        "jubarte-rust",
        "jubarte-wasm",
        "jubarte-pdf",
    } <= set(affiliated)
    assert r.by_id("docxodus").affiliated is False
