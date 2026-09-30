"""Tests for the visual_* benchmark infrastructure (config, matcher, dispatch)."""

from pathlib import Path

import pytest

from neurotic_docx_bench.config import load_config


def test_visual_oracles_parsed_and_visual_redlines_is_what_word_prints():
    cfg = load_config("bench.yaml")
    assert "visual_rendering" in cfg.visual_oracles
    assert "visual_accepted_changes" in cfg.visual_oracles
    # a viewer is measured against Word's PDFs of the redlines the oracle holds
    assert cfg.visual_oracles["visual_redlines"] == cfg.oracle_roots["word"] / "tracking_without_comments/pdf"
    for name, p in cfg.visual_oracles.items():
        assert isinstance(p, Path), f"{name} oracle is not a Path"


def test_visual_oracles_missing_dir_raises(tmp_path):
    bad_yaml = tmp_path / "bench.yaml"
    bad_yaml.write_text(
        "source_of_truth: corpus/word_based/pdf_redlines_word\n"
        "visual_oracles:\n"
        "  visual_rendering: does/not/exist\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="visual_oracles.visual_rendering not found"):
        load_config(bad_yaml)
