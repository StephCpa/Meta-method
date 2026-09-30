"""v0.4 structural regressions, not evidence of contribution-generation effectiveness."""
from pathlib import Path
import copy
import re
import sys
import unittest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from records import load_json, schema_errors
from generation import check_records, check_opportunity, summarize_candidates, assess_selection

class GenerationRecordsTests(unittest.TestCase):
    def test_release_records(self):
        r=check_records(ROOT); self.assertTrue(r['passed'],r['errors'])
    def test_author_annotations_link_existing_cases(self):
        authors=load_json(ROOT/'data/author-moves.json')['records']
        cases={x['id'] for x in load_json(ROOT/'data/cases.json')['cases']}
        self.assertTrue(all(a['case_id'] in cases for a in authors))
        self.assertEqual(len(authors),8)
    def test_old_48_not_expanded_or_recoded(self):
        cases=load_json(ROOT/'data/cases.json')['cases']
        self.assertEqual(len(cases),48)
        self.assertTrue(all(x['coding_role']=='proposal' for x in cases if x['cohort']=='MAS'))
    def test_first_pass_not_second_coder(self):
        for x in load_json(ROOT/'data/author-moves.json')['records']:
            self.assertFalse(x['independent_second_coder'])
            self.assertEqual(x['dataset_role'],'development')
    def test_six_source_backed_cards(self):
        self.assertEqual(len(load_json(ROOT/'data/generative-cards.json')['cards']),6)
    def test_external_mapping_not_upgraded(self):
        x=load_json(ROOT/'data/external-review-crosswalk.json')
        self.assertFalse(x['coverage_recomputed']); self.assertFalse(x['full_catalog_received'])
    def test_all_rules_have_traceable_links(self):
        ids={x['id'] for x in load_json(ROOT/'data/rule-lineage.json')['links']}
        for r in load_json(ROOT/'data/rules.json')['rules']:
            self.assertTrue(r['lineage_refs']); self.assertTrue(set(r['lineage_refs'])<=ids)
    def test_author_schema_is_valid(self):
        Draft202012Validator.check_schema(load_json(ROOT/'schemas/author-move.schema.json'))
    def test_author_missing_anchor_rejected(self):
        r=copy.deepcopy(load_json(ROOT/'data/author-moves.json')['records'][0]);r['author_codings'][0]['anchor']=[]
        self.assertTrue(schema_errors(r,load_json(ROOT/'schemas/author-move.schema.json')))
    def test_audit_role_cannot_be_author_annotation(self):
        r=copy.deepcopy(load_json(ROOT/'data/author-moves.json')['records'][0]);r['author_codings'][0]['role']='proposal'
        self.assertTrue(schema_errors(r,load_json(ROOT/'schemas/author-move.schema.json')))
    def test_draft_needs_no_precise_claim(self):
        self.assertEqual(check_opportunity({'id':'x','stage':'exploring','problem_situation':'A real question'}),[])
    def test_specified_needs_a_concrete_move(self):
        self.assertTrue(check_opportunity({'id':'x','stage':'specified','problem_situation':'A question'}))
    def test_nonobject_is_rejected(self):
        for x in (None,[],3,'x'): self.assertTrue(check_opportunity(x))
    def test_combination_needs_lift_when_specified(self):
        r=copy.deepcopy(load_json(ROOT/'examples/opportunities.json')['records'][1]);r['is_combination']=True
        self.assertTrue(check_opportunity(r))
    def test_no_combination_no_lift_required(self):
        r=load_json(ROOT/'examples/opportunities.json')['records'][1];self.assertEqual(check_opportunity(r),[])
    def test_supported_lift_needs_evidence_ref(self):
        r=copy.deepcopy(load_json(ROOT/'examples/opportunities.json')['records'][1]);r['is_combination']=True
        r['combination_lift']={k:'x' for k in ['nearest_simple_combination','relation_changed','added_result','evidence_needed']};r['combination_lift']['status']='supported'
        self.assertTrue(check_opportunity(r))
    def test_audited_needs_linked_claim(self):
        r=copy.deepcopy(load_json(ROOT/'examples/opportunities.json')['records'][1]);r['stage']='audited'
        self.assertTrue(check_opportunity(r))
    def test_unknown_card_rejected(self):
        r=copy.deepcopy(load_json(ROOT/'templates/opportunity.json'));r['move_cards']=['invented']
        self.assertTrue(check_opportunity(r))
    def test_no_new_M_identifiers(self):
        x=load_json(ROOT/'data/operation-roles.json')['operations']
        self.assertEqual({r['code'] for r in x},{f'M{i}' for i in range(1,15)})
    def test_participant_materials_no_arm_signposts(self):
        files=[]
        for manifest in ['evaluation/materials.json','evaluation/generation/materials.json']:
            for arm in load_json(ROOT/manifest)['arms'].values():files.extend(arm['files'])
        for name in set(files):
            text=(ROOT/name).read_text(encoding='utf-8')
            with self.subTest(path=name):self.assertIsNone(re.search(r'B/C|A/B/C|B、C|仅C|\bG[01]\b|试验臂|实验组|对照组',text))
    def test_generation_prompts_no_winner_answers(self):
        m=load_json(ROOT/'evaluation/generation/materials.json')
        for arm in m['arms'].values():
            for f in arm['files']:
                t=(ROOT/f).read_text()
                self.assertNotIn('SAM 2',t);self.assertNotIn('STDE',t);self.assertNotIn('XD01',t)
    def test_generation_not_reported_as_run(self):
        p=load_json(ROOT/'evaluation/generation/plan.json')
        self.assertFalse(p['prospective_results_available']);self.assertIsNone(p['model_id'])

class GenerationArithmeticTests(unittest.TestCase):
    def row(self,i,q,concept=None):return {'id':str(i),'concept_id':str(i) if concept is None else concept,'qualification':q}
    def test_qualified_at_three(self):
        self.assertTrue(summarize_candidates([self.row(1,'qualified')])['any_qualified_at_k'])
    def test_unresolved_not_a_failure(self):
        r=summarize_candidates([self.row(1,'unjudgeable')]);self.assertIsNone(r['any_qualified_at_k']);self.assertEqual(r['possible_range'],[0,1])
    def test_good_with_unresolved_retains_good(self):
        r=summarize_candidates([self.row(1,'qualified'),self.row(2,'unjudgeable')]);self.assertTrue(r['any_qualified_at_k']);self.assertEqual(r['unresolved_count'],1)
    def test_semantic_duplicates_not_extra_contributions(self):
        r=summarize_candidates([self.row(1,'qualified','same'),self.row(2,'qualified','same')]);self.assertEqual(r['qualified_count_known'],1)
    def test_conflicting_semantic_ratings_rejected(self):
        with self.assertRaises(ValueError):summarize_candidates([self.row(1,'qualified','same'),self.row(2,'not_qualified','same')])
    def test_cannot_select_best_after_oversampling(self):
        with self.assertRaises(ValueError):summarize_candidates([self.row(i,'qualified') for i in range(4)])
    def test_no_candidate_can_be_valid_behavior(self):
        self.assertFalse(summarize_candidates([])['any_qualified_at_k'])
    def test_no_positive_pool_retention_is_na(self):
        self.assertIsNone(assess_selection([self.row(1,'not_qualified')],[],1)['retains_at_least_one'])
    def test_not_choosing_all_good_is_not_false_rejection(self):
        r=assess_selection([self.row(1,'qualified'),self.row(2,'qualified')],['1'],1);self.assertTrue(r['retains_at_least_one'])
    def test_selection_cannot_invent_candidate(self):
        with self.assertRaises(ValueError):assess_selection([self.row(1,'qualified')],['2'],1)
    def test_selection_budget_enforced(self):
        with self.assertRaises(ValueError):assess_selection([self.row(1,'qualified'),self.row(2,'qualified')],['1','2'],1)
    def test_unresolved_pool_requires_review(self):
        with self.assertRaises(ValueError):assess_selection([self.row(1,'unjudgeable')],[],1)
    def test_no_automatic_scientific_grading(self):
        self.assertFalse(summarize_candidates([])['scientific_grading_performed'])

if __name__=='__main__':unittest.main()
