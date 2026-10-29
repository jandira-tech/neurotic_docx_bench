"""Build preview copies; every source viewer is read-only."""
import hashlib
import json
import re
from pathlib import Path
from common import merge_ar, patch_html, split

H=Path(__file__).resolve().parent
SITE=H.parents[1]

def main():
    source=SITE/'redlines/index.html'
    before=source.read_bytes()
    rows=json.loads((H/'build/cases.json').read_text())
    replacements=[r for r in rows if not r['group'].startswith('ar/')]
    ar=[r for r in rows if r['group'].startswith('ar/')]
    assert len(replacements)==2800 and len(ar)==3200,'Refuse partial preview'
    assert len({(r['group'],r['case']) for r in replacements})==1400
    engines=json.loads(re.search(r'const ENGINES = (.*?);\n',before.decode()).group(1))
    added=merge_ar(ar,[k for k,_ in engines])
    assert len(added)==800
    output=patch_html(before.decode(),replacements,added).encode()
    dest=H/'preview/redlines/index.html'
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_bytes(output)
    index=(SITE/'index.html').read_bytes()
    (H/'preview/index.html').write_bytes(index)
    assert source.read_bytes()==before and (SITE/'index.html').read_bytes()==index
    evidence={'source_sha256':hashlib.sha256(before).hexdigest(),
              'preview_sha256':hashlib.sha256(output).hexdigest(),
              'replaced_cases':1400,'replaced_columns':2800,'added_ar_cases':len(added),
              'total_cases':len(split(output.decode())[1]),
              'outside_DATA_unchanged':split(before.decode())[::2]==split(output.decode())[::2]}
    (H/'patch_evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print(json.dumps(evidence))

if __name__=='__main__':main()
