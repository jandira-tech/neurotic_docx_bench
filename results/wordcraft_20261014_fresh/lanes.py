"""The lanes of this cohort, in report order. The first four of each task are the original run;
the rest were added on 2026-10-14 with the newest releases: the top three non-jubarte tools of
every past results table (RESULTS.md), plus wordcraft 0.7.0 and docxodus 13.0.0."""
from pathlib import Path
import csv,json
OUT=Path(__file__).resolve().parent
COMPARE=['wordcraft','wordcraft-0.7.0','jubarte-0.11.0','jubarte-0.12.0','docxodus-12.6.5','docxodus-13.0.0','folio-0.60.0','stemma-0.6.0','superdoc-2.20.0']
CONVERT=['wordcraft','wordcraft-0.7.0','jubarte-0.11.0','jubarte-0.12.0','soffice','office2pdf-0.8.1','pdfitdown-4.2.0','rdocx-0.16.0','docxide-pdf-0.18.4','libreoffice_convert_rust-0.1.0','pymupdf-pro-1.28.2']
LANES={'compare':COMPARE,'convert':CONVERT}
# PyMuPDF Pro runs unlicensed (first 3 pages only): measured only where the fresh Word oracle has <= 3 pages.
LE3_ONLY={'pymupdf-pro-1.28.2'}
# version pairs reported as transitions
TRANSITIONS=[('wordcraft','wordcraft-0.7.0'),('jubarte-0.11.0','jubarte-0.12.0'),('docxodus-12.6.5','docxodus-13.0.0')]
def le3_ids():
 cache=OUT/'convert'/'le3_ids.json'
 if cache.exists():return json.loads(cache.read_text())
 import pymupdf
 ids=[]
 for r in csv.DictReader(open(OUT/'conversions.csv')):
  with pymupdf.open(OUT/'convert'/'oracle'/(r['stem']+'.pdf')) as d:
   if d.page_count<=3:ids.append(r['stem'])
 cache.write_text(json.dumps(ids,indent=0)+'\n');return ids
def keys_for(kind,tool,manifest_keys):
 if tool in LE3_ONLY:
  s=set(le3_ids());return [k for k in manifest_keys if k in s]
 return list(manifest_keys)
