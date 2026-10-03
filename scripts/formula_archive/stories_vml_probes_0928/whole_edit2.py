# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import pathlib
p = pathlib.Path("src/edit.rs"); s = p.read_text()
def rep(old, new):
    global s
    assert s.count(old) == 1, (old[:80], s.count(old))
    s = s.replace(old, new)
rep("""fn anchor_comment(dom: &mut Dom, paragraph: NodeId, start: usize, end: usize, id: u32) {
    let projection = project_paragraph(dom, paragraph);""", """fn anchor_comment(dom: &mut Dom, paragraph: NodeId, start: usize, end: usize, id: u32) {
    let id_str = id.to_string();
    let range_start = dom.new_element(W::name("commentRangeStart"));
    dom.set_attribute_value(range_start, &W::id(), Some(&id_str));
    let range_end = dom.new_element(W::name("commentRangeEnd"));
    dom.set_attribute_value(range_end, &W::id(), Some(&id_str));
    let reference_run = dom.new_element(W::r());
    let reference = dom.new_element(W::name("commentReference"));
    dom.set_attribute_value(reference, &W::id(), Some(&id_str));
    dom.add(reference_run, reference);
    if wrap_range(dom, paragraph, start, end, range_start, range_end) {
        dom.add_after_self(range_end, reference_run);
    } else {
        dom.add(paragraph, range_start);
        dom.add(paragraph, range_end);
        dom.add(paragraph, reference_run);
    }
}

/// Put `open` right before the run holding projection offset `start` and
/// `close` right after the run ending at `end`, splitting runs at both
/// offsets first. False, with nothing placed, when the range holds no run.
fn wrap_range(
    dom: &mut Dom,
    paragraph: NodeId,
    start: usize,
    end: usize,
    open: NodeId,
    close: NodeId,
) -> bool {
    let projection = project_paragraph(dom, paragraph);""")
rep("""        .find(|s| s.end <= end && s.end > start)
        .map(|s| run_of(&s.piece));
    let id_str = id.to_string();
    let range_start = dom.new_element(W::name("commentRangeStart"));
    dom.set_attribute_value(range_start, &W::id(), Some(&id_str));
    let range_end = dom.new_element(W::name("commentRangeEnd"));
    dom.set_attribute_value(range_end, &W::id(), Some(&id_str));
    let reference_run = dom.new_element(W::r());
    let reference = dom.new_element(W::name("commentReference"));
    dom.set_attribute_value(reference, &W::id(), Some(&id_str));
    dom.add(reference_run, reference);
    match (first, last) {
        (Some(first), Some(last)) if start < end => {
            dom.add_before_self(first, range_start);
            dom.add_after_self(last, range_end);
            dom.add_after_self(range_end, reference_run);
        }
        _ => {
            dom.add(paragraph, range_start);
            dom.add(paragraph, range_end);
            dom.add(paragraph, reference_run);
        }
    }
}""", """        .find(|s| s.end <= end && s.end > start)
        .map(|s| run_of(&s.piece));
    match (first, last) {
        (Some(first), Some(last)) if start < end => {
            dom.add_before_self(first, open);
            dom.add_after_self(last, close);
            true
        }
        _ => false,
    }
}""")
rep("""            // Comment ranges, in new coordinates.
            let mut pending""", """            // Helper bookmarks around `whole` replacements. Comment ranges
            // placed below land inside them, on the inserted text.
            let plan = self.plan;
            for edit in &edits {
                let OperationKind::Replace {
                    find, whole: true, ..
                } = &plan.operations[edit.op].kind
                else {
                    continue;
                };
                if edit.replacement.is_empty() {
                    continue;
                }
                let s = new_position(&edits, edit.start, true, Some(edit.op));
                let end = s + edit.replacement.len();
                if let Some(mark) = whole::mark(
                    &mut self.opened.dom,
                    node,
                    (s, end),
                    edit.op,
                    (find, &edit.replacement),
                ) {
                    self.whole_marks.push(mark);
                }
            }
            // Comment ranges, in new coordinates.
            let mut pending""")
rep("""use crate::xmllinq::{Dom, NodeId, XNamespace};
""", """use crate::xmllinq::{Dom, NodeId, XNamespace};

mod whole;
""")
p.write_text(s)