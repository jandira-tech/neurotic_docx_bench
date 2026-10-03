# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import pathlib
p = pathlib.Path("src/edit.rs"); s = p.read_text()
def rep(old, new, count=1, path=None):
    global s
    assert s.count(old) == count, (old[:80], s.count(old))
    s = s.replace(old, new)
rep("""                let s = new_position(&edits, edit.start, true, Some(edit.op));
                let end = s + edit.replacement.len();
                if let Some(mark) = whole::mark(
                    &mut self.opened.dom,
                    node,
                    (s, end),
                    edit.op,
                    (find, &edit.replacement),
                ) {""", """                let s = new_position(&edits, edit.start, true, Some(edit.op));
                let end = s + edit.replacement.len();
                let story = self.paragraph_story[para].0;
                let part = (story != 0).then(|| self.stories[story].part.clone());
                if let Some(mark) = whole::mark(
                    &mut self.opened.dom,
                    node,
                    (s, end),
                    (edit.op, part),
                    (find, &edit.replacement),
                ) {""")
p.write_text(s)

p = pathlib.Path("src/edit/whole.rs"); s = p.read_text()
rep("""pub(super) struct Mark {
    op: usize,
""", """pub(super) struct Mark {
    op: usize,
    /// The header, footer or notes part holding the text; `None` for the body.
    part: Option<String>,
""")
rep("""    (start, end): (usize, usize),
    op: usize,
    (find, replacement): (&str, &str),
) -> Option<Mark> {""", """    (start, end): (usize, usize),
    (op, part): (usize, Option<String>),
    (find, replacement): (&str, &str),
) -> Option<Mark> {""")
rep("""    wrap_range(dom, paragraph, start, end, open, close).then(|| Mark {
        op,
""", """    wrap_range(dom, paragraph, start, end, open, close).then(|| Mark {
        op,
        part,
""")
rep("""    let mut opened =
        Opened::open(redline).map_err(|e| err("COMPARE_FAILED", None, e.to_string()))?;
    let mut next_id = opened
        .dom
        .descendants(opened.body, None)
        .into_iter()
        .filter_map(|n| opened.dom.attribute(n, &W::id())?.parse::<u64>().ok())
        .max()
        .map_or(1, |max| max + 1);
    let mut fallbacks = Vec::new();
    for mark in marks {
        let stamp = Stamp {
            author,
            date,
            next_id: &mut next_id,
        };
        if let Err(reason) = rewrite_one(&mut opened.dom, opened.body, mark, stamp) {
            fallbacks.push((mark.op, reason));
        }
    }
    strip(&mut opened.dom, opened.body);
    let xml = opened.dom.serialize_document(opened.document);
    let main = opened.main.clone();
    opened.pkg.set_part(&main, xml.into_bytes());
    let bytes""", """    let mut opened =
        Opened::open(redline).map_err(|e| err("COMPARE_FAILED", None, e.to_string()))?;
    // The body, then every story part a mark lives in.
    let mut parts = vec![(opened.main.clone(), opened.document, opened.body)];
    let stories: std::collections::BTreeSet<&String> =
        marks.iter().filter_map(|m| m.part.as_ref()).collect();
    for part in stories {
        let missing = || err("COMPARE_FAILED", None, format!("redline lost {part}"));
        let xml = opened.pkg.part_string(part).ok_or_else(missing)?;
        let document = opened.dom.parse_xdocument(&xml);
        let root = opened.dom.root(document).ok_or_else(missing)?;
        parts.push((part.clone(), document, root));
    }
    let mut next_id = parts
        .iter()
        .flat_map(|&(_, _, root)| opened.dom.descendants(root, None))
        .filter_map(|n| opened.dom.attribute(n, &W::id())?.parse::<u64>().ok())
        .max()
        .map_or(1, |max| max + 1);
    let mut fallbacks = Vec::new();
    for mark in marks {
        let stamp = Stamp {
            author,
            date,
            next_id: &mut next_id,
        };
        let root = parts
            .iter()
            .find(|(part, ..)| mark.part.as_ref() == Some(part))
            .map_or(opened.body, |&(_, _, root)| root);
        if let Err(reason) = rewrite_one(&mut opened.dom, root, mark, stamp) {
            fallbacks.push((mark.op, reason));
        }
    }
    for (part, document, root) in parts {
        strip(&mut opened.dom, root);
        let xml = opened.dom.serialize_document(document);
        opened.pkg.set_part(&part, xml.into_bytes());
    }
    let bytes""")
p.write_text(s)