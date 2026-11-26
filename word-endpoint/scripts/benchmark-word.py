"""Compare the two-request workflow with direct comparison PDF export."""
import json
from pathlib import Path
import statistics
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tests.factory import encode_form, pack, standard_files
from word_endpoint.config import load_settings


def main():
    settings = load_settings()
    out = ROOT / 'artifacts' / 'performance-verification'
    out.mkdir(parents=True, exist_ok=True)
    report = ROOT / 'reports' / 'word-benchmark.json'

    def call(path, fields):
        content_type, payload = encode_form(fields)
        request = urllib.request.Request(f'http://127.0.0.1:{settings.port}' + path,
            data=payload, headers={'Authorization': 'Bearer ' + settings.token,
                                  'Content-Type': content_type}, method='POST')
        with urllib.request.urlopen(request, timeout=310) as response:
            return response.read()

    samples = []
    for amount in ('100', '250'):
        files = standard_files([f'The monthly service fee is {amount} dollars.',
            'Invoices are payable within 30 days.',
            'Both parties must keep business information confidential.'])
        samples.append(pack(files))
    fields = [('original', 'original.docx', samples[0]), ('revised', 'revised.docx', samples[1])]
    timings = {'separate': [], 'direct': []}
    for trial in range(4):
        # Alternate order and discard the first pair as warmup.
        for mode in (('separate', 'direct') if trial % 2 == 0 else ('direct', 'separate')):
            started = time.perf_counter()
            if mode == 'direct':
                pdf = call('/v1/compare-pdf', fields)
            else:
                docx = call('/v1/compare', fields)
                if not docx.startswith(b'PK'):
                    raise RuntimeError('Comparison did not return a DOCX.')
                pdf = call('/v1/convert', [('document', 'comparison.docx', docx)])
            elapsed = round((time.perf_counter() - started) * 1000, 1)
            if not pdf.startswith(b'%PDF-') or len(pdf) < 500:
                raise RuntimeError('Word did not return a PDF.')
            (out / f'benchmark-{mode}.pdf').write_bytes(pdf)
            if trial:
                timings[mode].append(elapsed)
            print(f'{mode}: {elapsed} ms' + (' (warmup)' if not trial else ''), flush=True)
    medians = {mode: statistics.median(values) for mode, values in timings.items()}
    result = {'runs_ms': timings, 'median_ms': medians,
              'direct_time_saved_percent': round(100 * (1 - medians['direct'] / medians['separate']), 1),
              'limitations': 'Small synthetic documents, three measured pairs; tests combined workflow, not proofing alone.'}
    report.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
