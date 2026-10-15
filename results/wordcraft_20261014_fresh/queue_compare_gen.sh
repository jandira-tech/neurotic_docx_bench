#!/bin/zsh
# Start comparison generation only after the conversion lanes finish (serial timing).
cd /Users/arthrod/temp/T/neurotic_docx_bench
while pgrep -f "generate_fresh.py convert" >/dev/null; do sleep 10; done
R=results/wordcraft_20261014_fresh
# purge the aborted concurrent start (04:09): its rows and outputs were timed alongside the convert lanes
.venv/bin/python - <<'PY'
import json
from pathlib import Path
p=Path('results/wordcraft_20261014_fresh/operations.jsonl')
keep=[l for l in p.read_text().splitlines() if json.loads(l)['task']!='compare']
p.write_text('\n'.join(keep)+'\n')
PY
rm -rf $R/compare/wordcraft $R/compare/jubarte-0.11.0 $R/compare/jubarte-0.12.0 $R/compare/docxodus-12.6.5
PREFREEZE=1 .venv/bin/python $R/generate_fresh.py compare wordcraft jubarte-0.11.0 jubarte-0.12.0 docxodus-12.6.5 > $R/generate_compare_prefreeze.out 2>&1
