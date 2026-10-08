# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
exec(open('gen.py').read().split("AUTO=")[0])
AUTO='<w:pPr><w:spacing w:after="200" w:line="276" w:lineRule="auto"/></w:pPr>'
FA=f'<w:p>{AUTO}<w:r><w:t>Page</w:t></w:r></w:p><w:p>{AUTO}</w:p>'
exec(open('gen.py').read().split("def mk(")[1].join(["def mk(",""]) if False else "")