# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
"""Top-level body blocks of document.xml (string spans, so every namespace prefix survives)."""
import re
TAG = re.compile(r"<(/?)([A-Za-z0-9_:.-]+)([^>]*?)(/?)>", re.S)
MARK = re.compile(r"<w:comment(?:RangeStart|RangeEnd|Reference)\b")

def body_span(xml):
    s = xml.index("<w:body>") + len("<w:body>"); e = xml.rindex("</w:body>")
    return s, e

def blocks(xml):
    """[(start, end, name)] of <w:body>'s children, final sectPr excluded."""
    s, e = body_span(xml); out = []; depth = 0; start = None; name = None
    for m in TAG.finditer(xml, s, e):
        closing, tag, selfclose = m.group(1), m.group(2), m.group(4) or m.group(3).rstrip().endswith("/")
        if tag.startswith("?") or tag.startswith("!"): continue
        if depth == 0 and not closing:
            start, name = m.start(), tag
            if selfclose: out.append((start, m.end(), tag)); continue
            depth = 1; continue
        if not closing and not selfclose: depth += 1
        elif closing:
            depth -= 1
            if depth == 0: out.append((start, m.end(), name))
    return [b for b in out if b[2] != "w:sectPr"]

def has_marker(xml, b):
    return bool(MARK.search(xml, b[0], b[1]))

def drop(xml, bl, idx):
    idx = sorted(set(idx), reverse=True)
    for i in idx:
        s, e, _ = bl[i]; xml = xml[:s] + xml[e:]
    return xml
