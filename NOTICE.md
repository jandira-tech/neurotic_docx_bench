# NOTICE

This site is built on work from **docxide-pdf** by Sverre Johann Bjørke
(<https://github.com/sverrejb/docxide-pdf>), licensed under the Apache License 2.0
(<https://www.apache.org/licenses/LICENSE-2.0>):

- the viewer (`index.html`) is generated from the template in `tools/engine_compare.py`,
  modified to add engines, a second document set, and true page counts when only the
  first pages are shown, then restyled in jubarte.pro's design (`_build/viewer_theme.py`);
- the scores are computed with its `page-metrics` tool (`tools/`, commit 261618a9);
- the "docxide fixtures" document set, and the Word, docxide-pdf, LibreOffice, MiniPdf,
  rdocx and office2pdf page images and scores for it, come from its published comparison
  (<https://sverrejb.github.io/docxide-pdf/>, built 2026-09-15), re-encoded at 100 DPI.

The "corpus sample" documents come from neurotic-docx-bench `corpus/word`; see its
`notices/` for their sources and licences.

The fonts under `_static/fonts/` are the ones jubarte.pro serves: Manrope (The Manrope
Project Authors) and JetBrains Mono (The JetBrains Mono Project Authors), both under the
SIL Open Font License 1.1; each licence is beside its font.
