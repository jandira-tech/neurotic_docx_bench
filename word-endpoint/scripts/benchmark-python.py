"""Compare an isolated candidate Python with the current DOCX guard runtime."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import importlib
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def worker(samples: int, fixture: Path | None) -> dict:
    import purexml
    from tests.factory import make_docx, pack, standard_files
    from word_endpoint.guard import GuardError, validate_docx
    from xml.parsers import expat

    gil = getattr(sys, '_is_gil_enabled', lambda: True)
    document = (fixture.read_bytes() if fixture is not None else
                make_docx([f'Clause {i}: the parties agree to these synthetic terms.'
                           for i in range(1024)]))
    validate_docx(document)
    for extra in ('<w:p><w:fldSimple w:instr="DDEAUTO synthetic"/></w:p>',
                  '<w:p><w:r><w:instrText>INCLUDETEXT synthetic</w:instrText></w:r></w:p>'):
        try:
            validate_docx(pack(standard_files(['Hello'], extra)))
        except GuardError as error:
            assert error.code == 'active_content'
        else:
            raise RuntimeError('Candidate missed a forbidden Word field')
    result = {'python': sys.version, 'executable': sys.executable,
              'purexml': purexml.__version__, 'expat': expat.EXPAT_VERSION,
              'gil_during_guard_benchmark': gil(), 'samples': samples,
              'documents_per_batch': 8, 'compressed_docx_bytes': len(document),
              'docx_sha256': hashlib.sha256(document).hexdigest()}

    def validate(_):
        validate_docx(document)

    with ThreadPoolExecutor(max_workers=4) as pool:
        def sequential():
            for i in range(8):
                validate(i)

        def threaded():
            list(pool.map(validate, range(8)))

        measurements = {'sequential': [], 'four_threads': []}
        functions = {'sequential': sequential, 'four_threads': threaded}
        for function in functions.values():
            function()
            function()
        for index in range(samples):
            order = list(functions)
            if index % 2:
                order.reverse()
            for name in order:
                started = time.perf_counter()
                functions[name]()
                measurements[name].append((time.perf_counter() - started) * 1000)
        result['validation_batches'] = {
            name: {'median_ms': round(statistics.median(values), 3),
                   'samples_ms': [round(v, 3) for v in values]}
            for name, values in measurements.items()}
    # Imports only: no Word instances are started and no native 3.12 DLLs
    # are shared with the candidate. Missing support is recorded explicitly.
    native = {}
    for name in ('pythoncom', 'pywintypes', 'win32com.client', 'win32gui', 'win32process'):
        try:
            importlib.import_module(name)
        except Exception as error:
            native[name] = {'imported': False, 'error': type(error).__name__ + ': ' + str(error)}
        else:
            native[name] = {'imported': True}
    result['word_native_imports'] = native
    result['gil_after_native_imports'] = gil()
    result['word_automation_tested'] = False
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path)
    parser.add_argument('--control', type=Path, help='Optional GIL-enabled comparison interpreter')
    parser.add_argument('--samples', type=int, default=11)
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--fixture', type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not 3 <= args.samples <= 101:
        parser.error('--samples must be between 3 and 101')
    if args.worker:
        print(json.dumps(worker(args.samples, args.fixture)))
        return
    if args.candidate is None or not args.candidate.is_file():
        parser.error('--candidate must identify an installed candidate python.exe')
    if args.control is not None and not args.control.is_file():
        parser.error('--control must identify an installed control python.exe')
    from tests.factory import make_docx
    fixture = ROOT / '.tools/runtime-benchmark.docx'
    fixture.write_bytes(make_docx([f'Clause {i}: the parties agree to these synthetic terms.'
                                  for i in range(1024)]))
    report = {'baseline': None, 'candidate': None}
    runtimes = [('baseline', Path(sys.executable)), ('candidate', args.candidate)]
    if args.control is not None:
        runtimes.append(('control', args.control))
    for name, executable in runtimes:
        completed = subprocess.run([str(executable), '-B', str(Path(__file__).resolve()),
                                    '--worker', '--samples', str(args.samples),
                                    '--fixture', str(fixture)],
                                   cwd=ROOT, capture_output=True, text=True,
                                   encoding='utf-8', errors='replace', timeout=180)
        if completed.returncode:
            raise RuntimeError(f'{name} benchmark failed: {completed.stderr}')
        report[name] = json.loads(completed.stdout)
        if completed.stderr.strip():
            report[name]['runtime_warnings'] = completed.stderr.strip()
    if len({report[name]['docx_sha256'] for name, _ in runtimes}) != 1:
        raise RuntimeError('Benchmark runtimes used different fixtures')
    report['candidate_time_saved_percent'] = {}
    for mode in ('sequential', 'four_threads'):
        baseline = report['baseline']['validation_batches'][mode]['median_ms']
        candidate = report['candidate']['validation_batches'][mode]['median_ms']
        report['candidate_time_saved_percent'][mode] = round((1 - candidate / baseline) * 100, 1)
    if args.control is not None:
        report['candidate_time_saved_vs_control_percent'] = {}
        for mode in ('sequential', 'four_threads'):
            control = report['control']['validation_batches'][mode]['median_ms']
            candidate = report['candidate']['validation_batches'][mode]['median_ms']
            report['candidate_time_saved_vs_control_percent'][mode] = round((1 - candidate / control) * 100, 1)
    report['limitations'] = ('Synthetic DOCX validation only, two warmups per mode; each runtime '
        'runs in a separate process. Shared host load can affect results. Native imports do not '
        'prove Word comparison/PDF compatibility. No production restart or endpoint speed claim.')
    destination = ROOT / 'reports/python-runtime-benchmark.json'
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
