# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import pathlib, re
p = pathlib.Path("src/edit.rs"); s = p.read_text()
def rep(old, new):
    global s
    assert s.count(old) == 1, (old[:80], s.count(old))
    s = s.replace(old, new)
rep("""/// Paragraph selector; every form must match exactly one body paragraph.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(untagged)]
pub enum Selector {
    /// `{"id": "body:p:12"}`.
    Id {
        /// `body:p:N`.
        id: String,
    },
    /// `{"index": 12}`.
    Index {
        /// Zero-based body index.
        index: usize,
    },
    /// `{"starts_with": "..."}`; unique prefix match.
    StartsWith {
        /// Unique paragraph text prefix.
        starts_with: String,
    },
    /// `{"contains": "..."}`; unique substring match.
    Contains {
        /// Unique paragraph text substring.
        contains: String,
    },
}
""", """/// Paragraph selector; every form must match exactly one paragraph. Ids
/// name their story (`body:p:3`, `header1:p:0`); the other forms search the
/// body unless they carry a `story` (`header1`, `footnotes`, ...).
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(untagged, deny_unknown_fields)]
pub enum Selector {
    /// `"body:p:12"`, the same as `{"id": "body:p:12"}`.
    Name(String),
    /// `{"id": "body:p:12"}`.
    Id {
        /// `{story}:p:N`.
        id: String,
    },
    /// `{"index": 12}`.
    Index {
        /// Zero-based index in the story.
        index: usize,
        #[serde(default, skip_serializing_if = "Option::is_none")]
        /// Story to search; the body when omitted.
        story: Option<String>,
    },
    /// `{"starts_with": "..."}`; unique prefix match.
    StartsWith {
        /// Unique paragraph text prefix.
        starts_with: String,
        #[serde(default, skip_serializing_if = "Option::is_none")]
        /// Story to search; the body when omitted.
        story: Option<String>,
    },
    /// `{"contains": "..."}`; unique substring match.
    Contains {
        /// Unique paragraph text substring.
        contains: String,
        #[serde(default, skip_serializing_if = "Option::is_none")]
        /// Story to search; the body when omitted.
        story: Option<String>,
    },
}
""")
# select()
start = s.index("    fn select(&self, selector: &Selector) -> Result<usize, (String, String, usize)> {")
end = s.index("    /// The unique occurrence of `find` (overlapping occurrences count), checked")
s = s[:start] + """    fn select(&self, selector: &Selector) -> Result<usize, (String, String, usize)> {
        let not_found = |message: String| Err(("ANCHOR_NOT_FOUND".to_string(), message, 0));
        let (story, index) = match selector {
            Selector::Name(id) | Selector::Id { id } => match id
                .rsplit_once(":p:")
                .and_then(|(story, n)| Some((story, n.parse::<usize>().ok()?)))
            {
                Some((story, n)) => (story, Some(n)),
                None => return not_found(format!("unknown paragraph id {id}")),
            },
            Selector::Index { index, story } => (story.as_deref().unwrap_or("body"), Some(*index)),
            Selector::StartsWith { story, .. } | Selector::Contains { story, .. } => {
                (story.as_deref().unwrap_or("body"), None)
            }
        };
        let Some(story_index) = self.stories.iter().position(|s| s.id == story) else {
            let known: Vec<&str> = self.stories.iter().map(|s| s.id.as_str()).collect();
            return not_found(format!(
                "unknown story {story:?}; this document has {}",
                known.join(", ")
            ));
        };
        let members: Vec<usize> = (0..self.paragraph_nodes.len())
            .filter(|&g| self.paragraph_story[g].0 == story_index)
            .collect();
        if let Some(index) = index {
            return match members.get(index) {
                Some(&g) => Ok(g),
                None => not_found(format!(
                    "paragraph index {index} does not exist in {story} ({} paragraphs)",
                    members.len()
                )),
            };
        }
        let (wanted, prefix) = match selector {
            Selector::StartsWith { starts_with, .. } => (starts_with, true),
            Selector::Contains { contains, .. } => (contains, false),
            _ => unreachable!("ids and indexes returned above"),
        };
        if wanted.is_empty() {
            return Err((
                "INVALID_EDIT".into(),
                "paragraph selector text must be nonempty".into(),
                0,
            ));
        }
        let hits: Vec<usize> = members
            .into_iter()
            .filter(|&g| {
                let text = &self.projections[g].text;
                if prefix {
                    text.starts_with(wanted.as_str())
                } else {
                    text.contains(wanted.as_str())
                }
            })
            .collect();
        match hits.as_slice() {
            [one] => Ok(*one),
            [] => not_found(format!("no paragraph matches {wanted:?}")),
            many => Err((
                "AMBIGUOUS_ANCHOR".into(),
                format!(
                    "{} paragraphs match {wanted:?}: {}",
                    many.len(),
                    many.iter()
                        .map(|&g| self.paragraph_id(g))
                        .collect::<Vec<_>>()
                        .join(", ")
                ),
                many.len(),
            )),
        }
    }

    /// `{story}:p:{index}` of a paragraph.
    fn paragraph_id(&self, para: usize) -> String {
        let (story, local) = self.paragraph_story[para];
        format!("{}:p:{local}", self.stories[story].id)
    }

    /// The body, header, footer or note a paragraph belongs to, for the
    /// "keeps one paragraph" checks.
    fn story_container(&self, node: NodeId) -> (NodeId, &'static str) {
        let dom = &self.opened.dom;
        for (name, what) in [
            ("footnote", "a footnote"),
            ("endnote", "an endnote"),
            ("hdr", "a header"),
            ("ftr", "a footer"),
        ] {
            if let Some(&found) = dom.ancestors(node, Some(&W::name(name))).first() {
                return (found, what);
            }
        }
        (self.opened.body, "the body")
    }

""" + s[end:]
rep("""        outcome.paragraph = Some(format!("body:p:{para}"));""", """        outcome.paragraph = Some(self.paragraph_id(para));""")
p.write_text(s)