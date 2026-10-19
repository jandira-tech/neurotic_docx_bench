"""Unsafe gate before Word. Nothing is sanitized: files are copied byte-for-byte.

Unsafe (never opened): zip bombs, purexml bomb/XXE/limit hits (RECOMMENDED_LIMITS), and
files today's word_endpoint guard flags as active_content / external_content / macros.
Broken-but-safe (malformed XML, unreadable member, not a zip) goes to Word: that is
what we want to find out. Writes <dst>/purexml_gate.csv.

usage: purexml_gate.py <src_dir> <dst_dir> <guard_reasons.csv>...
"""

import csv
import shutil
import sys
import zipfile
from pathlib import Path

import purexml
from purexml import RECOMMENDED_LIMITS
from purexml.ElementTree import fromstring

MAX_ENTRIES = 4096
MAX_MEMBER = 64 * 1024 * 1024
MAX_TOTAL = 256 * 1024 * 1024
MAX_RATIO = 200          # expanded / compressed, per member over 1 MB expanded

src, dst = Path(sys.argv[1]), Path(sys.argv[2])
ok_dir, bad_dir = dst / "word_input", dst / "unsafe_not_opened"
UNSAFE_GUARD = {"active_content", "external_content", "macros", "encrypted"}
guard = {}
for g in sys.argv[3:]:
    for r in csv.DictReader(open(g)):
        guard[r["sha256"]] = (r["local_code"], r["reason"], r["part"])
for d in (ok_dir, bad_dir):
    d.mkdir(parents=True, exist_ok=True)


def check(path: Path) -> str:
    try:
        zf = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, OSError) as exc:
        return f"not_zip: {exc}"
    with zf:
        infos = zf.infolist()
        if len(infos) > MAX_ENTRIES:
            return f"zip_bomb: {len(infos)} entries"
        total = 0
        for i in infos:
            total += i.file_size
            if i.file_size > MAX_MEMBER:
                return f"zip_bomb: {i.filename} expands to {i.file_size}"
            if i.file_size > 1 << 20 and i.compress_size and i.file_size / i.compress_size > MAX_RATIO:
                return f"zip_bomb: {i.filename} ratio {i.file_size / i.compress_size:.0f}"
        if total > MAX_TOTAL:
            return f"zip_bomb: total {total}"
        for i in infos:
            name = i.filename.lower()
            if not name.endswith((".xml", ".rels", ".vml")):
                continue
            try:
                data = zf.read(i)
            except Exception as exc:  # corrupt member, bad CRC, unsupported compression
                return f"zip_member_unreadable: {i.filename}: {type(exc).__name__}: {exc}"[:200]
            try:
                fromstring(data, limits=RECOMMENDED_LIMITS)
            except purexml.LimitExceeded as exc:
                return f"limit_exceeded: {i.filename}: {exc}"[:200]
            except Exception as exc:
                kind = type(exc).__name__
                family = ("xml_bomb_or_xxe" if kind in {"EntitiesForbidden", "ExternalReferenceForbidden",
                                                        "DTDForbidden", "NotSupportedError"}
                          else "xml_malformed")
                return f"{family}: {i.filename}: {kind}: {exc}"[:200]
    return "ok"


SAFE_TO_OPEN = {"ok", "xml_malformed", "zip_member_unreadable", "not_zip"}
rows = []
for path in sorted(src.glob("*.docx")):
    verdict = check(path)
    family = verdict.split(":", 1)[0]
    g = guard.get(path.stem, ("", "", ""))
    unsafe = family not in SAFE_TO_OPEN or g[0] in UNSAFE_GUARD
    shutil.copy2(path, (bad_dir if unsafe else ok_dir) / path.name)
    rows.append({"file": path.name, "opened": not unsafe, "purexml": family, "detail": verdict,
                 "guard_now": g[0], "guard_reason": g[1], "guard_part": g[2]})

with open(dst / "purexml_gate.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]))
    w.writeheader(); w.writerows(rows)
from collections import Counter
print(Counter((r["opened"], r["purexml"], r["guard_now"]) for r in rows))
