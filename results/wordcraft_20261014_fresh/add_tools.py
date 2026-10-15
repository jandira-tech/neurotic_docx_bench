"""Record the tools added on 2026-10-14 (newest releases) in tools.json: path, version, sha256, source."""
from pathlib import Path
import json,hashlib,subprocess
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1];B=OUT/'bin'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def npmv(root,pkg):return json.loads((root/pkg/'package.json').read_text())['version']
t=json.loads((OUT/'tools.json').read_text())
wc=B/'wordcraft-0.7.0/wordcraft-cli-0.7.0-macos-universal/wordcraft-cli'
t['wordcraft-0.7.0']={'path':str(wc),'sha256':sha(wc),'version':subprocess.run([wc,'--version'],capture_output=True,text=True).stdout.strip(),'source':'GitHub release storytold/wordcraft v0.7.0, wordcraft-cli-0.7.0-macos-universal.zip, sha256 checked against SHA256SUMS.txt','zip_sha256':sha(B/'wordcraft-0.7.0/wordcraft-cli-0.7.0-macos-universal.zip')}
d=B/'npm/docxodus-13.0.0/node_modules';t['docxodus-13.0.0']={'package_version':npmv(d,'docxodus'),'node_modules':str(d),'generator':'one_redline.ts docxodus (bench loadEngine, DOCXODUS_NODE_MODULES)','source':'npm docxodus@13.0.0'}
f=B/'npm/folio-0.60.0/node_modules';t['folio-0.60.0']={'package_version':npmv(f,'@stll/folio-core'),'node_modules':str(f),'generator':'one_redline.ts folio (bench loadEngine, FOLIO_MODULE_ROOT)','source':'npm @stll/folio-core@0.60.0'}
s=ROOT/'src/neurotic_docx_bench/utils/stemma/stemma';t['stemma-0.5.0']={'path':str(s),'sha256':sha(s),'version':subprocess.run([s,'--version'],capture_output=True,text=True).stdout.strip(),'engine_commit':(s.parent/'ENGINE_COMMIT.txt').read_text().strip(),'generator':'one_redline.ts stemma (bench loadEngine)','source':'stemma-cli 0.5.0 (newest on crates.io)'}
py=B/'superdoc-venv/bin/python';t['superdoc-2.20.0']={'package_version':subprocess.run([py,'-c','import importlib.metadata as m;print(m.version("superdoc-sdk"))'],capture_output=True,text=True).stdout.strip(),'python':str(py),'generator':'superdoc_one.py (bench superdoc_gen.generate_one)','source':'PyPI superdoc-sdk==2.20.0, isolated venv'}
s6=B/'cargo/stemma-cli-0.6.0/bin/stemma';t['stemma-0.6.0']={'path':str(s6),'sha256':sha(s6),'version':subprocess.run([s6,'--version'],capture_output=True,text=True).stdout.strip(),'git_tag':'v0.6.0','git_commit':'ad1e70deac0a828d5162ac3b3f2186c2bb0c075e','generator':'one_redline.ts stemma (bench loadEngine)','source':'cargo install --locked --git https://github.com/stemma-sh/stemma --tag v0.6.0 stemma-cli (newest release; crates.io stops at 0.5.0, and the GitHub release ships only stemma-mcp binaries)'}
pm=B/'pymupdf-pro-convert';t['pymupdf-pro-1.28.2']={'path':str(pm),'version':subprocess.run([pm,'--version'],capture_output=True,text=True).stdout.strip(),'source':'PyPI pymupdfpro==1.28.2 (newest), isolated venv; unlicensed: first 3 pages only, so measured on conversions whose Word oracle has at most 3 pages'}
for name,crate,binname in [('office2pdf-0.8.1','office2pdf-cli','office2pdf'),('pdfitdown-4.2.0','pdfitdown','pdfitdown'),('rdocx-0.16.0','rdocx-cli','rdocx'),('docxide-pdf-0.18.4','docxide-pdf','docxide-pdf'),('libreoffice_convert_rust-0.1.0','libreoffice_convert_rust','libreoffice_convert')]:
 v=name.rsplit('-',1)[1];p=B/'cargo'/f'{crate}-{v}'/'bin'/binname
 if p.exists():t[name]={'path':str(p),'sha256':sha(p),'version':f'{crate} {v}','source':f'cargo install --locked {crate} --version {v} (newest on crates.io)'}
(OUT/'tools.json').write_text(json.dumps(t,indent=2)+'\n');print(sorted(t))
