#!/usr/bin/env python3
"""One-shot native library import. Does not rerun scientific experiments."""
from pathlib import Path
import base64, hashlib, importlib.util, json, lzma

REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / 'paper-library'
BASE = '6e017d7a2a55db683d7f89e2eefdafd1aedf52bb'
RAW_SHA = 'd5cd941c8e7ac93d42403e262870e86ac84ad5cf4d0cd54a19b0741ce49d1f3f'
BUNDLE_SHA = '36f8f1007b8444a5e0d6f44728106af2f09bace3d25b5a5a5dbc5c772223f4cd'
PREFIX = 'sources/rlvr14-20261001-original'
SOURCE_ID = 'SRC-RLVR14-20261001'
DATE = '2026-10-01'

def check(ok, message):
    if not ok: raise RuntimeError(message)

def sha(b): return hashlib.sha256(b).hexdigest()
def readj(p): return json.loads(p.read_text(encoding='utf-8'))
def save(p, value): lib.atomic(p, lib.encoded(value))

def main():
    global lib
    spec=importlib.util.spec_from_file_location('native_library',ROOT/'tools/library.py')
    lib=importlib.util.module_from_spec(spec);spec.loader.exec_module(lib)
    before=lib.records(ROOT)
    check({k:len(v) for k,v in before.items() if k!='sources'}=={'papers':57,'analyses':71,'ideas':44},'Unexpected base counts; stop for reconciliation')
    immutable={p:sha(p.read_bytes()) for folder in ['notes','sources','data/analyses','data/ideas','data/sources'] for p in (ROOT/folder).rglob('*') if p.is_file()}
    parts=sorted(Path(__file__).parent.glob('payload-*.b64'))
    check(len(parts)==6,'Expected six payload parts')
    raw=lzma.decompress(base64.b64decode(''.join(p.read_text().strip() for p in parts),validate=True))
    check(sha(raw)==RAW_SHA,'Transport checksum mismatch')
    source_files=json.loads(raw)
    papers=json.loads(source_files['data/papers.json'])['papers']
    directions=json.loads(source_files['data/directions.json'])['directions']
    author_moves={x['paper_id']:x for x in json.loads(source_files['data/author_moves.json'])['author_moves']}
    xd=json.loads(source_files['data/xd_merge_candidates.json'])['merge_candidates']
    check((len(papers),len(directions),len(xd))==(14,40,14),'Unexpected supplied record counts')
    manifest=[]
    for rel,content in sorted(source_files.items()):
        check(isinstance(content,str) and Path(rel).suffix in {'.json','.md'},'Only supplied analysis text allowed')
        out=lib.safe_path(ROOT,PREFIX+'/'+rel)
        lib.atomic(out,content.encode('utf-8'),False)
        manifest.append({'path':rel,'sha256':sha(content.encode('utf-8')),'bytes':len(content.encode('utf-8'))})
    manifest_rel=PREFIX+'/TEXT-MANIFEST.json'
    source_manifest={'source':'Meta_method_RLVR14_library_import_20261001.zip','original_bundle_sha256':BUNDLE_SHA,'transport_raw_sha256':RAW_SHA,'files':manifest,'scientific_reverification_performed':False,'scope':'All prepared paper/idea/author metadata, 28 consolidated notes, four progress notes and five original text cards. Binary calibration ZIPs remain in the original conversation handoff; not executed or mirrored by this analysis-text import. Historical archive statements refer to that handoff, not to this repository directory.'}
    save(ROOT/manifest_rel,source_manifest)
    save(ROOT/'data/sources'/f'{SOURCE_ID}.json',{'id':SOURCE_ID,'kind':'conversation_import_manifest','path':manifest_rel,'sha256':sha((ROOT/manifest_rel).read_bytes()),'description':'本对话RLVR001–014及XD补充的原始文本快照；历史报告不等于本次新核验。','imported_at':lib.now(),'reverified_in_library_build':False})
    paper_map={};analysis_map={};idea_map={};notes=[]
    state_map={'awaiting_data':'checking','awaiting_materials':'paused','blocked_fulltext':'paused','blocked_materials':'paused','calibrated_model_based':'checking','parked':'paused','planned':'candidate','scope_limited_stop':'paused'}
    def codes_for(p):
        out=[]
        for role,key in [('author','author_codes'),('review','review_codes')]:
            for c in p.get(key,[]):
                out.append({'code':c['code'],'role':role,'anchor':c.get('locator') or f"{p['id']}既有对话收敛分析的审查段；本次未重核原论文",'rationale':c.get('rationale',''),'verification_status':'inherited_candidate_not_reverified_in_import'})
        return out
    def finish_analysis(result, source_path, origin_id):
        aid=result['analysis_id'];p=ROOT/'data/analyses'/f'{aid}.json';a=readj(p)
        a['preservation']='structured_conversation_digest'
        a['dataset_role']='development';a['used_for_framework_development']=True
        a['status']='imported_not_reverified';a['original_analysis_id']=origin_id
        a['source_refs'].append({'source_id':SOURCE_ID,'locator':source_path})
        a['organizing_framework_version']='0.4.0'
        save(p,a);notes.append((aid,source_path))
    for p in papers:
        rid=p['id'];am=author_moves[rid];ds=[x for x in directions if x['paper_id']==rid]
        rel=f'analyses/rlvr/{rid}.md'
        intake={'title':p['title'],'short_name':p['short_name'],'paper_url':p['primary_url'],
                'arxiv':p['canonical_key'].split(':',1)[1] if p['canonical_key'].startswith('arxiv:') else None,
                'aliases':[rid,'RLVR/'+p['legacy_case_id']],'topics':['RLVR／后训练'],'tags':['development','rlvr-dialogue-import'],
                'analyzed_at':DATE,'framework_version':'0.4.0' if int(rid[-3:])>=13 else None,
                'paper_version':p.get('reviewed_version'),'source_description':'本对话已提供收敛分析的导入；不重新核验论文、数学结论或真实模型实验。'+p['current_state'],
                'summary':am['change'],'sections':{'原有局限':am['original_opportunity'],'作者改变了什么':am['change'],'新增结果/组合增量':am['increment'],'证据与边界':p['current_state']},
                'codings':codes_for(p),'analysis_markdown':source_files[rel],
                'ideas':[{'title':x['title'],'question':x['question'],'first_evidence':x['first_artifact'],'decision_branches':[x['stop_or_rewrite']]} for x in ds]}
        result=lib.ingest(ROOT,intake)
        check(result['action']=='created','Primary paper already exists; stop rather than duplicate')
        pid=result['paper_id'];paper_map[rid]=pid;analysis_map[rid]=result['analysis_id']
        finish_analysis(result,rel,f'AN-{rid}-20261001')
        path=ROOT/'data/papers'/f'{pid}.json';native=readj(path)
        native['reading_status']='historical_partial_material_review' if rid=='RLVR006' else 'inherited_conversation_analysis'
        native['legacy_case_namespace']='rlvr_post_training_dialogue';native['legacy_case_id']=p['legacy_case_id']
        native['source_current_state']=p['current_state'];native['used_for_framework_development']=True
        if p['canonical_key'].startswith('openreview:'):native['identifiers']['openreview']=p['canonical_key'].split(':',1)[1]
        rating=p.get('historical_potential_score')
        if rating:
            native['ratings'].append({'date':DATE,'recorded_at':lib.now(),'score':rating['value'],'scale':10,'scope':'paper_main_followup','reason':rating['meaning']+'；来源：'+rating['provenance'],'assessor':'ChatGPT，本对话历史主线评价；导入未重评','not_paper_quality':True,'historical_import':True,'original_assessment_date':None,'date_semantics':'import_date_not_new_assessment','source_id':SOURCE_ID})
        save(path,native)
        for iid,old in zip(result['idea_ids'],ds):
            path=ROOT/'data/ideas'/f'{iid}.json';idea=readj(path)
            idea.update({'kind':old['kind'],'status':state_map[old['work_status']],'original_direction_id':old['id'],'source_work_status':old['work_status'],'priority':old['priority'],'proposed_change':old['proposed_change'],'strong_controls':old['strong_controls'],'novelty_boundary':old['novelty_boundary'],'execution_status':'historical_status_imported_not_rerun','dataset_role':'development','source_role':'proposal','research_claim_status':old['research_claim_status']})
            reason='按原记录映射工作状态，不认证科学有效性。'+old['stop_or_rewrite']
            if old['work_status']=='scope_limited_stop':reason='直接上下文新增训练干预已停止；同一记录中的主动工具迁移尚未运行。不得解释成整项证据依赖研究已失败。'
            idea['state_history'].append({'date':DATE,'status':idea['status'],'previous':'candidate','source_status':old['work_status'],'reason':reason})
            save(path,idea);idea_map[old['id']]=iid
    xd_map={}
    for item in xd:
        db=lib.records(ROOT);existing=lib.find_paper(db,item['existing_id_hint'])
        ar=item['canonical_key'].split(':',1)[1] if item['canonical_key'].startswith('arxiv:') else None
        if ar and existing['identifiers'].get('arxiv'):check(ar==existing['identifiers']['arxiv'],'XD canonical mismatch')
        rel=item['analysis_path'];body=source_files[rel]
        result=lib.ingest(ROOT,{'paper_id':existing['id'],'title':item['title'],'paper_url':item['primary_url'],'arxiv':ar,'aliases':['RLVR-XD/'+item['source_case_id']],'topics':['跨领域'],'tags':['rlvr-dialogue-supplement','development'],'analyzed_at':DATE,'framework_version':None,'source_description':'本对话跨领域历史补充；复用已有论文实体，原分析和编码不覆盖，本次未重核奖项/原文。','summary':'本对话对研究对象、证据终点和Meta-method适用条件的补充记录。','codings':[],'analysis_markdown':body,'ideas':[]})
        check(result['action']=='appended','Expected XD append to existing entity')
        finish_analysis(result,rel,item['id']);xd_map[item['existing_id_hint']]={'paper_id':existing['id'],'analysis_id':result['analysis_id']}
    collections=readj(ROOT/'data/collections.json')
    check(not any(x['id']=='RLVR14' for x in collections['collections']),'Collection collision')
    collections['collections'].append({'id':'RLVR14','name':'本对话RLVR／后训练14篇（development）','paper_ids':list(paper_map.values())})
    collections['collections'].append({'id':'RLVR-XD14','name':'本对话跨领域补充14份（复用已有论文）','paper_ids':[x['paper_id'] for x in xd_map.values()]})
    save(ROOT/'data/collections.json',collections)
    config=readj(ROOT/'library.json');config['source_cutoff']=DATE;config['last_imported_at']=lib.now();config['last_import_report']='IMPORT-RLVR14-20261001.json';save(ROOT/'library.json',config)
    report=lib.validate(ROOT);check(report['passed'],str(report['errors']))
    check({k:report['counts'][k] for k in ('papers','analyses','ideas')}=={'papers':71,'analyses':99,'ideas':84},'Unexpected merged counts')
    for p,oldsha in immutable.items():check(sha(p.read_bytes())==oldsha,f'Existing immutable record changed: {p}')
    for pid,p in before['papers'].items():
        after=readj(ROOT/'data/papers'/f'{pid}.json')
        for field in ('analysis_ids','idea_ids','ratings'):
            check(after[field][:len(p[field])]==p[field],f'Existing history changed: {pid}/{field}')
    for aid,rel in notes:check((ROOT/'notes'/f'{aid}.md').read_bytes()==source_files[rel].encode(),f'Body changed: {aid}')
    lib.build(ROOT)
    native_before_build={p.relative_to(ROOT).as_posix():sha(p.read_bytes()) for p in [ROOT/'INDEX.md',ROOT/'IDEAS.md',ROOT/'index.html',ROOT/'catalog.json',*(ROOT/'views').glob('*.md')]}
    lib.build(ROOT)
    check(all(sha((ROOT/p).read_bytes())==v for p,v in native_before_build.items()),'Build not deterministic')
    readme=REPO/'README.md';text=readme.read_text();text=text.replace('57篇去重论文、71份分析／补充记录、44条方向或迁移提问','71篇去重论文、99份分析／补充记录、84条方向、观察轴或迁移提问');lib.atomic(readme,text.encode())
    p=ROOT/'README.md';text=p.read_text();text=text.replace('来源截止日期：2026-09-30','来源截止日期：2026-10-01')
    text=text.replace('## 当前实际导入','## 首批导入（历史记录）',1)
    marker='## 三层数据，避免重复和混淆'
    addition='## 2026-10-01：本对话追加\n\n当前总计 **71篇论文、99份分析、84条方向／观察轴／迁移提问**。本批新增14篇RLVR论文、14份收敛分析与40条候选；另为已有14篇跨领域论文各追加一份补充，不重复建论文。保留10个历史主线分，不给未评分条目补分。\n\n原分析、评分和来源不覆盖。原记录中的模拟、用户报告实证与未执行提案保持区分；本次只验证导入和工程完整性。校准二进制ZIP不镜像到分析库，仍见原对话交接包；相应原始文本已保留。详情见[本批导入报告](IMPORT-RLVR14-20261001.md)。\n\n'
    check(marker in text,'README insertion anchor missing');text=text.replace(marker,addition+marker,1);lib.atomic(p,text.encode())
    md=['# RLVR14 追加导入记录','',f'基线提交：`{BASE}`。框架版本不变，仍为0.4.0。','', '新增14论文、28分析、40方向记录；跨领域14篇复用原实体。已有正文、分析、方向、来源、评分均保留。','', '本轮没有核验论文科学结论、没有执行真实模型或旧校准脚本。原始阶段声明仍属历史材料。','', '源文本与原结构快照：`'+PREFIX+'`；二进制校准ZIP留在原始对话交接包，并未在此镜像。','', '| 本对话编号 | 论文库ID | 分析ID |','|---|---|---|']
    for rid,pid in paper_map.items():md.append(f'| {rid} | [{pid}](views/{pid}.md) | [{analysis_map[rid]}](notes/{analysis_map[rid]}.md) |')
    md+=['','## 本批边界','', '- Case002：直接上下文范围停止新增训练干预；576生成是用户报告，原始日志未取得；事后排除与原始结果分开。','- Case004：v0.2/P6和后续组大小/奖励语义限制均按提供记录保留；无作者训练复现。','- Case006：全文未完成核验，代码和机制主张仍为候选。','- 历史评分为主线优先级，不是论文质量，不是本次重评。','- 所有材料仍为development，不增加独立有效性验证次数。','']
    lib.atomic(ROOT/'IMPORT-RLVR14-20261001.md','\n'.join(md).encode(),False)
    summary={'base_commit':BASE,'imported_at':lib.now(),'original_bundle_sha256':BUNDLE_SHA,'text_payload_sha256':RAW_SHA,'counts_before':{k:len(v) for k,v in before.items()},'counts_after':report['counts'],'added_papers':14,'added_analyses':28,'added_ideas':40,'paper_map':paper_map,'analysis_map':analysis_map,'idea_map':idea_map,'xd_merge_map':xd_map,'historical_ratings_imported':10,'source_text_files_preserved':len(manifest),'preexisting_immutable_files_preserved':len(immutable),'scientific_reverification_performed':False,'old_calibrations_rerun':False,'native_validation_passed':True,'native_build_deterministic':True,'binary_calibration_archives_mirrored':False}
    save(ROOT/'IMPORT-RLVR14-20261001.json',summary)
    save(ROOT/'history'/'rlvr14-20261001-import-mapping.json',{'operation':'append_from_portable_bundle','summary':summary})
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
