# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import pathlib
def edit(path, pairs):
    p = pathlib.Path(path); s = p.read_text()
    for old, new in pairs:
        assert s.count(old) == 1, (path, old[:70], s.count(old))
        s = s.replace(old, new)
    p.write_text(s)
edit("jubarte-python/python/jubarte_redlines/models.py", [
("""        format: Mapping[str, object] | None = None,
        comment: str | None = None,
        id: str | None = None,
    ) -> EditPlan:
        \"\"\"Replace the unique occurrence of ``find``; ``format`` styles only the new text.\"\"\"
        op: dict[str, object] = {"kind": "replace", "paragraph": _selector(paragraph), "find": find, "replacement": replacement}
        if format is not None:
            op["format"] = _format(format)
""", """        format: Mapping[str, object] | None = None,
        comment: str | None = None,
        whole: bool = False,
        id: str | None = None,
    ) -> EditPlan:
        \"\"\"Replace the unique occurrence of ``find``; ``format`` styles only the new text.

        ``whole=True`` shows the change as all of ``find`` deleted, then all of
        ``replacement`` inserted, instead of Word Compare's word-level diff.
        \"\"\"
        op: dict[str, object] = {"kind": "replace", "paragraph": _selector(paragraph), "find": find, "replacement": replacement}
        if format is not None:
            op["format"] = _format(format)
        if whole:
            op["whole"] = True
"""),
])
edit("skills/jubarte-documents/SKILL.md", [
("""`insert` take an optional `format` (`bold`/`italic`/`underline`/`highlight`)
that applies to the new text only.
""", """`insert` take an optional `format` (`bold`/`italic`/`underline`/`highlight`)
that applies to the new text only. `replace` takes `"whole": true` to show
the change as the whole old text deleted, then the whole new text inserted.
"""),
("""- The redline is produced by comparing the source with the clean copy, the
  way Word Compare does. A long replacement therefore appears as a
  word-level diff against the old text, not as one deletion plus one
  insertion. The `ctx` field in the report shows exactly what you asked for.
""", """- The redline is produced by comparing the source with the clean copy, the
  way Word Compare does. A long replacement therefore appears as a
  word-level diff against the old text. Give the `replace` `"whole": true`
  to show one deletion followed by one insertion instead, as typing over
  the selection with Track Changes on would; if the comparer's diff cannot
  be regrouped, the operation stays word-level and its report line carries
  a `message` saying why. The `ctx` field in the report shows exactly what
  you asked for.
"""),
])
edit("jubarte-wasm/npm/README.md", [
("`replace`/`insert` take an optional run `format`)",
 "`replace`/`insert` take an optional run `format`; `replace` takes `whole: true` for one deletion then one insertion)"),
])