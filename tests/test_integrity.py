"""Engineering regression tests, not an evaluation of research effectiveness."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from validate import validate_claim, validate_repo, duplicate_ids, check_links, load, PROFILES
from freeze import build_manifest

class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = {s['id'] for s in load(ROOT / 'data/sources.json')['sources']}
        cls.base = load(ROOT / 'examples/claims.json')['claims'][0]
    def claim(self): return copy.deepcopy(self.base)
    def test_repository_integrity(self): self.assertTrue(validate_repo()['passed'], validate_repo()['errors'])
    def test_six_evidence_profiles(self):
        cards = load(ROOT / 'examples/claims.json')['claims']
        self.assertEqual({p for c in cards for p in c['contribution_types']}, PROFILES)
    def test_all_examples_valid(self):
        for c in load(ROOT / 'examples/claims.json')['claims']:
            with self.subTest(c=c['id']): self.assertEqual(validate_claim(c, self.sources), [])
    def test_empty_code_list_is_valid(self):
        c=self.claim(); c['codings']=[]; self.assertEqual(validate_claim(c,self.sources),[])
    def test_theory_does_not_require_training(self):
        c=self.claim(); c['work_status']='complete'; c['completion_basis']='Finite-action proof provided in this synthetic record.'
        c['evidence_plan']=[{'method':'proof','suffices_for':'final_claim','status':'checked'}]
        self.assertEqual(validate_claim(c,self.sources),[])
    def test_mixed_claim_types_supported(self):
        c=self.claim(); c['contribution_types']=['theory','system']; self.assertEqual(validate_claim(c,self.sources),[])
    def test_invalid_code_rejected(self):
        c=self.claim(); c['codings'][0]['code']='M15'; self.assertTrue(validate_claim(c,self.sources))
    def test_author_coding_requires_anchor(self):
        c=self.claim(); c['codings'][0].update(role='author',anchor=''); self.assertTrue(validate_claim(c,self.sources))
    def test_role_not_conflated(self):
        c=self.claim(); c['codings'][0]['role']='author+proposal'; self.assertTrue(validate_claim(c,self.sources))
    def test_completed_needs_basis(self):
        c=self.claim(); c['work_status']='complete'; self.assertTrue(validate_claim(c,self.sources))
    def test_unknown_source_rejected(self):
        c=self.claim(); c['source_ids']=['INVENTED']; self.assertTrue(validate_claim(c,self.sources))
    def test_claim_requires_scope(self):
        c=self.claim(); c['object_and_scope']=' '; self.assertTrue(validate_claim(c,self.sources))
    def test_preference_reference_allowed(self):
        c=self.claim(); c['reference_kind']='preference'; self.assertEqual(validate_claim(c,self.sources),[])
    def test_public_synthetic_cannot_be_holdout(self):
        c=self.claim(); c['dataset_role']='holdout'; self.assertTrue(validate_claim(c,self.sources))
    def test_selection_history_contaminates_holdout(self):
        c=self.claim(); c['is_synthetic']=False; c['provenance']['generation_method']='observed'; c['dataset_role']='holdout'; c['selection_history']=['used for rule revision']
        self.assertTrue(validate_claim(c,self.sources))
    def test_duplicate_ids_detected(self): self.assertEqual(duplicate_ids([{'id':'x'},{'id':'x'}]),['x'])
    def test_inapplicable_requirement_needs_reason(self):
        c=self.claim(); c['inapplicable_requirements'][0]['reason']=''; self.assertTrue(validate_claim(c,self.sources))
    def test_evidence_purpose_is_explicit(self):
        c=self.claim(); c['evidence_plan'][0]['suffices_for']='everything'; self.assertTrue(validate_claim(c,self.sources))
    def test_legacy_awards_not_reverified(self):
        cases=load(ROOT/'data/cases.json')['cases']
        self.assertTrue(all(c['award_verified_in_release'] is False for c in cases if c['cohort']=='cross_domain'))
    def test_pilot_not_run(self): self.assertFalse(load(ROOT/'evaluation/plan.json')['prospective_results_available'])

class ToolTests(unittest.TestCase):
    def test_freeze_deterministic_content(self):
        self.assertEqual(build_manifest(ROOT,['VERSION'])['content_digest'],build_manifest(ROOT,['VERSION'])['content_digest'])
    def test_freeze_changes_with_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); p=root/'x'; p.write_text('one'); a=build_manifest(root,['x']); p.write_text('two'); b=build_manifest(root,['x'])
            self.assertNotEqual(a['content_digest'],b['content_digest'])
    def test_freeze_rejects_traversal(self):
        with self.assertRaises(ValueError): build_manifest(ROOT,['../outside'])
    def test_freeze_rejects_duplicate(self):
        with self.assertRaises(ValueError): build_manifest(ROOT,['VERSION','VERSION'])
    def test_freeze_is_not_registration(self): self.assertFalse(build_manifest(ROOT,['VERSION'])['external_preregistration'])
    def test_broken_link_detected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); (root/'README.md').write_text('[x](missing.md)',encoding='utf-8')
            self.assertTrue(check_links(root))
    def test_external_link_not_falsely_verified(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); (root/'README.md').write_text('[x](https://example.invalid/not-checked)',encoding='utf-8')
            self.assertEqual(check_links(root),[])
    def test_local_links_present(self): self.assertEqual(check_links(ROOT),[])

if __name__ == '__main__': unittest.main()
