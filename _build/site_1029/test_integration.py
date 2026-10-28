"""Integration smoke using actual local PDFs, subprocesses and the pinned public API."""
import sys
from pathlib import Path
import pytest
H = Path(__file__).resolve().parent
sys.path.insert(0, str(H / 'scorer-source/src'))
from neurotic_docx_bench import content_cache, pipeline
import reference_process_1028
from reference_process_1028 import draw, metrics
reference_process_1028.METRICS_BIN = H / 'bin/page-metrics'


@pytest.mark.integration
def test_pinned_public_api_identity_and_upstream_binary(tmp_path):
    ref = Path.home() / 'temp/T/renew_1028/references/docxide/case1.pdf'
    assert content_cache.scorer_fingerprint() == '5e481477e2196f6b'
    result = pipeline.score_pdf_pair(ref, ref, tmp_path / 'pixel', dpi=144, cache=None)
    assert pipeline.overall_from_result(result) == pytest.approx(100)
    assert result['ssim'] == pytest.approx(1)
    assert result['page_count_oracle'] == result['page_count_candidate'] == 1
    draw(ref, tmp_path / 'reference', 150)
    values = metrics(ref, ref, tmp_path / 'reference', tmp_path / 'reference')
    assert values == {'jaccard': 100, 'ssim': 100, 'text_boundary': 100}
