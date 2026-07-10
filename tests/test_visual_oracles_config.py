"""Tests for the visual_* benchmark infrastructure (config, matcher, dispatch)."""

from pathlib import Path

import pytest

from neurotic_docx_bench.config import load_config


def test_visual_oracles_parsed_and_visual_redlines_defaults_to_source_of_truth():
    cfg = load_config("bench.yaml")
    assert "visual_rendering" in cfg.visual_oracles
    assert "visual_accepted_changes" in cfg.visual_oracles
    # visual_redlines always present, defaults to source_of_truth when omitted
    assert cfg.visual_oracles["visual_redlines"] == cfg.source_of_truth
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
