# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import pathlib
p = pathlib.Path("src/edit.rs"); s = p.read_text()
def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (old[:80], s.count(old))
    s = s.replace(old, new)
rep("""    paragraph_nodes: Vec<NodeId>,
    projections: Vec<Projection>,
""", """    /// The body first, then every header, footer and notes part.
    stories: Vec<StoryPart>,
    /// Every addressable paragraph: the body's, then each story's.
    paragraph_nodes: Vec<NodeId>,
    /// `(story, index in that story)` per entry of `paragraph_nodes`.
    paragraph_story: Vec<(usize, usize)>,
    projections: Vec<Projection>,
""")
rep("""impl<'p> Transaction<'p> {
    fn start(""", """/// The body, or a header, footer or notes part, parsed into the plan's DOM.
struct StoryPart {
    /// `body`, or the part's file stem (`header1`, `footnotes`).
    id: String,
    /// Package part name.
    part: String,
    document: NodeId,
    root: NodeId,
}

impl<'p> Transaction<'p> {
    fn start(""")
rep("""        let has_revisions = crate::inspect::revision_count(&probe.dom, probe.body) > 0;""",
"""        let story_revisions: usize = probe
            .story_parts()
            .iter()
            .filter_map(|(_, _, part)| crate::inspect::parse_part(&probe.pkg, part).ok())
            .map(|(dom, _, root)| crate::inspect::revision_count(&dom, root))
            .sum();
        let has_revisions =
            crate::inspect::revision_count(&probe.dom, probe.body) + story_revisions > 0;""")
rep("""        let (base, opened) = match (has_revisions, plan.existing_revisions) {""",
    """        let (base, mut opened) = match (has_revisions, plan.existing_revisions) {""")
rep("""        let paragraph_nodes = crate::inspect::body_paragraph_nodes(&opened.dom, opened.body);
        let projections = paragraph_nodes""", """        let mut stories = vec![StoryPart {
            id: "body".to_string(),
            part: opened.main.clone(),
            document: opened.document,
            root: opened.body,
        }];
        for (id, _, part) in opened.story_parts() {
            let invalid = |m: String| err("INVALID_DOCUMENT", None, format!("{part}: {m}"));
            let xml = opened
                .pkg
                .part_string(&part)
                .ok_or_else(|| invalid("missing part".into()))?;
            crate::xmllinq::parse::validate_xml(&xml).map_err(|e| invalid(e.to_string()))?;
            let document = opened.dom.parse_xdocument(&xml);
            let root = opened
                .dom
                .root(document)
                .ok_or_else(|| invalid("missing XML root".into()))?;
            stories.push(StoryPart {
                id,
                part,
                document,
                root,
            });
        }
        let mut paragraph_nodes = Vec::new();
        let mut paragraph_story = Vec::new();
        for (index, story) in stories.iter().enumerate() {
            let nodes = if index == 0 {
                crate::inspect::body_paragraph_nodes(&opened.dom, story.root)
            } else {
                crate::inspect::story_paragraph_nodes(&opened.dom, story.root)
            };
            for (local, node) in nodes.into_iter().enumerate() {
                paragraph_nodes.push(node);
                paragraph_story.push((index, local));
            }
        }
        let projections = paragraph_nodes""")
rep("""            paragraph_nodes,
            projections,
""", """            stories,
            paragraph_nodes,
            paragraph_story,
            projections,
""")
rep("""                from: self.paragraph_nodes.len(),
                to: self.paragraph_nodes.len(),""", """                from: self.body_paragraph_count(),
                to: self.body_paragraph_count(),""")
rep("""    /// `{story}:p:{index}` of a paragraph.""", """    fn body_paragraph_count(&self) -> usize {
        self.paragraph_story.iter().filter(|(s, _)| *s == 0).count()
    }

    /// Stories an operation of the plan edits.
    fn touched_stories(&self) -> std::collections::BTreeSet<usize> {
        self.resolved
            .iter()
            .map(|(_, r)| match r {
                Resolved::Text { para, .. }
                | Resolved::CommentRange { para, .. }
                | Resolved::DeleteParagraph { para }
                | Resolved::FormatParagraph { para, .. }
                | Resolved::MergeParagraphs { para, .. } => *para,
                Resolved::InsertParagraph { anchor, .. } => *anchor,
            })
            .map(|para| self.paragraph_story[para].0)
            .collect()
    }

    /// `{story}:p:{index}` of a paragraph.""")
# comments outside body
rep("""        outcome.paragraph = Some(self.paragraph_id(para));
        let projection = &self.projections[para];""", """        outcome.paragraph = Some(self.paragraph_id(para));
        let comments = match kind {
            OperationKind::Replace { comment, .. }
            | OperationKind::Insert { comment, .. }
            | OperationKind::InsertParagraph { comment, .. } => comment.is_some(),
            OperationKind::Comment { .. } => true,
            _ => false,
        };
        if comments && self.paragraph_story[para].0 != 0 {
            return Err(fail(
                "UNSUPPORTED_STRUCTURE",
                "comments are supported in the body only".into(),
                outcome,
            ));
        }
        let projection = &self.projections[para];""")
rep("""                let body_children = dom.elements(self.opened.body, Some(&W::p()));
                if body_children.len() == 1 && body_children[0] == node {
                    return Err(fail(
                        "UNSUPPORTED_STRUCTURE",
                        "the body must keep one paragraph".into(),
                        outcome,
                    ));
                }""", """                let (container, what) = self.story_container(node);
                let siblings = dom.elements(container, Some(&W::p()));
                if siblings.len() == 1 && siblings[0] == node {
                    return Err(fail(
                        "UNSUPPORTED_STRUCTURE",
                        format!("{what} must keep one paragraph"),
                        outcome,
                    ));
                }""")
rep("""            } else if dom
                .elements(self.opened.body, Some(&W::p()))
                .iter()
                .all(|p| gone.contains(p))
            {
                return Err(self.conflict(
                    *i,
                    "the plan's deletions leave the body without a paragraph",
                ));
            }""", """            } else {
                let (container, what) = self.story_container(node);
                if dom
                    .elements(container, Some(&W::p()))
                    .iter()
                    .all(|p| gone.contains(p))
                {
                    return Err(self.conflict(
                        *i,
                        &format!("the plan's deletions leave {what} without a paragraph"),
                    ));
                }
            }""")
p.write_text(s)