# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import pathlib
p = pathlib.Path("src/inspect.rs"); s = p.read_text()
def rep(old, new):
    global s
    assert s.count(old) == 1, (old[:80], s.count(old))
    s = s.replace(old, new)
rep("""    /// Body paragraphs.
    pub paragraphs: Vec<Paragraph>,
}
""", """    /// Body paragraphs.
    pub paragraphs: Vec<Paragraph>,
    /// Header, footer and note stories, each with its own paragraphs.
    pub stories: Vec<Story>,
}

/// A header, footer or notes part an edit plan can address. Its paragraph
/// ids are `{id}:p:{index}`.
#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
pub struct Story {
    /// The part's file stem: `header1`, `footer2`, `footnotes`, `endnotes`.
    pub id: String,
    /// `header`, `footer`, `footnotes` or `endnotes`.
    pub kind: String,
    /// Package part name, e.g. `word/header1.xml`.
    pub part: String,
    /// The story's paragraphs; separator notes are left out.
    pub paragraphs: Vec<Paragraph>,
}
""")
rep("""/// Paragraphs prefixed with their ids and direct formatting as Markdown
/// marks: `[body:p:12 Heading1] (a) **Confidentiality.** You will ...`.
pub fn markdown(docx: &[u8]) -> Result<String, InspectError> {
    Ok(render_markdown(&paragraphs(docx)?))
}
""", """/// Header, footer and note stories in a stable order (headers, footers,
/// footnotes, endnotes).
pub fn stories(docx: &[u8]) -> Result<Vec<Story>, InspectError> {
    Opened::open(docx)?.stories()
}

/// Paragraphs prefixed with their ids and direct formatting as Markdown
/// marks: `[body:p:12 Heading1] (a) **Confidentiality.** You will ...`.
/// Story paragraphs (`[header1:p:0] ...`) follow the body's.
pub fn markdown(docx: &[u8]) -> Result<String, InspectError> {
    let opened = Opened::open(docx)?;
    let mut all = body_paragraphs(&opened.dom, opened.body);
    for story in opened.stories()? {
        all.extend(story.paragraphs);
    }
    Ok(render_markdown(&all))
}
""")
rep("""        paragraphs: body_paragraphs(&opened.dom, opened.body),
    };""", """        paragraphs: body_paragraphs(&opened.dom, opened.body),
        stories: opened.stories()?,
    };""")
rep("""    pub(crate) fn related(&self, kind: &str) -> BTreeSet<String> {""", """    /// Header, footer and note parts: `(story id, kind, part name)`. The id
    /// is the part's file stem; `header2` sorts before `header10`.
    pub(crate) fn story_parts(&self) -> Vec<(String, &'static str, String)> {
        let mut out = Vec::new();
        for kind in ["header", "footer", "footnotes", "endnotes"] {
            let mut parts: Vec<String> = self.related(kind).into_iter().collect();
            parts.sort_by_key(|part| (part.len(), part.clone()));
            for part in parts {
                let stem = part.rsplit('/').next().unwrap_or(&part);
                let id = stem.strip_suffix(".xml").unwrap_or(stem).to_string();
                out.push((id, kind, part));
            }
        }
        out
    }

    fn stories(&self) -> Result<Vec<Story>, InspectError> {
        self.story_parts()
            .into_iter()
            .map(|(id, kind, part)| {
                let (dom, _, root) = parse_part(&self.pkg, &part)?;
                let paragraphs = paragraphs_of(&dom, story_paragraph_nodes(&dom, root), &id);
                Ok(Story {
                    id,
                    kind: kind.to_string(),
                    part,
                    paragraphs,
                })
            })
            .collect()
    }

    pub(crate) fn related(&self, kind: &str) -> BTreeSet<String> {""")
rep("""fn body_paragraphs(dom: &Dom, body: NodeId) -> Vec<Paragraph> {
    body_paragraph_nodes(dom, body)
        .into_iter()
        .enumerate()""", """/// A header, footer or notes part's paragraphs, separator notes left out.
pub(crate) fn story_paragraph_nodes(dom: &Dom, root: NodeId) -> Vec<NodeId> {
    body_paragraph_nodes(dom, root)
        .into_iter()
        .filter(|&p| {
            !dom.ancestors(p, None).into_iter().any(|a| {
                (dom.name_is(a, &W::name("footnote")) || dom.name_is(a, &W::name("endnote")))
                    && matches!(
                        dom.attribute(a, &W::name("type")),
                        Some("separator" | "continuationSeparator" | "continuationNotice")
                    )
            })
        })
        .collect()
}

fn body_paragraphs(dom: &Dom, body: NodeId) -> Vec<Paragraph> {
    paragraphs_of(dom, body_paragraph_nodes(dom, body), "body")
}

fn paragraphs_of(dom: &Dom, nodes: Vec<NodeId>, story: &str) -> Vec<Paragraph> {
    nodes
        .into_iter()
        .enumerate()""")
rep("""                id: format!("body:p:{index}"),""", """                id: format!("{story}:p:{index}"),""")
rep("""    /// Zero-based body order, table-cell paragraphs included.
    pub index: usize,
    /// `body:p:{index}`; the edit plan's paragraph selector.""", """    /// Zero-based order in its story, table-cell paragraphs included.
    pub index: usize,
    /// `body:p:{index}` (or `header1:p:{index}`, ...); the edit plan's
    /// paragraph selector.""")
p.write_text(s)