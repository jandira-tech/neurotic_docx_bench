# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import pathlib
p = pathlib.Path("src/edit.rs"); s = p.read_text()
def rep(old, new):
    global s
    assert s.count(old) == 1, (old[:80], s.count(old))
    s = s.replace(old, new)
rep("""        #[serde(default, skip_serializing_if = "Option::is_none")]
        /// Formatting of the replacement on top of the replaced run's.
        format: Option<RunFormat>,
        #[serde(default, skip_serializing_if = "Option::is_none")]
        /// Comment text anchored to the changed text.
        comment: Option<String>,
    },
    /// Insert `text` after/before""", """        #[serde(default, skip_serializing_if = "Option::is_none")]
        /// Formatting of the replacement on top of the replaced run's.
        format: Option<RunFormat>,
        #[serde(default, skip_serializing_if = "Option::is_none")]
        /// Comment text anchored to the changed text.
        comment: Option<String>,
        #[serde(default, skip_serializing_if = "std::ops::Not::not")]
        /// Show the change as all of `find` deleted, then all of
        /// `replacement` inserted, instead of Word Compare's word-level diff.
        whole: bool,
    },
    /// Insert `text` after/before""")
rep(""""replace" => &["find", "replacement", "format", "comment"],""",
    """"replace" => &["find", "replacement", "format", "comment", "whole"],""")
# Transaction fields
rep("""    next_comment_id: u64,
    comments_added: usize,
}
""", """    next_comment_id: u64,
    comments_added: usize,
    /// Helper bookmarks around `whole` replacements, one per operation.
    whole_marks: Vec<whole::Mark>,
}
""")
p.write_text(s)