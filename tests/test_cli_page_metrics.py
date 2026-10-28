"""Standalone accept/roundtrip reports retain the page metrics from scored rows."""
from neurotic_docx_bench import cli


def test_accepted_report_carries_page_metrics_beside_pixel_scores():
    rows = {"a": {"ink_jaccard": 0.4, "ssim": 0.8, "text_boundary": None}}
    md, data = cli._accepted_report("tool", {"a": 60.0}, {"a": 90.0}, [], accepted_per_doc=rows)
    assert data["per_doc"]["a"] == {"redline_score": 60.0, "accepted_score": 90.0, "delta": 30.0}
    assert data["page_metrics"] == {"a": {"jaccard": 0.4, "ssim": 0.8, "text_boundary": None}}
    assert data["page_metrics_mean"] == data["page_metrics"]["a"]
    assert "Jaccard" in md and "SSIM" in md and "Text boundary" in md
    assert "0.400000" in md and "0.800000" in md


def test_roundtrip_report_carries_page_metrics_beside_pixel_scores():
    rows = {"a": {"ink_jaccard": 0.4, "ssim": 0.8, "text_boundary": None}}
    data = cli._roundtrip_report("tool", {"a": 90.0}, rows)
    assert data["scores"] == {"a": 90.0}
    assert data["page_metrics"] == {"a": {"jaccard": 0.4, "ssim": 0.8, "text_boundary": None}}
    assert data["page_metrics_mean"] == data["page_metrics"]["a"]
