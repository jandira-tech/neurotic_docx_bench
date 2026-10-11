# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import zipfile,re,os,collections,sys
from lxml import etree
WR=os.path.expanduser('~/temp/T/neurotic_docx_bench/grok_run/wr0926')
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
W='{%s}'%NS['w']
def load(p,part):
    try: return etree.fromstring(zipfile.ZipFile(p).read(part))
    except Exception: return None
class Styles:
    def __init__(s,root):
        s.by={}; s.dd=None; s.default=None
        if root is None: return
        for st in root.findall('w:style',NS):
            sid=st.get(W+'styleId'); s.by[sid]=st
            if st.get(W+'type')=='paragraph' and st.get(W+'default') in ('1','true'): s.default=sid
        s.dd=root.find('w:docDefaults/w:pPrDefault/w:pPr',NS)
    def chain(s,sid):
        out=[];cur=sid if sid in s.by else s.default
        while cur and cur in s.by and len(out)<12 and s.by[cur] not in out:
            st=s.by[cur]; out.append(st.find('w:pPr',NS))
            b=st.find('w:basedOn',NS); cur=b.get(W+'val') if b is not None else None
        if s.dd is not None: out.append(s.dd)
        return out
def val(holders,attr,default):
    for h in holders:
        if h is None: continue
        sp=h.find('w:spacing',NS)
        if sp is not None and sp.get(W+attr) is not None: return sp.get(W+attr)
    return default
def lineval(holders):
    for h in holders:
        if h is None: continue
        sp=h.find('w:spacing',NS)
        if sp is not None and sp.get(W+'line') is not None: return (sp.get(W+'line'),sp.get(W+'lineRule') or 'auto')
    return ('240','auto')
def pstyle(ppr):
    if ppr is None: return None
    e=ppr.find('w:pStyle',NS); return e.get(W+'val') if e is not None else None
def text(p): return ''.join(t.text or '' for t in p.iter(W+'t',W+'delText'))
def live_ppr(p):
    return p.find('w:pPr',NS)
def eff(ppr,styles,sid):
    return [ppr]+styles.chain(sid)
agree=collections.Counter(); bad=collections.Counter(); ex=[]
for pool in ['word_based','word_based_randomized','word_redlines_superdoc']:
    for line in open(f'{WR}/{pool}/map.tsv'):
        pid,stem=line.rstrip('\n').split('\t')[:2]
        O=f'{WR}/{pool}/out/{pid}__vs__{pid}.docx'; B=f'{WR}/{pool}/b/{pid}.docx'
        od=load(O,'word/document.xml'); bd=load(B,'word/document.xml')
        if od is None or bd is None: continue
        os_=Styles(load(O,'word/styles.xml')); bs=Styles(load(B,'word/styles.xml'))
        bps=collections.defaultdict(list)
        for p in bd.iter(W+'p'):
            t=text(p)
            if t.strip(): bps[t].append(p)
        for p in od.iter(W+'p'):
            ppr=p.find('w:pPr',NS)
            if ppr is None or ppr.find('w:rPr/w:ins',NS) is None: continue
            if p.find('.//w:del',NS) is not None or p.find('.//w:delText',NS) is not None: continue
            if ppr.find('w:pPrChange',NS) is not None: continue
            t=text(p)
            if not t.strip() or len(bps.get(t,[]))!=1: continue
            bp=bps[t][0]; bppr=bp.find('w:pPr',NS)
            # skip Lines/autospacing
            hb=eff(bppr,bs,pstyle(bppr))
            if any(h is not None and h.find('w:spacing',NS) is not None and any(k in (h.find('w:spacing',NS).attrib) for k in (W+'beforeLines',W+'afterLines',W+'beforeAutospacing',W+'afterAutospacing')) for h in hb): continue
            osid=pstyle(ppr)
            ho=os_.chain(osid)
            sp=ppr.find('w:spacing',NS)
            for attr,d in (('before','0'),('after','0')):
                bv=val(hb,attr,d); ov=val(ho,attr,d)
                pred=bv if bv!=ov else None
                act=sp.get(W+attr) if sp is not None else None
                # also compare with jubarte-style "keep source direct" baseline
                src=(bppr.find('w:spacing',NS).get(W+attr) if bppr is not None and bppr.find('w:spacing',NS) is not None else None)
                agree[(attr,'model',pred==act)]+=1; agree[(attr,'direct',src==act)]+=1
                if pred!=act and len(ex)<15: ex.append((pool,pid,attr,'pred',pred,'act',act,'src',src,t[:30]))
            bl=lineval(hb); ol=lineval(ho)
            pred=bl if bl!=ol else None
            act=(sp.get(W+'line'),sp.get(W+'lineRule') or 'auto') if sp is not None and sp.get(W+'line') else None
            srcsp=bppr.find('w:spacing',NS) if bppr is not None else None
            src=(srcsp.get(W+'line'),srcsp.get(W+'lineRule') or 'auto') if srcsp is not None and srcsp.get(W+'line') else None
            agree[('line','model',pred==act)]+=1; agree[('line','direct',src==act)]+=1
            if pred!=act and len(ex)<30: ex.append((pool,pid,'line','pred',pred,'act',act,'src',src,t[:30]))
for k in sorted(agree): print(k,agree[k])
for e in ex: print(e)