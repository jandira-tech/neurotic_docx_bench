"""Run renewal tests with line/branch coverage and preserve pytest's exit status."""
import json
import os
import subprocess
import sys
from pathlib import Path
H=Path(__file__).resolve().parent
command=[sys.executable,'-m','pytest','-c',str(H/'pytest.ini'),'--rootdir='+str(H),
         '--basetemp='+str(H/'build/pytest-tmp'),str(H/'test_helpers.py'),str(H/'test_integration.py'),
         '--cov='+str(H),'--cov-branch','--cov-report=term-missing','--cov-report=json:'+str(H/'coverage.json')]
# Include the instrumented full build/asset-validation integration run when present.
if (H/'.coverage.build').is_file():
    from coverage import Coverage
    cov=Coverage(data_file=str(H/'.coverage'))
    cov.erase()
    cov.combine(data_paths=[str(H/'.coverage.build')],keep=True)
    cov.save()
    command.append('--cov-append')
p=subprocess.run(command,env={**os.environ,'COVERAGE_FILE':str(H/'.coverage')})
t=json.loads((H/'coverage.json').read_text())['totals']
print(f"Coverage: {100*t['covered_lines']/t['num_statements']:.2f}% lines, {100*t['covered_branches']/t['num_branches']:.2f}% branches",flush=True)
raise SystemExit(p.returncode)
