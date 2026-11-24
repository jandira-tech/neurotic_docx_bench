"""Read text from our simple Word PDF fixtures; not a general PDF validator."""
import json
from pathlib import Path
import re
import sys
import zlib

ROOT = Path(__file__).resolve().parents[1]


def fixture_text(path):
    data = path.read_bytes()
    objects = {int(ident): body for ident, body in re.findall(
        rb'(\d+)\s+\d+\s+obj\b(.*?)endobj', data, re.S)}

    def stream(body):
        found = re.search(rb'stream\r?\n(.*?)\r?\nendstream', body, re.S)
        if not found:
            return b''
        return zlib.decompress(found[1]) if b'/FlateDecode' in body else found[1]

    fonts = {}
    for name, ident in re.findall(rb'/(F\w+)\s+(\d+)\s+0\s+R', data):
        font = objects[int(ident)]
        reference = re.search(rb'/ToUnicode\s+(\d+)\s+0\s+R', font)
        mapping = {}
        width = 1
        if reference:
            cmap = stream(objects[int(reference[1])])
            for block in re.findall(rb'beginbfchar(.*?)endbfchar', cmap, re.S):
                for source, dest in re.findall(rb'<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>', block):
                    code = bytes.fromhex(source.decode())
                    width = len(code)
                    mapping[code] = bytes.fromhex(dest.decode()).decode('utf-16-be')
            for block in re.findall(rb'beginbfrange(.*?)endbfrange', cmap, re.S):
                for start, end, dest in re.findall(rb'<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>', block):
                    width = len(start) // 2
                    first, last, target = int(start, 16), int(end, 16), int(dest, 16)
                    if last - first > 65536:
                        raise ValueError('Fixture font range is too large.')
                    for code in range(first, last + 1):
                        mapping[code.to_bytes(width, 'big')] = chr(target + code - first)
        fonts[name] = (mapping, width)

    text = []
    for body in objects.values():
        if b'stream' not in body or b'/FontFile' in body:
            continue
        content = stream(body)
        for block in re.findall(rb'BT\b(.*?)\bET', content, re.S):
            selected = re.search(rb'/(F\w+)\s+[\d.]+\s+Tf', block)
            mapping, width = fonts.get(selected[1] if selected else b'', ({}, 1))
            for literal, hex_string in re.findall(rb'\(((?:\\.|[^\\)])*)\)|<([0-9A-Fa-f\s]+)>', block, re.S):
                if hex_string:
                    raw = bytes.fromhex(hex_string.decode())
                else:
                    escapes = {b'n': b'\n', b'r': b'\r', b't': b'\t', b'b': b'\b', b'f': b'\f'}
                    raw = re.sub(rb'\\([0-7]{1,3}|\r\n|\n|\r|.)',
                        lambda m: (bytes([int(m[1], 8)]) if m[1][:1] in b'01234567'
                            else b'' if m[1] in (b'\r\n', b'\n', b'\r') else escapes.get(m[1], m[1])), literal)
                if mapping:
                    text.append(''.join(mapping.get(raw[pos:pos + width], '\ufffd') for pos in range(0, len(raw), width)))
                else:
                    text.append(raw.decode('cp1252', errors='replace'))
    return ''.join(text)


def main():
    root = ROOT / 'artifacts' / 'performance-verification'
    files = {name: fixture_text(root / name) for name in (
        'direct-comparison.pdf', 'separate-comparison.pdf', 'direct-comparison-with-comments.pdf')}
    checks = {
        'direct_keeps_old_and_new_amounts': all(value in files['direct-comparison.pdf'] for value in ('100', '250')),
        'direct_and_separate_text_match': files['direct-comparison.pdf'] == files['separate-comparison.pdf'],
        'commented_pdf_keeps_vat_comment': 'ConfirmwhetherthefeeincludesVAT.' in ''.join(files['direct-comparison-with-comments.pdf'].split()),
        'commented_pdf_keeps_payment_comment': 'Considerreducingthepaymenttermto14days.' in ''.join(files['direct-comparison-with-comments.pdf'].split()),
    }
    report = {'checks': checks, 'text': files, 'limitations': 'Text checks on simple Word fixtures; no visual or general PDF validation.'}
    (ROOT / 'reports' / 'pdf-markup-verification.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
    return 0 if all(checks.values()) else 1


if __name__ == '__main__':
    sys.exit(main())
