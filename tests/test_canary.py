"""Renderer fingerprint canary (PR5): abort before scoring when the rendering
environment drifted (LibreOffice build, fonts, dpi) instead of producing subtly
shifted scores across the whole corpus."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from neurotic_docx_bench import canary
from helpers import requires_soffice


def test_parse_soffice_version() -> None:
    out = "LibreOffice 26.2.4.2 0229ac93fcf0d7cbc6376066c6f35021cef002dc\n"
    assert canary.parse_soffice_version(out) == "26.2.4.2"
    assert canary.parse_soffice_version("garbage") is None


def test_verify_pure_logic(tmp_path: Path) -> None:
    expected_path = tmp_path / "canary_expected.json"
    expected_path.write_text(json.dumps({
        "docx": "docx_source/x.docx",
        "expected": {"26.2.4.2": {"dpi": 144, "page1_sha256": "abc"}},
    }))
    spec = canary.load_canary_spec(expected_path)
    assert spec is not None
    assert canary.expected_hash(spec, "26.2.4.2", 144) == "abc"
    # Unknown LO version → None (caller warns + continues; CI has a different LO).
    assert canary.expected_hash(spec, "99.9.9.9", 144) is None
    # Known version but different dpi → None (not comparable, not a mismatch).
    assert canary.expected_hash(spec, "26.2.4.2", 300) is None


@requires_soffice
def test_canary_roundtrip_and_tamper(tmp_path: Path) -> None:
    docx = canary.DEFAULT_CANARY_DOCX
    assert docx.is_file(), "canary docx must exist in the corpus"
    version = canary.current_soffice_version()
    assert version is not None

    h1 = canary.render_canary_hash(docx, tmp_path / "w1", dpi=144)
    assert len(h1) == 64
    # Determinism: same environment, same hash.
    h2 = canary.render_canary_hash(docx, tmp_path / "w2", dpi=144)
    assert h1 == h2

    expected_path = tmp_path / "canary_expected.json"
    canary.write_canary_spec(expected_path, docx, {version: {"dpi": 144, "page1_sha256": h1}})
    outcome = canary.check(expected_path, tmp_path / "w3", dpi=144)
    assert outcome.status == "ok"

    # Tamper with the expectation → mismatch with both hashes in the message.
    canary.write_canary_spec(
        expected_path, docx, {version: {"dpi": 144, "page1_sha256": "0" * 64}},
    )
    outcome = canary.check(expected_path, tmp_path / "w4", dpi=144)
    assert outcome.status == "mismatch"
    assert h1 in outcome.detail

    # No baseline for this LO version → no-baseline (warn, not fail). Fresh spec
    # path: write_canary_spec MERGES versions (multiple LO baselines coexist), so
    # reusing expected_path would keep the current version's entry around.
    other_spec = tmp_path / "other_canary.json"
    canary.write_canary_spec(
        other_spec, docx, {"1.0.0.0": {"dpi": 144, "page1_sha256": h1}},
    )
    outcome = canary.check(other_spec, tmp_path / "w5", dpi=144)
    assert outcome.status == "no-baseline"


def test_check_missing_spec_is_no_baseline(tmp_path: Path) -> None:
    outcome = canary.check(tmp_path / "nope.json", tmp_path / "w", dpi=144)
    assert outcome.status == "no-baseline"


def test_check_malformed_spec_is_invalid_spec(tmp_path: Path) -> None:
    path = tmp_path / "canary_expected.json"
    path.write_text("{not-json")
    outcome = canary.check(path, tmp_path / "w", dpi=144)
    assert outcome.status == "invalid-spec"
    assert "malformed" in outcome.detail


def test_check_non_utf8_spec_is_invalid_spec(tmp_path: Path) -> None:
    path = tmp_path / "canary_expected.json"
    path.write_bytes(b'{"docx": "x.docx"}\xff')
    outcome = canary.check(path, tmp_path / "w", dpi=144)
    assert outcome.status == "invalid-spec"


def test_parse_soffice_version_from_stderr_style_banner() -> None:
    # Some LO builds put the banner on stderr; we concatenate both streams.
    assert canary.parse_soffice_version(
        "\nLibreOffice 26.2.4.2 0229ac93fcf0d7cbc6376066c6f35021cef002dc\n",
    ) == "26.2.4.2"
