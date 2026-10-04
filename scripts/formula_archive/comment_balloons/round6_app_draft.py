# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
src=open('survey5.py').read()
src=src.replace('''"""Balloon model v2 over the 151 docs.

A comment gets a balloon iff it is referenced in the body and its range end is live:
no commentRangeEnd, or one with content before it in its own paragraph (text, deleted
text, a drawing/object/symbol/tab, or another comment's reference mark). A reply
(commentsExtended paraIdParent) takes its parent's fate when THREADS is on.
"""''','''"""Balloon model v3 over the 151 docs (2026-10-03).

v2 plus one refinement: a range end whose OWN commentRangeStart precedes it in the
same paragraph is live too (an empty range followed by its reference is a reference
alone). That explains the two documents v2 missed, 6ef6726c28 (Word 1, v2 predicted
0: `<w:commentRangeStart w:id="11"/><w:commentRangeEnd w:id="11"/><ref 11>`) and
1672057675 (Word 4, v2 predicted 2: `<start 0/><start 1/><end 0/><ref 0/><end 1/>
<ref 1/>`, comment 1 a reply of 0), and keeps the other 149 and all 37 zero-balloon
documents: exact 151/151. Reads survey5.json's Word counts; writes survey6.json.
Round 6 (`round6.py`) puts the shape itself in front of Word.
"""''')
src=src.replace('''                if x.tag in CONTENT and (x.text or x.tag not in (f"{W}t", f"{W}delText")): live = True''','''                if x.tag in CONTENT and (x.text or x.tag not in (f"{W}t", f"{W}delText")): live = True
                if x.tag == f"{W}commentRangeStart" and x.get(f"{W}id") == e.get(f"{W}id"): live = True''')
src=src.replace('rows = json.load(open("survey4.json"))','rows = json.load(open("survey5.json"))')
src=src.replace('json.dump(rows, open("survey5.json", "w"), indent=1)','json.dump(rows, open("survey6.json", "w"), indent=1)')
open('survey6.py','w').write(src)