#!/usr/bin/env python3
"""Local analysis library. Standard library only; no network or original-paper downloads.

Canonical records: data/{papers,analyses,ideas,sources}/*.json and notes/*.md.
index.html, catalog.json, INDEX.md, IDEAS.md and views/ are rebuildable outputs.
"""
from __future__ import annotations
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import html
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile
import unicodedata
from urllib.parse import urlsplit, unquote
import zipfile

ROOT = Path(__file__).resolve().parents[1]
KINDS = ('papers', 'analyses', 'ideas', 'sources')
ROLES = {'author','review','proposal'}
STATES = {'candidate','checking','active','paused','completed','stopped'}

def now() -> str: return datetime.now(timezone.utc).isoformat()
def today() -> str: return datetime.now(timezone.utc).date().isoformat()
def digest(data: bytes) -> str: return hashlib.sha256(data).hexdigest()
def load(p: Path): return json.loads(p.read_text(encoding='utf-8'))
def encoded(d) -> bytes: return (json.dumps(d, ensure_ascii=False, indent=2, allow_nan=False)+'\n').encode()
def text(x) -> bool: return isinstance(x,str) and bool(x.strip())
def norm_title(s: str) -> str: return ''.join(c for c in unicodedata.normalize('NFKC',s).casefold() if c.isalnum())

def norm_arxiv(s) -> str | None:
    if not s: return None
    if not isinstance(s,str): raise ValueError('arXiv identifier must be text')
    m=re.search(r'(?:^|/|arxiv:\s*)(\d{4}\.\d{4,5})(?:v\d+)?(?:\.pdf)?(?:$|[?#/])',s.strip(),re.I)
    if not m: raise ValueError('Use a complete modern arXiv ID or URL, optionally including vN')
    return m.group(1)

def norm_doi(s) -> str | None:
    if not s: return None
    if not isinstance(s,str): raise ValueError('DOI must be text')
    value=re.sub(r'^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)','',s.strip(),flags=re.I).casefold()
    if not re.match(r'^10\.\d{4,9}/\S+$',value): raise ValueError('Invalid DOI syntax')
    return value

def safe_url(s: str) -> bool:
    try: return isinstance(s,str) and urlsplit(s).scheme.lower() in {'https','http'} and bool(urlsplit(s).netloc)
    except ValueError: return False

def safe_path(root: Path, rel: str) -> Path:
    if not isinstance(rel,str) or not rel or '\\' in rel: raise ValueError('Invalid relative path')
    p=Path(rel)
    if p.is_absolute() or '..' in p.parts: raise ValueError('Path must remain in the library')
    target=root.resolve()
    for part in p.parts:
        target/=part
        if target.is_symlink(): raise ValueError('Symlinks are not accepted')
    target.resolve().relative_to(root.resolve())
    return target

def atomic(path: Path, data: bytes, replace=True):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.is_symlink(): raise ValueError('Refusing symlink output')
    if not replace and path.exists(): raise FileExistsError(path)
    fd,tmp=tempfile.mkstemp(prefix='.write-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as f: f.write(data);f.flush();os.fsync(f.fileno())
        if not replace and path.exists(): raise FileExistsError(path)
        if replace:
            os.replace(tmp,path)
        else:
            os.link(tmp,path)  # Atomic no-clobber publication on the same filesystem.
    finally:
        if os.path.exists(tmp): os.unlink(tmp)

@contextmanager
def locked(root: Path):
    path=root/'.library.lock'
    fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    try:
        os.write(fd,str(os.getpid()).encode());os.close(fd);yield
    finally: path.unlink(missing_ok=True)

def records(root: Path) -> dict:
    result={}
    for kind in KINDS:
        result[kind]={}
        for path in sorted((root/'data'/kind).glob('*.json')):
            if path.is_symlink(): raise ValueError('Record symlink rejected')
            d=load(path)
            if not isinstance(d,dict) or d.get('id')!=path.stem: raise ValueError(f'Record ID/path mismatch: {path.name}')
            if d['id'] in result[kind]: raise ValueError('Duplicate record ID')
            result[kind][d['id']]=d
    return result

def numeric_score(v):
    if type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=10:
        raise ValueError('Score must be a finite number from 0 to 10; unrated is absence, not zero')
    return float(v)

def validate(root: Path=ROOT) -> dict:
    errors=[];warnings=[]
    try: db=records(root)
    except (OSError,ValueError,TypeError) as e: return {'passed':False,'errors':[str(e)],'warnings':[]}
    ids={};aliases={}
    def error(msg): errors.append(msg)
    for pid,p in db['papers'].items():
        if not re.fullmatch(r'P\d{4,}',pid) or not text(p.get('title')): error(f'{pid}: missing/invalid title or ID')
        for v in p.get('aliases',[]):
            if not text(v): error(f'{pid}: invalid alias');continue
            k=v.casefold()
            if k in aliases and aliases[k]!=pid: error(f'Alias collision: {v}')
            aliases[k]=pid
        for typ,fn in [('arxiv',norm_arxiv),('doi',norm_doi)]:
            try: v=fn(p.get('identifiers',{}).get(typ))
            except ValueError as e: error(f'{pid}: {e}');continue
            if v:
                if (typ,v) in ids: error(f'Duplicate {typ}: {v}')
                ids[typ,v]=pid
        if any(not safe_url(u) for u in p.get('links',[])): error(f'{pid}: unsafe source URL')
        for aid in p.get('analysis_ids',[]):
            if aid not in db['analyses'] or db['analyses'][aid]['paper_id']!=pid: error(f'{pid}: invalid analysis {aid}')
        for iid in p.get('idea_ids',[]):
            if iid not in db['ideas'] or pid not in db['ideas'][iid]['paper_ids']: error(f'{pid}: invalid idea {iid}')
        for rating in p.get('ratings',[]):
            try: numeric_score(rating['score'])
            except (ValueError,KeyError) as e: error(f'{pid}: invalid rating {e}')
            if not text(rating.get('reason')) or not text(rating.get('scope')): error(f'{pid}: rating lacks rationale or scope')
    for aid,a in db['analyses'].items():
        if a.get('paper_id') not in db['papers']: error(f'{aid}: unknown paper')
        elif aid not in db['papers'][a['paper_id']]['analysis_ids']: error(f'{aid}: missing backlink')
        try:
            p=safe_path(root,a['note_path']);raw=p.read_bytes()
            if digest(raw)!=a['note_sha256']: error(f'{aid}: note changed; update the recorded hash or append a new analysis')
        except (OSError,ValueError,KeyError) as e:error(f'{aid}: {e}')
        for s in a.get('source_refs',[]):
            if s.get('source_id') not in db['sources']: error(f'{aid}: unknown source')
        for c in a.get('codings',[]):
            if c.get('role') not in ROLES or not re.fullmatch(r'M(?:[1-9]|1[0-4])',c.get('code','')):error(f'{aid}: invalid coding')
    for iid,i in db['ideas'].items():
        if not text(i.get('title')) or i.get('status') not in STATES: error(f'{iid}: invalid idea')
        if not i.get('paper_ids') or any(p not in db['papers'] for p in i['paper_ids']):error(f'{iid}: paper refs missing')
        for p in i.get('paper_ids',[]):
            if p in db['papers'] and iid not in db['papers'][p]['idea_ids']:error(f'{iid}: missing paper backlink')
        if any(a not in db['analyses'] for a in i.get('analysis_ids',[])):error(f'{iid}: invalid analysis source')
        for r in i.get('ratings',[]):
            try:numeric_score(r['score'])
            except (ValueError,KeyError):error(f'{iid}: invalid score')
    for sid,s in db['sources'].items():
        try:
            p=safe_path(root,s['path'])
            if digest(p.read_bytes())!=s['sha256']:error(f'{sid}: source snapshot changed')
            if p.suffix.lower() not in {'.md','.txt','.json'}:error(f'{sid}: only analysis text is allowed')
        except (OSError,ValueError,KeyError) as e:error(f'{sid}: {e}')
    if (root/'data/collections.json').exists():
        for c in load(root/'data/collections.json')['collections']:
            if any(p not in db['papers'] for p in c['paper_ids']): error(f"{c['id']}: unknown collection paper")
    counts={k:len(v) for k,v in db.items()}
    return {'passed':not errors,'errors':errors,'warnings':warnings,'counts':counts,
            'scope':'record_integrity_not_scientific_validation','rated_papers':sum(bool(p.get('ratings')) for p in db['papers'].values()),
            'rated_ideas':sum(bool(p.get('ratings')) for p in db['ideas'].values())}

def next_id(items: dict, prefix: str) -> str:
    n=max([int(k[len(prefix):]) for k in items if re.fullmatch(prefix+r'\d+',k)] or [0])+1
    return f'{prefix}{n:04d}'

def find_paper(db: dict, query: str) -> dict:
    if query in db['papers']:return db['papers'][query]
    hits=[p for p in db['papers'].values() if query.casefold() in [s.casefold() for s in p.get('aliases',[])]]
    if len(hits)!=1:raise ValueError('Paper not found or ambiguous; use its P ID')
    return hits[0]

def ingest(root: Path, intake: object) -> dict:
    if not isinstance(intake,dict):raise ValueError('Intake must be a JSON object')
    for key in ('title','analysis_markdown','source_description'):
        if not text(intake.get(key)):raise ValueError(f'{key} is required')
    for key in ('aliases','topics','tags','ideas'):
        if key in intake and not isinstance(intake[key],list):raise ValueError(f'{key} must be a list')
    for key in ('aliases','topics','tags'):
        if not all(text(v) for v in intake.get(key,[])):raise ValueError(f'{key} must contain nonempty strings')
    url=intake.get('paper_url','')
    if url and not safe_url(url):raise ValueError('Only http(s) paper links are allowed')
    ar=norm_arxiv(intake.get('arxiv') or (url if 'arxiv.org/' in url else None));doi=norm_doi(intake.get('doi'))
    for x in intake.get('ideas',[]):
        if not isinstance(x,dict) or not text(x.get('title')):raise ValueError('Each idea needs a title')
        if not isinstance(x.get('decision_branches',[]),list) or not all(text(z) for z in x.get('decision_branches',[])):raise ValueError('Idea branches must be a string list')
    codes=intake.get('codings',[])
    if not isinstance(codes,list):raise ValueError('codings must be a list')
    for c in codes:
        if not isinstance(c,dict) or c.get('role') not in ROLES or not re.fullmatch(r'M(?:[1-9]|1[0-4])',c.get('code','')) or not text(c.get('anchor')):
            raise ValueError('Each coding needs M1–M14, role and source anchor')
    with locked(root):
        db=records(root); matches=set()
        for p in db['papers'].values():
            ident=p.get('identifiers',{})
            if (ar and ar==ident.get('arxiv')) or (doi and doi==ident.get('doi')): matches.add(p['id'])
        if len(matches)>1:raise ValueError('Identifiers point to different papers; resolve explicitly')
        explicit=intake.get('paper_id')
        if explicit:
            p=find_paper(db,explicit)
            if matches and p['id'] not in matches:raise ValueError('paper_id conflicts with identifier')
        elif matches:p=db['papers'][next(iter(matches))]
        else:
            same=[p for p in db['papers'].values() if norm_title(p['title'])==norm_title(intake['title'])]
            if same:raise ValueError('Same title found; set paper_id to append, or distinguish the title and identifiers')
            p=None
        pid=p['id'] if p else next_id(db['papers'],'P')
        if p:
            for k,v in [('arxiv',ar),('doi',doi)]:
                if v and p['identifiers'].get(k) and p['identifiers'][k]!=v:raise ValueError('Identifier conflicts with selected paper')
            for a in p['analysis_ids']:
                if db['analyses'][a]['note_sha256']==digest(intake['analysis_markdown'].encode()):
                    return {'action':'unchanged','paper_id':pid,'analysis_id':a,'reason':'identical_analysis_body'}
        if p:
            p=json.loads(json.dumps(p))  # Preserve the pre-update record in the journal.
        aliases=intake.get('aliases',[])
        for other in db['papers'].values():
            if other['id']!=pid and {a.casefold() for a in aliases}&{a.casefold() for a in other.get('aliases',[])}:
                raise ValueError('Alias already belongs to another paper')
        stamp=now();date=intake.get('analyzed_at') or today()
        if not isinstance(date,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',date):raise ValueError('Use YYYY-MM-DD for analyzed_at')
        if not p:
            p={'schema_version':'1.0','id':pid,'title':intake['title'],'short_name':intake.get('short_name') or intake['title'],
               'aliases':[],'identifiers':{'arxiv':ar,'doi':doi},'links':[],'topics':intake.get('topics') or ['未分类'],
               'tags':[],'reading_status':'v04_detailed_analysis' if intake.get('framework_version')=='0.4.0' else 'brief_analysis',
               'metadata_observations':[],'analysis_ids':[],'idea_ids':[],'ratings':[],'created_at':date,'updated_at':date,'dataset_role':'development'}
        p['topics']=list(dict.fromkeys(p['topics']+intake.get('topics',[])))
        p['aliases']=list(dict.fromkeys(p['aliases']+aliases));p['tags']=list(dict.fromkeys(p['tags']+intake.get('tags',[])))
        for k,v in [('arxiv',ar),('doi',doi)]:
            if v:p['identifiers'][k]=v
        if url:p['links']=list(dict.fromkeys(p['links']+[url]))
        aid=next_id(db['analyses'],'A');sid=next_id(db['sources'],'S');note=f'notes/{aid}.md'
        source_path=f'sources/{sid}.json'; source_raw=encoded(intake)
        src={'id':sid,'kind':'user_supplied_analysis','path':source_path,'sha256':digest(source_raw),'description':intake['source_description'],'imported_at':stamp,'reverified_in_library_build':False}
        p['metadata_observations'].append({'source_id':sid,'as_of':date,'title':intake['title'],'venue':intake.get('venue'),'paper_version':intake.get('paper_version'),'verification':'as_supplied_not_automatically_verified'})
        if intake.get('framework_version')=='0.4.0':p['reading_status']='v04_detailed_analysis'
        a={'schema_version':'1.0','id':aid,'paper_id':pid,'kind':'added_analysis','analyzed_at':date,'imported_at':stamp,'framework_version':intake.get('framework_version'),
           'paper_version_as_reported':intake.get('paper_version'),'summary':intake.get('summary',''),'sections':{},'codings':codes,'note_path':note,'note_sha256':digest(intake['analysis_markdown'].encode()),
           'source_refs':[{'source_id':sid,'locator':'analysis_markdown'}],'status':'as_supplied_not_reverified','independent_recoding':False,'paper_experiment_reproduced':False,'preservation':'user_supplied_text'}
        if not isinstance(intake.get('sections',{}),dict) or not all(isinstance(k,str) and isinstance(v,str) for k,v in intake.get('sections',{}).items()):raise ValueError('sections must map headings to strings')
        a['sections']=intake.get('sections',{})
        pending={source_path:source_raw,'data/sources/'+sid+'.json':encoded(src),note:intake['analysis_markdown'].encode(),'data/analyses/'+aid+'.json':encoded(a)}
        p['analysis_ids'].append(aid);p['updated_at']=date
        for x in intake.get('ideas',[]):
            iid=next_id(db['ideas'],'I')
            i={'schema_version':'1.0','id':iid,'title':x['title'],'paper_ids':[pid],'analysis_ids':[aid],
               'kind':'research_direction','question':x.get('question',x['title']),'first_evidence':x.get('first_evidence',''),
               'decision_branches':x.get('decision_branches',[]),'status':'candidate','novelty_status':'not_established','execution_status':'not_run_in_library',
               'ratings':[],'created_at':date,'updated_at':date,'state_history':[{'date':date,'status':'candidate','reason':'新增阅读提案，未自动视为已验证'}]}
            db['ideas'][iid]=i;p['idea_ids'].append(iid);pending['data/ideas/'+iid+'.json']=encoded(i)
        pending['data/papers/'+pid+'.json']=encoded(p)
        # Stage bytes before writing; preserve changed metadata in an append-only event journal.
        event={'time':stamp,'operation':'ingest','paper_id':pid,'analysis_id':aid,'before':db['papers'].get(pid),'after':p}
        event_path='history/'+stamp.replace(':','-')+'-'+aid+'.json'
        pending[event_path]=encoded(event)
        old={}
        try:
            for name,raw in pending.items():
                path=safe_path(root,name);old[name]=path.read_bytes() if path.exists() else None;atomic(path,raw)
        except Exception:
            for name,raw in old.items():
                path=safe_path(root,name)
                if raw is None:path.unlink(missing_ok=True)
                else:atomic(path,raw)
            raise
        return {'action':'appended' if pid in db['papers'] else 'created','paper_id':pid,'analysis_id':aid,'idea_ids':p['idea_ids']}

def rate(root: Path, target: str, score, reason: str, assessor='user'):
    value=numeric_score(score)
    if not text(reason):raise ValueError('A score needs a rationale')
    with locked(root):
        db=records(root)
        if target.startswith('I') and target in db['ideas']:kind='ideas';r=db[kind][target];scope='specific_direction'
        else:kind='papers';r=find_paper(db,target);scope='paper_main_followup'
        before=json.loads(json.dumps(r));entry={'date':today(),'recorded_at':now(),'score':value,'scale':10,'scope':scope,'reason':reason,'assessor':assessor,'not_paper_quality':True}
        r.setdefault('ratings',[]).append(entry);r['updated_at']=today()
        atomic(root/'history'/f'{entry["recorded_at"].replace(":","-")}-{r["id"]}-rating.json',encoded({'operation':'rate','before':before,'after':r}),False)
        atomic(root/'data'/kind/(r['id']+'.json'),encoded(r));return {'id':r['id'],'rating':entry,'history_preserved':True}

def set_state(root: Path, iid: str, state: str, reason: str):
    if state not in STATES or not text(reason):raise ValueError('Valid state and reason required')
    with locked(root):
        db=records(root)
        if iid not in db['ideas']:raise ValueError('Unknown idea ID')
        i=db['ideas'][iid];old=i['status'];i['status']=state;i['updated_at']=today();i['state_history'].append({'date':today(),'status':state,'reason':reason,'previous':old})
        atomic(root/'data/ideas'/(iid+'.json'),encoded(i));return {'id':iid,'state':state,'does_not_certify_scientific_success':True}

def link_idea(root: Path, iid: str, paper_query: str):
    """Add a second provenance link without duplicating a direction."""
    with locked(root):
        db=records(root)
        if iid not in db['ideas']: raise ValueError('Unknown idea ID')
        i=db['ideas'][iid]; p=find_paper(db,paper_query)
        if p['id'] in i['paper_ids']: return {'action':'unchanged','idea_id':iid,'paper_id':p['id']}
        before_i=json.loads(json.dumps(i));before_p=json.loads(json.dumps(p))
        i['paper_ids'].append(p['id']);p['idea_ids'].append(iid)
        i['updated_at']=p['updated_at']=today()
        stamp=now().replace(':','-')
        atomic(root/'history'/f'{stamp}-{iid}-link.json',encoded({'operation':'link','before_idea':before_i,'before_paper':before_p,'paper_id':p['id'],'idea_id':iid}),False)
        atomic(root/'data/ideas'/(iid+'.json'),encoded(i))
        atomic(root/'data/papers'/(p['id']+'.json'),encoded(p))
        return {'action':'linked','idea_id':iid,'paper_id':p['id'],'independent_validation_implied':False}

def payload(root: Path):
    db=records(root)
    for a in db['analyses'].values():a['body']=safe_path(root,a['note_path']).read_text()
    return {'config':load(root/'library.json'),**{k:list(v.values()) for k,v in db.items()},'collections':load(root/'data/collections.json')['collections'] if (root/'data/collections.json').exists() else []}

def build(root: Path=ROOT):
    report=validate(root)
    if not report['passed']:raise ValueError('; '.join(report['errors']))
    data=payload(root);template=(root/'assets/browser.html').read_text()
    blob=json.dumps(data,ensure_ascii=False,allow_nan=False).replace('<','\\u003c').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
    atomic(root/'index.html',template.replace('/*__LIBRARY_DATA__*/',blob).encode())
    atomic(root/'catalog.json',encoded(data))
    lookup={p['id']:p for p in data['papers']}
    lines=['# 论文分析库索引','',f"{len(data['papers'])}篇去重论文；{len(data['analyses'])}份分析记录；{len(data['ideas'])}条方向/迁移提问。",'',
           '数值为有来源的后续研究潜力历史分；未评分不等于0分。详细浏览请打开根目录index.html。','',
           '| 编号 | 论文 | 主题 | 分析数 | 方向数 | 主线历史潜力 |','|---|---|---|---:|---:|---:|']
    for p in data['papers']:
        score=str(p['ratings'][-1]['score']) if p.get('ratings') else '未评分'
        lines.append(f"| {p['id']} | [{p['short_name'].replace('|','/')}](views/{p['id']}.md) | {' / '.join(p['topics'])} | {len(p['analysis_ids'])} | {len(p['idea_ids'])} | {score} |")
        page=[f"# {p['title']}",'',f"编号：{p['id']}；别名：{'、'.join(p['aliases'])}",'',f'主线历史潜力：{score}；不是论文质量分。','', '[返回索引](../INDEX.md)','']
        for a in data['analyses']:
            if a['paper_id']==p['id']:
                page += [f"## {a['id']} · {a['kind']}",f"框架版本：{a.get('framework_version') or '源记录未指定'}；日期：{a['analyzed_at']}",a['summary'],f"[阅读完整记录](../{a['note_path']})",'']
        for i in data['ideas']:
            if p['id'] in i['paper_ids']:page += [f"## {i['id']} · {i['title']}",i['question'],'首项证据：'+i['first_evidence'],'结果—行动：'+'；'.join(i['decision_branches']),'状态：'+i['status'],'']
        atomic(root/'views'/(p['id']+'.md'),'\n'.join(page).encode())
    atomic(root/'INDEX.md','\n'.join(lines).encode())
    idea_lines=['# 后续研究方向池','','此表包括具体研究方向和迁移提问；不能把提问视为已验证的新颖项目。','']
    for i in data['ideas']:
        parents='、'.join(f"[{p} · {lookup[p]['short_name']}](views/{p}.md)" for p in i['paper_ids'])
        idea_lines += [f"## {i['id']} · {i['title']}",f"来源：{parents}；类型：{i['kind']}；状态：{i['status']}",'',i['question'],'','最小证据：'+i['first_evidence'],'','结果—行动：'+'；'.join(i['decision_branches']),'']
    atomic(root/'IDEAS.md','\n'.join(idea_lines).encode());return report

def template_record():
    return {'title':'填写论文标题','short_name':'','paper_id':None,'arxiv':None,'doi':None,'paper_url':'','aliases':[],'topics':['OPD'],'tags':[],
            'analyzed_at':today(),'framework_version':'0.4.0','paper_version':None,'venue':None,'source_description':'本次阅读分析；请注明材料版本与核验范围',
            'summary':'填写核心贡献','sections':{'原有局限':'','作者改变了什么':'','新增结果/组合增量':'','证据与边界':''},
            'codings':[],'analysis_markdown':'# 论文分析\n\n请填入完整分析正文。\n','ideas':[]}

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,default=ROOT)
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('validate');sub.add_parser('build')
    s=sub.add_parser('search');s.add_argument('query',nargs='?',default='');s.add_argument('--topic');s.add_argument('--min-score',type=float)
    s=sub.add_parser('show');s.add_argument('id')
    s=sub.add_parser('template');s.add_argument('--out',type=Path,required=True)
    s=sub.add_parser('add');s.add_argument('intake',type=Path)
    s=sub.add_parser('rate');s.add_argument('id');s.add_argument('score',type=float);s.add_argument('--reason',required=True);s.add_argument('--assessor',default='user')
    s=sub.add_parser('status');s.add_argument('id');s.add_argument('state',choices=sorted(STATES));s.add_argument('--reason',required=True)
    s=sub.add_parser('link');s.add_argument('idea_id');s.add_argument('paper_id')
    s=sub.add_parser('backup');s.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();root=args.root.resolve()
    try:
        if args.command=='validate':result=validate(root)
        elif args.command=='build':result=build(root)
        elif args.command=='template':atomic(args.out,encoded(template_record()),False);result={'created':str(args.out)}
        elif args.command=='add':result=ingest(root,load(args.intake));build(root)
        elif args.command=='rate':result=rate(root,args.id,args.score,args.reason,args.assessor);build(root)
        elif args.command=='status':result=set_state(root,args.id,args.state,args.reason);build(root)
        elif args.command=='link':result=link_idea(root,args.idea_id,args.paper_id);build(root)
        elif args.command=='backup':
            if args.out.exists():raise FileExistsError(args.out)
            args.out.parent.mkdir(parents=True,exist_ok=True)
            with zipfile.ZipFile(args.out,'x',zipfile.ZIP_DEFLATED) as z:
                for p in sorted(root.rglob('*')):
                    if p.is_file() and not p.is_symlink() and p.resolve()!=args.out.resolve() and not any(x in {'.git','__pycache__','.library.lock'} for x in p.relative_to(root).parts):z.write(p,Path(root.name)/p.relative_to(root))
            result={'backup':str(args.out),'includes_research_ideas':True}
        elif args.command=='show':
            db=records(root);result=db['ideas'].get(args.id) or find_paper(db,args.id)
        else:
            data=payload(root);result=[]
            for p in data['papers']:
                a=[v for v in data['analyses'] if v['paper_id']==p['id']];ii=[v for v in data['ideas'] if p['id'] in v['paper_ids']]
                hay=json.dumps([p,a,ii],ensure_ascii=False).casefold()
                if args.query.casefold() not in hay or (args.topic and args.topic not in p['topics']):continue
                score=p['ratings'][-1]['score'] if p.get('ratings') else None
                if args.min_score is not None and (score is None or score<args.min_score):continue
                result.append({'id':p['id'],'title':p['title'],'aliases':p['aliases'],'score':score,'analyses':len(a),'ideas':len(ii)})
        print(json.dumps(result,ensure_ascii=False,indent=2));return 1 if isinstance(result,dict) and result.get('passed') is False else 0
    except (OSError,ValueError,TypeError,KeyError) as e: print('ERROR: '+str(e),file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())
