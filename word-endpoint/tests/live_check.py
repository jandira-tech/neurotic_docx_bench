"""Exercise the running service against the local Word installation."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
import zipfile
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests.factory import encode_form, make_docx  # noqa: E402


def winword_pids() -> set[int]:
    output = subprocess.check_output(
        ["tasklist", "/FI", "IMAGENAME eq WINWORD.EXE", "/FO", "CSV", "/NH"],
        text=True,
        errors="replace",
    )
    pids = set()
    for line in output.splitlines():
        if "WINWORD.EXE" not in line.upper():
            continue
        parts = line.replace('"', "").split(",")
        if len(parts) > 1 and parts[1].strip().isdigit():
            pids.add(int(parts[1].strip()))
    return pids


def call(base: str, path: str, payload: bytes, content_type: str, token: str | None):
    headers = {"Content-Type": content_type}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(base + path, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            return response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as exc:
        with exc:
            return exc.code, dict(exc.headers), exc.read()


def leaks(data: bytes) -> list[str]:
    found = []
    needles = {
        "work-path": b"word-endpoint",
        "profile": b"C:\\Users\\",
        "profile-slash": b"C:/Users/",
    }
    lowered = data.lower()
    for label, needle in needles.items():
        if needle.lower() in lowered or needle.decode("ascii", "ignore").encode("utf-16le") in data:
            found.append(label)
    return found


def main() -> int:
    from word_endpoint.config import load_settings
    settings = load_settings()
    base = os.environ.get("WORD_BASE_URL", f"http://127.0.0.1:{settings.port}").rstrip("/")
    token = settings.token
    failures = []
    before = winword_pids()

    def check(name: str, ok: bool, detail: str = "") -> None:
        print(("PASS " if ok else "FAIL ") + name + (f" {detail}" if detail else ""))
        if not ok:
            failures.append(name)

    health = urllib.request.urlopen(base + "/ready", timeout=10)
    check("health", health.status == 200 and b'"ok"' in health.read())

    content_type, payload = encode_form([("document", "a.docx", make_docx(["Hello from the converter."]))])
    status, _, body = call(base, "/v1/convert", payload, content_type, None)
    check("convert rejects missing token", status == 401, str(status))

    status, headers, body = call(base, "/v1/convert", payload, content_type, token)
    check("convert returns pdf", status == 200 and body.startswith(b"%PDF-") and len(body) > 500, str(status))
    check("pdf has no local path", leaks(body) == [], ",".join(leaks(body)))
    check("pdf content type", "pdf" in headers.get("Content-Type", "").lower())

    original = make_docx(["The fee is 100 dollars."])
    revised = make_docx(["The fee is 250 dollars."])
    artifacts = ROOT / 'artifacts' / 'performance-verification'
    artifacts.mkdir(parents=True, exist_ok=True)
    content_type, payload = encode_form(
        [("original", "original.docx", original), ("revised", "revised.docx", revised)]
    )
    status, _, body = call(base, "/v1/compare", payload, content_type, token)
    compared = status == 200 and body.startswith(b"PK")
    check("compare returns docx", compared, str(status))
    status, _, combined_pdf = call(base, "/v1/compare-pdf", payload, content_type, token)
    check("comparison exports directly to pdf", status == 200 and combined_pdf.startswith(b"%PDF-") and len(combined_pdf) > 500, str(status))
    check("direct comparison pdf has no local path", leaks(combined_pdf) == [], ",".join(leaks(combined_pdf)))
    if combined_pdf.startswith(b'%PDF-'):
        (artifacts / 'direct-comparison.pdf').write_bytes(combined_pdf)
    if compared:
        with zipfile.ZipFile(BytesIO(body)) as archive:
            xml = archive.read("word/document.xml")
        check("compare contains a revision", b"w:ins" in xml or b"w:del" in xml)
        check("compare keeps both amounts", b"100" in xml and b"250" in xml)
        check("comparison has no local path", leaks(body) == [], ",".join(leaks(body)))
        (artifacts / 'comparison.docx').write_bytes(body)
        content_type, payload = encode_form([("document", "redline.docx", body)])
        status, _, pdf = call(base, "/v1/convert", payload, content_type, token)
        check("redline exports to pdf", status == 200 and pdf.startswith(b"%PDF-") and len(pdf) > 500, str(status))
        if pdf.startswith(b'%PDF-'):
            (artifacts / 'separate-comparison.pdf').write_bytes(pdf)

    # Preserve the two existing synthetic comments while changing the fee.
    comments_sample = ROOT / 'artifacts' / 'markup-demo' / 'with-comments.docx'
    check('commented DOCX fixture exists', comments_sample.is_file(), str(comments_sample))
    if comments_sample.is_file():
        from tests.factory import pack
        with zipfile.ZipFile(comments_sample) as archive:
            files = {name: archive.read(name) for name in archive.namelist()}
        files['word/document.xml'] = files['word/document.xml'].replace(b'1,000', b'1,250')
        content_type, payload = encode_form([
            ('original', 'original.docx', comments_sample.read_bytes()),
            ('revised', 'revised.docx', pack(files))])
        status, _, pdf = call(base, '/v1/compare-pdf', payload, content_type, token)
        check('commented comparison exports directly to pdf', status == 200 and pdf.startswith(b'%PDF-'), str(status))
        if pdf.startswith(b'%PDF-'):
            (artifacts / 'direct-comparison-with-comments.pdf').write_bytes(pdf)

    from tests.factory import pack, standard_files
    files = standard_files(["A document with custom XML metadata."])
    files["customXml/item1.xml"] = "<metadata><value>example</value></metadata>"
    files["word/_rels/document.xml.rels"] = files["word/_rels/document.xml.rels"].replace(
        "</Relationships>", '<Relationship Id="rId99" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/customXml" Target="../customXml/item1.xml"/></Relationships>')
    content_type, payload = encode_form([("document", "metadata.docx", pack(files))])
    status, _, body = call(base, "/v1/convert", payload, content_type, token)
    check("internal parent relationship converts", status == 200 and body.startswith(b"%PDF-"), str(status))

    hostile = make_docx(
        ["Hello"],
        "<w:p><w:r><w:instrText>DDEAUTO c:\\\\Windows\\\\System32\\\\cmd.exe</w:instrText></w:r></w:p>",
    )
    content_type, payload = encode_form([("document", "bad.docx", hostile)])
    status, _, body = call(base, "/v1/convert", payload, content_type, token)
    check("dde is rejected", status == 400 and b"active_content" in body, str(status))

    # These are our own small fixtures, with text accessible through Word's
    # standard PDF font mappings. This does not validate arbitrary uploaded PDFs.
    import runpy
    fixture_text = runpy.run_path(str(ROOT / 'scripts' / 'inspect-synthetic-pdfs.py'))['fixture_text']
    direct_path = artifacts / 'direct-comparison.pdf'
    separate_path = artifacts / 'separate-comparison.pdf'
    if direct_path.is_file() and separate_path.is_file():
        direct_text = fixture_text(direct_path)
        check('direct pdf keeps deleted and inserted amounts', '100' in direct_text and '250' in direct_text)
        check('direct and separate pdf text match', direct_text == fixture_text(separate_path))
    commented_path = artifacts / 'direct-comparison-with-comments.pdf'
    if comments_sample.is_file() and commented_path.is_file():
        comment_text = fixture_text(commented_path)
        compact_comments = ''.join(comment_text.split())
        check('direct pdf retains VAT comment text', 'ConfirmwhetherthefeeincludesVAT.' in compact_comments)
        check('direct pdf retains payment comment text', 'Considerreducingthepaymenttermto14days.' in compact_comments)

    service = set()
    for name in ("compare.word.pid", "convert.word.pid"):
        pid_file = ROOT / "work" / name
        if pid_file.is_file() and pid_file.read_text(encoding="ascii").strip().isdigit():
            service.add(int(pid_file.read_text(encoding="ascii").strip()))
    after = winword_pids()
    check("both service words stay up", len(service) == 2 and service <= after, str(sorted(service)))
    check("no extra word process", not (after - before - service), str(sorted(after - before - service)))
    print(f"{len(failures)} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
