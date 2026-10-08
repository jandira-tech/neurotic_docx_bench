# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import pathlib
p = pathlib.Path("src/edit.rs"); s = p.read_text()
def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (old[:80], s.count(old))
    s = s.replace(old, new)
rep("""        let main = self.opened.main.clone();
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
        let clean = self""", """        // The body is always written; a story part only when an operation
        // edits it, so untouched parts keep their exact bytes.
        let mut written = self.touched_stories();
        written.insert(0);
        let marked = if self.whole_marks.is_empty() {
            None
        } else {
            self.write_stories(&written);
            let bytes = self
                .opened
                .pkg
                .to_zip()
                .map_err(|e| err("PACKAGE_WRITE", None, e.to_string()))?;
            for &story in &written {
                whole::strip(&mut self.opened.dom, self.stories[story].root);
            }
            Some(bytes)
        };
        self.write_stories(&written);
        let clean = self""")
rep("""    fn write_comments_part(&mut self)""", """    fn write_stories(&mut self, stories: &std::collections::BTreeSet<usize>) {
        for &story in stories {
            let StoryPart { part, document, .. } = &self.stories[story];
            let xml = self.opened.dom.serialize_document(*document);
            self.opened.pkg.set_part(part, xml.into_bytes());
        }
    }

    fn write_comments_part(&mut self)""")
p.write_text(s)