"""Write only preview/index.html from CURRENT site/index.html. No uploads."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from common import patch_html, split

H = Path(__file__).resolve().parent
SITE = H.parents[1]


def main() -> None:
    source = SITE / 'index.html'
    before = source.read_bytes()
    rows = json.loads((H / 'build/cases_d2p_jubarte.json').read_text())
    assert len(rows) == 1276, 'Partial previews are not a completed renewal'
    output = patch_html(before.decode(), rows).encode()
    dest = H / 'preview/index.html'
    dest.parent.mkdir(exist_ok=True)
    dest.write_bytes(output)
    assert source.read_bytes() == before, 'Source viewer changed during patching'
    evidence = {'source_sha256': hashlib.sha256(before).hexdigest(),
                'preview_sha256': hashlib.sha256(output).hexdigest(),
                'replaced': len(rows), 'cases': len(split(output.decode())[1])}
    (H / 'patch_evidence.json').write_text(json.dumps(evidence, indent=2) + '\n')
    print(json.dumps(evidence))


if __name__ == '__main__':
    main()
