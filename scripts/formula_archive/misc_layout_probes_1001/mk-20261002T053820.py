# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
mk('a/hs4.docx',f'<w:p><w:r><w:t>Alpha body one.</w:t></w:r></w:p><w:p><w:pPr>{sp(1)}</w:pPr></w:p><w:p><w:r><w:t>Alpha body two.</w:t></w:r></w:p>{sp(2)}',['First head','Second head'])
mk('b/hs4.docx',f'<w:p><w:r><w:t>Alpha body one.</w:t></w:r></w:p><w:p><w:r><w:t>Alpha body two.</w:t></w:r></w:p>{sp(1)}',['Bravo head'])