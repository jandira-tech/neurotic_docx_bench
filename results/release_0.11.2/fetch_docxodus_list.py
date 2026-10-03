"""Fetch named docxodus Word-rendered redline PDFs from the results dataset into the lane."""
import os, sys
from huggingface_hub import hf_hub_download
dst='results/redlines_0929_full/docxodus/pdf_by_word'; os.makedirs(dst, exist_ok=True)
names=[l.strip() for l in open(sys.argv[1]) if l.strip()]
missing=0; done=0
for name in names:
    if os.path.exists(os.path.join(dst,name)): done+=1; continue
    try:
        p=hf_hub_download('arthrod/neurotic_docx_bench', f'outputs/redlines_0929_full/docxodus/pdf_by_word/{name}', repo_type='dataset', local_dir='results/release_0.11.2/hub_tmp')
        os.replace(p, os.path.join(dst,name)); done+=1
    except Exception as e:
        missing+=1; print('MISSING', name, type(e).__name__, file=sys.stderr)
print('fetched/present', done, 'missing', missing)
