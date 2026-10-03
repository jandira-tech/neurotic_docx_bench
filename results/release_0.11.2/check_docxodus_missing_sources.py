"""For the pairs whose Docxodus redline had no Word PDF: are the two source documents sound?

Per pair: the validator's error count on base, next, jubarte's redline and Docxodus's redline
(error kinds for the last), whether the corpus holds Word's own PDF of base and next, and
whether Word exported jubarte's and Docxodus's redline. Run from the bench root.
"""
import collections
import csv
import subprocess
from pathlib import Path

V = Path.home() / 'temp/T/jubarte-redlines/tools/validate-docx/bin/Release/net8.0/validate-docx'
R = Path('results/redlines_0929_full')
W = Path('corpus/word')


def errors(path: Path) -> tuple[int | str, collections.Counter]:
    if not path.is_file():
        return 'absent', collections.Counter()
    out = subprocess.run([str(V), str(path)], capture_output=True, text=True)
    kinds = collections.Counter(line.split('\t')[1] for line in out.stdout.splitlines() if '\t' in line)
    return (sum(kinds.values()) if out.returncode == 0 else f'exit {out.returncode}'), kinds


rows = list(csv.DictReader(open('results/release_0.11.2_evidence/gen_pairs_docxodus_missing.csv')))
print(f'{len(rows)} pairs')
for r in rows:
    k = r['key']
    base, nxt = W / f'{r["base"]}.docx', W / f'{r["next"]}.docx'
    word_pdf = [(W / f'{r[c]}.pdf'.replace('/docx/', '/pdf/')).is_file() for c in ('base', 'next')]
    jub, dox = R / 'jubarte-0.11.2/docx' / f'{k}_jubarte-0.11.2.docx', R / 'docxodus/docx' / f'{k}_docxodus.docx'
    eb, en, ej, (ed, kinds) = errors(base)[0], errors(nxt)[0], errors(jub)[0], errors(dox)
    print(f'{k[:58]:58} base {eb!s:>4} next {en!s:>4} wordpdf {word_pdf[0]:d}{word_pdf[1]:d} | jubarte err {ej!s:>3} pdf '
          f'{(R / "jubarte-0.11.2/pdf_by_word" / f"{k}_jubarte-0.11.2.pdf").is_file():d} | docxodus err {ed!s:>6} pdf '
          f'{(R / "docxodus/pdf_by_word" / f"{k}_docxodus.pdf").is_file():d} {dict(kinds.most_common(3))}')
