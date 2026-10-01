"""Engineering regression tests; not paper replication or a test of research potential."""
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import library as L

class Base(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        for d in ['data/papers','data/analyses','data/ideas','data/sources','notes','sources','history','assets']:(self.root/d).mkdir(parents=True,exist_ok=True)
        (self.root/'library.json').write_text('{}')
        (self.root/'data/collections.json').write_text('{"collections":[]}')
        shutil.copy(ROOT/'assets/browser.html',self.root/'assets/browser.html')
    def tearDown(self):self.tmp.cleanup()
    def sample(self):
        return {'title':'Example study','arxiv':'2601.12345v2','paper_url':'https://arxiv.org/abs/2601.12345','aliases':['Example'],
          'topics':['OPD'],'summary':'A contribution','analysis_markdown':'# Analysis\nA body','source_description':'Constructed test input, not a paper result',
          'ideas':[{'title':'Check an assumption','first_evidence':'An exact toy check','decision_branches':['If refuted, narrow claim']}],
          'framework_version':'0.4.0'}
    def add(self):return L.ingest(self.root,self.sample())

class ImportTests(Base):
    def test_create_paper_analysis_idea(self):
        r=self.add();self.assertEqual(r['paper_id'],'P0001');self.assertTrue(L.validate(self.root)['passed'])
    def test_arxiv_version_dedup(self):
        self.add();s=self.sample();s['arxiv']='2601.12345v3';s['analysis_markdown']='# Second analysis';r=L.ingest(self.root,s)
        self.assertEqual(r['action'],'appended');d=L.records(self.root);self.assertEqual(len(d['papers']),1);self.assertEqual(len(d['analyses']),2)
    def test_identical_analysis_idempotent(self):
        self.add();r=self.add();self.assertEqual(r['action'],'unchanged');self.assertEqual(len(L.records(self.root)['ideas']),1)
    def test_old_body_is_preserved(self):
        r=self.add();s=self.sample();s['analysis_markdown']='Another analysis';L.ingest(self.root,s)
        self.assertEqual((self.root/'notes/A0001.md').read_text(),self.sample()['analysis_markdown'])
    def test_same_title_requires_explicit_match(self):
        self.add();s=self.sample();s['arxiv']=None;s['paper_url']='';s['analysis_markdown']='Different'
        with self.assertRaisesRegex(ValueError,'Same title'):L.ingest(self.root,s)
    def test_explicit_alias_append(self):
        self.add();s=self.sample();s['paper_id']='Example';s['arxiv']=None;s['paper_url']='';s['analysis_markdown']='New'
        self.assertEqual(L.ingest(self.root,s)['action'],'appended')
    def test_conflicting_id_is_rejected(self):
        self.add();s=self.sample();s['paper_id']='P0001';s['arxiv']='2601.99999';s['analysis_markdown']='New'
        with self.assertRaisesRegex(ValueError,'conflict'):L.ingest(self.root,s)
    def test_duplicate_alias_rejected(self):
        self.add();s=self.sample();s['title']='Other';s['arxiv']='2601.99999';s['analysis_markdown']='New'
        with self.assertRaisesRegex(ValueError,'Alias'):L.ingest(self.root,s)
    def test_nonobject_intake(self):
        with self.assertRaises(ValueError):L.ingest(self.root,[])
    def test_invalid_topics_rejected(self):
        s=self.sample();s['topics']='OPD'
        with self.assertRaises(ValueError):L.ingest(self.root,s)
    def test_unsafe_link_rejected(self):
        s=self.sample();s['paper_url']='javascript:alert(1)'
        with self.assertRaises(ValueError):L.ingest(self.root,s)
    def test_unknown_code_rejected(self):
        s=self.sample();s['codings']=[{'code':'M99','role':'author','anchor':'x'}]
        with self.assertRaises(ValueError):L.ingest(self.root,s)
    def test_codes_keep_roles(self):
        s=self.sample();s['codings']=[{'code':'M2','role':'author','anchor':'section 2'},{'code':'M14','role':'proposal','anchor':'our proposal'}]
        L.ingest(self.root,s);roles=[c['role'] for c in L.records(self.root)['analyses']['A0001']['codings']]
        self.assertEqual(roles,['author','proposal'])
    def test_unrated_is_not_zero(self):
        self.add();p=L.records(self.root)['papers']['P0001'];self.assertEqual(p['ratings'],[])
    def test_rating_history_preserved(self):
        self.add();L.rate(self.root,'P0001',8,'Initial view');L.rate(self.root,'P0001',7,'New limitation')
        self.assertEqual([r['score'] for r in L.records(self.root)['papers']['P0001']['ratings']],[8,7])
    def test_idea_rating_not_inherited(self):
        self.add();L.rate(self.root,'P0001',9,'Main route')
        self.assertEqual(L.records(self.root)['ideas']['I0001']['ratings'],[])
    def test_idea_independent_rating(self):
        self.add();L.rate(self.root,'I0001',8,'Specific route');self.assertEqual(L.records(self.root)['papers']['P0001']['ratings'],[])
    def test_nan_score_rejected(self):
        with self.assertRaises(ValueError):L.numeric_score(float('nan'))
    def test_boolean_score_rejected(self):
        with self.assertRaises(ValueError):L.numeric_score(True)
    def test_out_of_range_score(self):
        with self.assertRaises(ValueError):L.numeric_score(11)
    def test_state_history(self):
        self.add();L.set_state(self.root,'I0001','paused','Need data');i=L.records(self.root)['ideas']['I0001'];self.assertEqual(len(i['state_history']),2)
    def test_note_tampering_detected(self):
        self.add();(self.root/'notes/A0001.md').write_text('tampered');self.assertFalse(L.validate(self.root)['passed'])
    def test_source_tampering_detected(self):
        self.add();(self.root/'sources/S0001.json').write_text('{}');self.assertFalse(L.validate(self.root)['passed'])
    def test_broken_backlink_detected(self):
        self.add();p=L.load(self.root/'data/papers/P0001.json');p['analysis_ids']=[];(self.root/'data/papers/P0001.json').write_bytes(L.encoded(p));self.assertFalse(L.validate(self.root)['passed'])
    def test_history_before_is_unmodified(self):
        self.add();s=self.sample();s['analysis_markdown']='New';L.ingest(self.root,s)
        e=sorted((self.root/'history').glob('*A0002.json'))[0];v=L.load(e);self.assertEqual(v['before']['analysis_ids'],['A0001']);self.assertEqual(len(v['after']['analysis_ids']),2)
    def test_lock_prevents_concurrent_write(self):
        with L.locked(self.root):
            with self.assertRaises(FileExistsError):self.add()
    def test_build_is_not_ingest(self):
        self.add();a=L.records(self.root);L.build(self.root);L.build(self.root);self.assertEqual(a,L.records(self.root))
    def test_html_escapes_script_injection(self):
        s=self.sample();s['analysis_markdown']='</script><script>alert(1)</script>';L.ingest(self.root,s);L.build(self.root)
        page=(self.root/'index.html').read_text();self.assertNotIn('</script><script>alert(1)',page);self.assertIn('\\u003c/script',page)

class RelationTests(Base):
    def test_cross_paper_link_and_backlink(self):
        self.add();s=self.sample();s.update(title='Second study', arxiv='2601.54321', aliases=['Second'], analysis_markdown='Second body', ideas=[])
        L.ingest(self.root,s);L.link_idea(self.root,'I0001','P0002');d=L.records(self.root)
        self.assertEqual(d['ideas']['I0001']['paper_ids'],['P0001','P0002']);self.assertIn('I0001',d['papers']['P0002']['idea_ids']);self.assertTrue(L.validate(self.root)['passed'])
    def test_duplicate_link_does_not_duplicate_idea(self):
        self.add();self.assertEqual(L.link_idea(self.root,'I0001','P0001')['action'],'unchanged')

class LibraryTests(unittest.TestCase):
    def test_seed_integrity(self):self.assertTrue(L.validate(ROOT)['passed'])
    def test_seed_unique_count(self):
        # Preserve the original 57-paper fixture while allowing append-only growth.
        collections=L.load(ROOT/'data/collections.json')['collections']
        seed_ids=set().union(*(set(c['paper_ids']) for c in collections if c['id'] in {'MAS10','OPD24','XD14','OPD-T10'}))
        self.assertEqual(len(seed_ids),57)
        self.assertTrue(seed_ids.issubset(L.records(ROOT)['papers']))
    def test_duplicate_eopd_keeps_both_ids(self):
        db=L.records(ROOT);p=L.find_paper(db,'OPD14');self.assertIn('OPD-T09',p['aliases']);self.assertGreaterEqual(len(p['analysis_ids']),2)
    def test_original_papers_absent(self):self.assertEqual(list(ROOT.rglob('*.pdf')),[])
    def test_only_historical_ratings(self):
        d=L.records(ROOT)
        collections=L.load(ROOT/'data/collections.json')['collections']
        seed_ids=set().union(*(set(c['paper_ids']) for c in collections if c['id'] in {'MAS10','OPD24','XD14','OPD-T10'}))
        self.assertEqual(sum(bool(d['papers'][pid]['ratings']) for pid in seed_ids),10)
        self.assertEqual(sum(bool(i['ratings']) for i in d['ideas'].values()),0)
    def test_arxiv_normalization(self):self.assertEqual(L.norm_arxiv('https://arxiv.org/pdf/2601.12345v9.pdf'),'2601.12345')
    def test_doi_normalization(self):self.assertEqual(L.norm_doi('https://doi.org/10.1234/ABc'),'10.1234/abc')
    def test_path_traversal(self):
        with self.assertRaises(ValueError):L.safe_path(ROOT,'../outside')
    def test_new_output_no_clobber(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x';L.atomic(p,b'a',False)
            with self.assertRaises(FileExistsError):L.atomic(p,b'b',False)
            self.assertEqual(p.read_bytes(),b'a')

if __name__=='__main__':unittest.main()
