"""Pure renewal helpers; the viewer envelope is immutable."""
import copy
import json
import re

R2 = 'https://pub-92c80eda1059428394970066c8500eda.r2.dev/'
VERSIONS = {'jubarte':'jubarte 0.14.0', 'jubarte-rust':'jubarte 0.14.0',
            'docxodus':'docxodus 14.2.0', 'superdoc':'superdoc-sdk 2.16.0',
            'reference':'Microsoft Word for Mac accept/reject'}
OLD_KEYS = ('jubarte-0.11.0','jubarte-0.12.0','jubarte-093','docxodus-12.6.5','docxodus-13.0.0')
FIELDS = ('pages','page_counts','scores','pdfs','times','errors','versions','metric_diagnostics')
LIST_FIELDS = ('unavailable','not_applicable')

def split(html):
    start=html.index('const DATA = ')+len('const DATA = ')
    end=html.index(';\n',start)
    return html[:start],json.loads(html[start:end]),html[end:]

def shown_pages(case):
    shown=case.get('shown')
    if shown is None:
        shown=list(range(1,min(3,case['page_counts']['reference'])+1))
    if len(shown)!=len(case['pages']['reference']) or shown!=sorted(set(shown)) or any(p<1 for p in shown):
        raise ValueError('Invalid shown pages or Word column alignment')
    for p,url in zip(shown,case['pages']['reference']):
        match=re.search(r'page_(\d+)\.webp$',url or '')
        if match and int(match[1])!=p:
            raise ValueError('Word image page disagrees with shown')
    return shown[:]

def remote_value(field,value):
    if field=='pages':
        return [R2+p if p else None for p in value]
    if field=='pdfs':
        return R2+value
    return copy.deepcopy(value)

def replace_case(original, rows):
    result=copy.deepcopy(original)
    columns=[r['column'] for r in rows]
    if len(set(columns))!=len(columns):
        raise ValueError('Duplicate replacement tool')
    removed=set()
    for row in rows:
        if (row['group'],row['case'])!=(original['group'],original['case']):
            raise ValueError('Case identity mismatch')
        if row['shown']!=shown_pages(original):
            raise ValueError('Shown selection changed')
    for field in FIELDS:
        values=result.get(field,{})
        for key in OLD_KEYS:
            if key in values:
                removed.add(key)
                del values[key]
        for row in rows:
            key=row['column']
            if key in row.get(field,{}):
                result.setdefault(field,{})[key]=remote_value(field,row[field][key])
            else:
                values.pop(key,None)
    for field in LIST_FIELDS:
        if field in result:
            result[field]=[k for k in result[field] if k not in (*OLD_KEYS,*columns)]
    result['dropped']=sorted((set(result.get('dropped',[]))|removed)-set(columns))
    return result

def patch_html(html, rows, added=()):
    head,cases,tail=split(html)
    if head+json.dumps(cases,ensure_ascii=False)+tail!=html:
        raise ValueError('Noncanonical DATA; refusing incidental changes')
    by_id={}
    for row in rows:
        by_id.setdefault((row['group'],row['case']),[]).append(row)
    output=[]
    seen=set()
    for case in cases:
        identity=case['group'],case['case']
        output.append(replace_case(case,by_id[identity]) if identity in by_id else case)
        seen.add(identity)
    if set(by_id)-seen:
        raise ValueError('Replacement case missing from viewer')
    for case in added:
        identity=case['group'],case['case']
        if identity in seen:
            raise ValueError('Added case identity collision')
        seen.add(identity)
        output.append(case)
    return head+json.dumps(output,ensure_ascii=False)+tail

def merge_ar(rows, engines):
    groups={}
    for row in rows:
        groups.setdefault((row['group'],row['case']),[]).append(row)
    result=[]
    for (group,name),parts in groups.items():
        if sorted(r['column'] for r in parts)!=['docxodus','jubarte-rust','reference','superdoc']:
            raise ValueError('Incomplete or duplicate AR columns')
        case={'group':group,'case':name,'shown':parts[0]['shown'],
              'reference_app':'Microsoft Word for Mac',
              'dropped':sorted(set(engines)-{r['column'] for r in parts})}
        for field in FIELDS:
            case[field]={key:remote_value(field,value) for r in parts for key,value in r.get(field,{}).items()}
        result.append(case)
    return result

def summary(rows):
    groups={}
    for row in rows:
        if row['tool']=='reference':
            continue
        values=groups.setdefault(row['group'],{}).setdefault(row['tool'],[])
        values.append(row)
    result={}
    for group,tools in sorted(groups.items()):
        result[group]={}
        for tool,parts in sorted(tools.items()):
            metrics={}
            for metric in ('pixel','jaccard','ssim','text_boundary'):
                vals=[r['scores'][r['column']].get(metric) for r in parts]
                vals=[v for v in vals if v is not None]
                metrics[metric]={'mean':sum(vals)/len(vals) if vals else None,'n':len(vals)}
            result[group][tool]={'cases':len(parts),'failures':{stage:sum(r.get('failure_type')==stage for r in parts) for stage in ('generation','word')},'metrics':metrics}
    return result
