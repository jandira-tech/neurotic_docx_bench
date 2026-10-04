# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import os
for f in os.listdir('src'): os.remove('src/'+f)
NS=lambda r: f'<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:rPr>{r}</w:rPr></w:style>'
def mk3(name, rpr, dd_r, normal_r=None):
    st=dd(dd_r) if dd_r is not None else ''
    if normal_r is not None:
        st+=NS(normal_r).replace('<w:style w:type="paragraph" w:default="1" w:styleId="Normal">','<w:style w:type="paragraph" w:default="1" w:styleId="Normal2">')
    mk(name, rpr, st or '<w:docDefaults/>')
ARI='<w:rFonts w:ascii="Arial" w:hAnsi="Arial"/>'; CAL='<w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>'
mk3('g_dd_tnr_run_tnr', TNR, TNR)
mk3('h_dd_arial_run_tnr', TNR, ARI)
mk3('k_dd_calibri_run_tnr', TNR, CAL)
mk3('m_dd_tnr_run_arial', ARI, TNR)
mk('l_nostyles_norun', '', None)
mk('l_nostyles_norun_dnc', '', None, 'doNotCompress')