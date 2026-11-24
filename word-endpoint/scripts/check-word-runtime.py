"""Verify actual Word jobs in an isolated instance from an interactive Windows session."""
from __future__ import annotations

import argparse
import io
import json
from pathlib import Path
import runpy
import statistics
import sys
import time
import uuid
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', default=f'python{sys.version_info.major}{sys.version_info.minor}')
    args = parser.parse_args()
    if not args.label.isalnum():
        parser.error('--label must contain only letters and digits')
    import pythoncom
    from tests.factory import make_docx, pack
    from word_endpoint.guard import prepare_docx, sanitize_output_docx
    from word_endpoint import worker

    output = ROOT / 'artifacts/runtime-verification' / f'{args.label}-{uuid.uuid4().hex}'
    output.mkdir(parents=True)
    report = {'python': sys.version, 'executable': sys.executable, 'artifacts': str(output),
              'checks': {}, 'median_ms': {}, 'production_service_changed': False}
    report_path = ROOT / 'reports' / f'word-runtime-{args.label}.json'
    report_path.parent.mkdir(exist_ok=True)
    word = None
    pythoncom.CoInitializeEx(pythoncom.COINIT_APARTMENTTHREADED)
    try:
        original = prepare_docx(make_docx(['The fee is 100 dollars.']))
        revised = prepare_docx(make_docx(['The fee is 250 dollars.']))
        comment_path = ROOT / 'artifacts/markup-demo/with-comments.docx'
        comments = prepare_docx(comment_path.read_bytes())
        with zipfile.ZipFile(comment_path) as archive:
            files = {name: archive.read(name) for name in archive.namelist()}
        files['word/document.xml'] = files['word/document.xml'].replace(b'1,000', b'1,250')
        comment_revision = prepare_docx(pack(files))
        fixture_text = runpy.run_path(str(ROOT / 'scripts/inspect-synthetic-pdfs.py'))['fixture_text']
        word = worker.start_word()
        report['word_version'] = str(word.Version)

        def job(name, *, document=None, pair=None, as_pdf=False):
            folder = output / name
            folder.mkdir()
            if document is not None:
                (folder / 'document.docx').write_bytes(document)
                worker.convert_document(word, folder)
            else:
                (folder / 'original.docx').write_bytes(pair[0])
                (folder / 'revised.docx').write_bytes(pair[1])
                worker.compare_documents(word, folder, as_pdf=as_pdf)
            return folder / ('output.pdf' if document is not None or as_pdf else 'output.docx')

        def check(name, condition):
            report['checks'][name] = bool(condition)
            if not condition:
                raise RuntimeError('Failed check: ' + name)

        comparison = sanitize_output_docx(job('redline', pair=(original, revised)).read_bytes())
        with zipfile.ZipFile(io.BytesIO(comparison)) as archive:
            root = ET.fromstring(archive.read('word/document.xml'))
        ns = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
        check('redline_has_insertions_and_deletions',
              next(root.iter(ns + 'ins'), None) is not None and
              next(root.iter(ns + 'del'), None) is not None)
        redline_pdf = job('redline-pdf', document=comparison)
        redline_text = fixture_text(redline_pdf)
        check('redline_pdf_keeps_old_and_new_amounts', all(v in redline_text for v in ('100', '250')))
        commented_pdf = job('commented-direct-pdf', pair=(comments, comment_revision), as_pdf=True)
        compact = ''.join(fixture_text(commented_pdf).split())
        check('pdf_retains_both_comment_texts', all(v in compact for v in (
            'ConfirmwhetherthefeeincludesVAT.', 'Considerreducingthepaymenttermto14days.')))
        timings = {'convert_pdf': [], 'compare_pdf': []}
        for trial in range(4):
            modes = ('convert_pdf', 'compare_pdf') if trial % 2 == 0 else ('compare_pdf', 'convert_pdf')
            for mode in modes:
                started = time.perf_counter()
                pdf = (job(f'{mode}-{trial}', document=original) if mode == 'convert_pdf' else
                       job(f'{mode}-{trial}', pair=(original, revised), as_pdf=True))
                elapsed = (time.perf_counter() - started) * 1000
                text = fixture_text(pdf)
                check(mode + '_text', all(v in text for v in (('100',) if mode == 'convert_pdf' else ('100', '250'))))
                if mode == 'compare_pdf':
                    check('direct_and_separate_pdf_text_match', text == redline_text)
                if trial:
                    timings[mode].append(round(elapsed, 1))
        report['runs_ms'] = timings
        report['median_ms'] = {name: statistics.median(values) for name, values in timings.items()}
        report['limitations'] = 'One isolated Word instance; one warmup and three measured runs per mode on small synthetic documents. This is not a production endpoint load test.'
    except Exception as error:
        report['error'] = type(error).__name__ + ': ' + str(error)
    finally:
        if word is not None:
            worker.quit_word(word)
        pythoncom.CoUninitialize()
        report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
    return 1 if 'error' in report else 0


if __name__ == '__main__':
    sys.exit(main())
