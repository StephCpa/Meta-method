"""Regression checks for this append-only import; not scientific validation."""
import hashlib,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import library as L

class RLVRImportTests(unittest.TestCase):
    def setUp(self):
        self.report=L.load(ROOT/'IMPORT-RLVR14-20261001.json')
        self.db=L.records(ROOT)
    def test_import_identity_and_counts(self):
        r=self.report
        self.assertEqual((r['added_papers'],r['added_analyses'],r['added_ideas']),(14,28,40))
        self.assertEqual(r['counts_after']['papers']-r['counts_before']['papers'],14)
        self.assertEqual(len(set(r['paper_map'].values())),14)
        self.assertEqual(len(r['xd_merge_map']),14)
        for alias,pid in r['paper_map'].items():
            self.assertEqual(L.find_paper(self.db,alias)['id'],pid)
            self.assertEqual(self.db['papers'][pid]['dataset_role'],'development')
        for alias,row in r['xd_merge_map'].items():
            self.assertEqual(L.find_paper(self.db,alias)['id'],row['paper_id'])
            self.assertIn(row['analysis_id'],self.db['papers'][row['paper_id']]['analysis_ids'])
        self.assertEqual(len(set(r['idea_map'].values())),40)
    def test_source_text_and_notes_are_exact(self):
        base=ROOT/'sources/rlvr14-20261001-original'
        manifest=L.load(base/'TEXT-MANIFEST.json')
        self.assertEqual(manifest['original_bundle_sha256'],'36f8f1007b8444a5e0d6f44728106af2f09bace3d25b5a5a5dbc5c772223f4cd')
        for item in manifest['files']:
            self.assertEqual(hashlib.sha256((base/item['path']).read_bytes()).hexdigest(),item['sha256'])
        ids=list(self.report['analysis_map'].values())+[x['analysis_id'] for x in self.report['xd_merge_map'].values()]
        self.assertEqual(len(ids),28)
        for aid in ids:
            a=self.db['analyses'][aid]
            ref=next(x for x in a['source_refs'] if x['source_id']=='SRC-RLVR14-20261001')
            self.assertEqual((ROOT/a['note_path']).read_bytes(),(base/ref['locator']).read_bytes())
            self.assertFalse(a['paper_experiment_reproduced'])
            self.assertFalse(a['independent_recoding'])
            self.assertEqual(a['status'],'imported_not_reverified')
    def test_historical_ratings_and_idea_roles_not_promoted(self):
        ratings=[r for pid in self.report['paper_map'].values() for r in self.db['papers'][pid]['ratings']]
        self.assertEqual(len(ratings),10)
        for r in ratings:
            self.assertTrue(r['historical_import'])
            self.assertTrue(r['not_paper_quality'])
            self.assertEqual(r['date_semantics'],'import_date_not_new_assessment')
        for iid in self.report['idea_map'].values():
            i=self.db['ideas'][iid]
            self.assertEqual(i['ratings'],[])
            self.assertEqual(i['source_role'],'proposal')
            self.assertEqual(i['dataset_role'],'development')
            self.assertEqual(i['execution_status'],'historical_status_imported_not_rerun')
        self.assertFalse(self.report['scientific_reverification_performed'])
        self.assertFalse(self.report['old_calibrations_rerun'])

if __name__=='__main__':unittest.main()
