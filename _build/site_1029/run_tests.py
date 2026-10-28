"""Run pure data-helper unit tests and report line AND branch coverage."""
import json
import shutil
import subprocess
import sys
from pathlib import Path
H = Path(__file__).resolve().parent
p = subprocess.run([sys.executable, '-m', 'pytest', '-c', str(H / 'pytest.ini'),
    '--rootdir=' + str(H), '--basetemp=' + str(H / 'integration-tmp'), str(H / 'test_common.py'), str(H / 'test_integration.py'), '--cov=common', '--cov-branch',
    '--cov-report=term-missing', '--cov-report=json:' + str(H / 'coverage.json'), '--cov-fail-under=90'], cwd=H)
t = json.loads((H / 'coverage.json').read_text())['totals']
print(f"Coverage: {100*t['covered_lines']/t['num_statements']:.2f}% lines, {100*t['covered_branches']/t['num_branches']:.2f}% branches", flush=True)
shutil.rmtree(H / 'integration-tmp', ignore_errors=True)
raise SystemExit(p.returncode)
