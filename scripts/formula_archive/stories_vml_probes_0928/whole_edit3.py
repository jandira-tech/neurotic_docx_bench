# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import pathlib
p = pathlib.Path("src/edit.rs"); s = p.read_text()
def rep(old, new):
    global s
    assert s.count(old) == 1, (old[:80], s.count(old))
    s = s.replace(old, new)
rep("""    fn finish_clean(&mut self) -> Result<Vec<u8>, EditError> {
        let xml = self.opened.dom.serialize_document(self.opened.document);
        let main = self.opened.main.clone();
        self.opened.pkg.set_part(&main, xml.into_bytes());
        if !self.comments.is_empty() {
            self.write_comments_part()?;
        }
        self.opened
            .pkg
            .to_zip()
            .map_err(|e| err("PACKAGE_WRITE", None, e.to_string()))
    }
""", """    /// The clean copy, and the copy the comparer reads when `whole`
    /// replacements carry helper bookmarks (the clean copy never does).
    fn finish(&mut self) -> Result<(Vec<u8>, Option<Vec<u8>>), EditError> {
        if !self.comments.is_empty() {
            self.write_comments_part()?;
        }
        let main = self.opened.main.clone();
        let marked = if self.whole_marks.is_empty() {
            None
        } else {
            let xml = self.opened.dom.serialize_document(self.opened.document);
            self.opened.pkg.set_part(&main, xml.into_bytes());
            let bytes = self
                .opened
                .pkg
                .to_zip()
                .map_err(|e| err("PACKAGE_WRITE", None, e.to_string()))?;
            whole::strip(&mut self.opened.dom, self.opened.body);
            Some(bytes)
        };
        let xml = self.opened.dom.serialize_document(self.opened.document);
        self.opened.pkg.set_part(&main, xml.into_bytes());
        let clean = self
            .opened
            .pkg
            .to_zip()
            .map_err(|e| err("PACKAGE_WRITE", None, e.to_string()))?;
        Ok((clean, marked))
    }
""")
rep("""    let clean = tx.finish_clean()?;
    let settings = WmlComparerSettings {
        author_for_revisions: plan.author.clone(),
        date_time_for_revisions: tx.date.clone(),
        ..WmlComparerSettings::default()
    };
    let redline =
        crate::document_comparer::compare_documents_with_settings(&tx.base, &clean, &settings)
            .map_err(|e| err("COMPARE_FAILED", None, e.to_string()))?;
    let mut report = tx.report(true);
""", """    let (clean, marked) = tx.finish()?;
    let settings = WmlComparerSettings {
        author_for_revisions: plan.author.clone(),
        date_time_for_revisions: tx.date.clone(),
        ..WmlComparerSettings::default()
    };
    let revised = marked.as_deref().unwrap_or(&clean);
    let mut redline =
        crate::document_comparer::compare_documents_with_settings(&tx.base, revised, &settings)
            .map_err(|e| err("COMPARE_FAILED", None, e.to_string()))?;
    if marked.is_some() {
        let (rewritten, fallbacks) =
            whole::rewrite(&redline, &tx.whole_marks, &plan.author, &tx.date)?;
        redline = rewritten;
        for (op, reason) in fallbacks {
            tx.outcomes[op].message = Some(format!("shown as a word-level diff: {reason}"));
        }
    }
    let mut report = tx.report(true);
""")
p.write_text(s)