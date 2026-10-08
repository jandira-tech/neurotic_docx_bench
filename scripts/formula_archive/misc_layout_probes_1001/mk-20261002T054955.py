# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
sp0='<w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="720" w:footer="720" w:gutter="0"/></w:sectPr>'
mk('a/hs5.docx',f'<w:p><w:r><w:t>Alpha body one.</w:t></w:r></w:p><w:p><w:pPr>{sp(1)}</w:pPr></w:p><w:p><w:r><w:t>Alpha body two.</w:t></w:r></w:p>{sp0}',['First head'])
mk('b/hs5.docx',f'<w:p><w:r><w:t>Alpha body one.</w:t></w:r></w:p><w:p><w:r><w:t>Alpha body two.</w:t></w:r></w:p>{sp(1)}',['Bravo head'])