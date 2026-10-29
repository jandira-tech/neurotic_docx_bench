"""Real local public API identity smoke, separated from deterministic unit tests."""
import os
import sys
from pathlib import Path
import pytest
H=Path(__file__).resolve().parent
os.environ['BENCH_DEVICE']='numpy'
sys.path.insert(0,str(H/'scorer-source/src'))
from neurotic_docx_bench import content_cache,pipeline
import reference_process_1028
reference_process_1028.METRICS_BIN=H/'bin/page-metrics'

@pytest.mark.integration
def test_public_scorer_api_and_upstream_identity(tmp_path):
    ref=Path('/Users/arthrod/temp/T/renew_1028/references/docxide/case1.pdf')
    assert content_cache.scorer_fingerprint()=='5e481477e2196f6b'
    result=pipeline.score_pdf_pair(ref,ref,tmp_path/'pixel',dpi=144,cache=None)
    assert pipeline.overall_from_result(result)==pytest.approx(100)
    assert result['page_count_candidate']==result['page_count_oracle']==1
    reference_process_1028.draw(ref,tmp_path/'upstream',150)
    assert reference_process_1028.metrics(ref,ref,tmp_path/'upstream',tmp_path/'upstream')=={'jaccard':100,'ssim':100,'text_boundary':100}
