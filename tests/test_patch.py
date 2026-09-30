"""v0.3.1 regressions: records, file safety, treatment isolation and metric arithmetic."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from records import assess_claim, schema_errors, load_json
from validate import validate_repo, validate_snapshot
from freeze import build_manifest, version_paths, write_new_output, verify_manifest, build_run_manifest
from protocol import validate_materials, run_readiness
from evaluate import summarize_case, aggregate_cases, interpret_comparison


def clone_repo(root):
    shutil.copytree(ROOT, root, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('.git', 'outputs', 'private', '__pycache__', '.venv'))

class RecordsTests(unittest.TestCase):
    def setUp(self):
        self.c = copy.deepcopy(load_json(ROOT / 'templates/claim.json'))
        self.s = {x['id'] for x in load_json(ROOT / 'data/sources.json')['sources']}
        self.schema = load_json(ROOT / 'schemas/claim.schema.json')
    def result(self): return assess_claim(self.c, self.s)
    def private_candidate(self):
        self.c['dataset_role'] = 'holdout_candidate'
        self.c['provenance'] = {'generation_method': 'synthetic', 'visibility': 'private',
            'development_use': 'no', 'development_history': [], 'problem_family': 'new-family',
            'family_overlap': 'no', 'analyst_exposure': 'no',
            'independence_review': {'status': 'approved', 'reviewer': 'test-reviewer', 'basis': 'Declared isolated new problem family; only a test fixture.'}}
    def evidence(self):
        self.c = copy.deepcopy(load_json(ROOT / 'examples/claims.json')['claims'][6])
    def test_nonobject_is_diagnostic_not_attributeerror(self):
        for obj in ([], None, 7, True, 'text'):
            with self.subTest(obj=obj): self.assertEqual(assess_claim(obj,self.s)['status'],'invalid')
    def test_duplicate_sources_rejected(self):
        self.c['source_ids'] *= 2; self.assertEqual(self.result()['status'],'invalid')
    def test_synthetic_string_false_rejected(self):
        self.c['is_synthetic']='false'; self.assertEqual(self.result()['status'],'invalid')
    def test_revision_integer_rejected(self):
        self.c['revision_history']=3; self.assertEqual(self.result()['status'],'invalid')
    def test_revision_item_integer_rejected(self):
        self.c['revision_history']=[3]; self.assertEqual(self.result()['status'],'invalid')
    def test_nan_rejected(self):
        self.c['extra']=float('nan'); self.assertEqual(self.result()['status'],'invalid')
    def test_unknown_source_rejected(self):
        self.c['source_ids']=['no-source']; self.assertEqual(self.result()['status'],'invalid')
    def test_optional_new_fields_not_required_for_drafts(self):
        for k in ('provenance','claim_status','evidence_outcome','record_version'): self.c.pop(k,None)
        self.assertEqual(self.result()['status'],'valid')
    def test_public_development_synthetic_excluded(self):
        self.c['dataset_role']='holdout'; self.assertEqual(self.result()['holdout']['status'],'ineligible')
    def test_used_real_material_excluded(self):
        self.c['dataset_role']='holdout'; self.c['is_synthetic']=False
        self.c['provenance']['generation_method']='observed'
        self.assertEqual(self.result()['holdout']['status'],'ineligible')
    def test_private_is_not_enough(self):
        self.private_candidate(); self.c['provenance'].pop('independence_review')
        self.assertEqual(self.result()['status'],'needs_review')
    def test_new_synthetic_candidate_allowed(self):
        self.private_candidate(); self.assertEqual(self.result()['status'],'valid')
        self.assertEqual(self.result()['holdout']['status'],'candidate_only')
    def test_observed_and_synthetic_have_same_separation_rule(self):
        self.private_candidate(); a=self.result()['status']
        self.c['is_synthetic']=False; self.c['provenance']['generation_method']='observed'
        self.assertEqual(a,self.result()['status'])
    def test_unknown_family_needs_review(self):
        self.private_candidate(); self.c['provenance']['family_overlap']='unknown'
        self.assertEqual(self.result()['status'],'needs_review')
    def test_overlapping_family_excluded(self):
        self.private_candidate(); self.c['provenance']['family_overlap']='yes'
        self.assertEqual(self.result()['status'],'invalid')
    def test_exposed_analyst_excluded(self):
        self.private_candidate(); self.c['provenance']['analyst_exposure']='yes'
        self.assertEqual(self.result()['status'],'invalid')
    def test_missing_provenance_needs_review(self):
        self.c.pop('provenance');self.c['dataset_role']='holdout'
        self.assertEqual(self.result()['status'],'needs_review')
    def test_synthetic_metadata_conflict(self):
        self.private_candidate();self.c['is_synthetic']=False
        self.assertEqual(self.result()['status'],'invalid')
    def test_supported_completed_example(self):
        self.evidence();self.assertEqual(self.result()['status'],'valid')
    def test_refuted_completed_is_valid(self):
        self.c=copy.deepcopy(load_json(ROOT/'examples/claims.json')['claims'][7])
        self.assertEqual(self.result()['status'],'valid')
    def test_inconclusive_paused_is_valid(self):
        self.c=copy.deepcopy(load_json(ROOT/'examples/claims.json')['claims'][8])
        self.assertEqual(self.result()['status'],'valid')
    def test_checked_does_not_infer_supported(self):
        self.c['evidence_plan'][0]['status']='checked'
        self.assertEqual(self.result()['status'],'valid');self.assertEqual(self.c['claim_status'],'draft')
    def test_completed_legacy_needs_review_not_truth_rejection(self):
        self.c['work_status']='complete';self.c['completion_basis']='See proof'
        self.assertEqual(self.result()['status'],'needs_review')
    def test_evidence_wrong_claim_rejected(self):
        self.evidence();self.c['evidence_refs'][0]['claim_id']='EX999'
        self.assertEqual(self.result()['status'],'invalid')
    def test_evidence_duplicate_id_rejected(self):
        self.evidence();self.c['evidence_refs']*=2;self.assertEqual(self.result()['status'],'invalid')
    def test_checked_outcome_missing_needs_review(self):
        self.evidence();self.c['evidence_refs'][0]['evidence_outcome']='not_evaluated'
        self.assertEqual(self.result()['status'],'needs_review')
    def test_planned_evidence_cannot_claim_outcome(self):
        self.evidence();self.c['evidence_refs'][0]['status']='planned'
        self.assertEqual(self.result()['status'],'invalid')
    def test_supported_refutes_conflict(self):
        self.evidence();self.c['evidence_outcome']='refutes'
        self.assertEqual(self.result()['status'],'invalid')
    def test_revision_bad_ref_rejected(self):
        self.evidence();self.c['revision_effect']=[{'revision_id':'r1','prior_version':'0.3.0','affected_evidence_ids':['missing'],'validity':'superseded','reason':'new claim'}]
        self.assertEqual(self.result()['status'],'invalid')
    def test_branch_bad_ref_rejected(self):
        self.evidence();self.c['decision_branches'][0]['evidence_ids']=['missing']
        self.assertEqual(self.result()['status'],'invalid')
    def test_m14_not_triggered_valid(self):
        self.c['measurement_recheck']={'status':'not_triggered','trigger_uses':[],'description':'No metric is fed back.'}
        self.assertEqual(self.result()['status'],'valid')
    def test_m14_trigger_is_review(self):
        self.c['measurement_recheck']={'status':'triggered_pending','trigger_uses':['sample_selection'],'description':'Metric now filters samples.'}
        self.assertEqual(self.result()['status'],'needs_review')
    def test_m14_revalidated_needs_refs(self):
        self.c['measurement_recheck']={'status':'revalidated','trigger_uses':['routing'],'description':'Claims a recheck.'}
        self.assertEqual(self.result()['status'],'invalid')
    def test_m14_recheck_does_not_imply_support(self):
        self.evidence();e=self.c['evidence_refs'][0];e['evidence_outcome']='refutes'
        self.c['claim_status']='refuted';self.c['evidence_outcome']='refutes'
        self.c['measurement_recheck']={'status':'revalidated','trigger_uses':['training_objective'],'description':'Check completed but failed validity.','evidence_ids':[e['id']]}
        self.assertEqual(self.result()['status'],'valid')
    def test_schema_validator_matches_authoritative_schema(self):
        variations=[[],42,None,copy.deepcopy(self.c)]
        for k,v in [('source_ids',['SRC-V03','SRC-V03']),('is_synthetic','false'),('revision_history',3),('revision_history',[2]),('claim_text',' '),('contribution_types',['theory','theory']),('claim_status','magic')]:
            c=copy.deepcopy(self.c);c[k]=v;variations.append(c)
        for c in variations:
            with self.subTest(c=c): self.assertEqual(bool(schema_errors(c,self.schema)),bool(list(Draft202012Validator(self.schema).iter_errors(c))))
    def test_schema_change_is_used_without_code_change(self):
        s=copy.deepcopy(self.schema);s['required'].append('new_required')
        self.assertEqual(assess_claim(self.c,self.s,s)['status'],'invalid')
    def test_remote_schema_ref_rejected(self):
        with self.assertRaises(ValueError):schema_errors({}, {'$ref':'https://example.invalid/schema'})
    def test_json_duplicate_keys_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x.json';p.write_text('{"id":"a","id":"b"}')
            with self.assertRaises(ValueError):load_json(p)

class FreezeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        (self.root/'README.md').write_text('original')
        (self.root/'x').write_text('x')
    def manifest(self):return build_manifest(self.root,version_paths(self.root),'version')
    def test_refuses_readme_output_even_when_not_frozen(self):
        with self.assertRaises(ValueError):write_new_output(self.root,Path('README.md'),{},['x'])
        self.assertEqual((self.root/'README.md').read_text(),'original')
    def test_refuses_new_source_path(self):
        with self.assertRaises(ValueError):write_new_output(self.root,Path('tools/new.json'),{})
    def test_refuses_any_existing_output(self):
        p=write_new_output(self.root,Path('outputs/x.json'),{'v':1})
        with self.assertRaises(FileExistsError):write_new_output(self.root,p,{'v':2})
        self.assertEqual(json.loads(p.read_text()),{'v':1})
    def test_refuses_frozen_input_below_outputs(self):
        p=self.root/'outputs/x.json';p.parent.mkdir();p.write_text('x')
        with self.assertRaises(ValueError):write_new_output(self.root,p,{},['outputs/x.json'])
    def test_refuses_symlink_output_parent(self):
        (self.root/'outputs').symlink_to(self.root/'elsewhere',target_is_directory=True)
        with self.assertRaises(ValueError):write_new_output(self.root,Path('outputs/x.json'),{})
    def test_refuses_input_symlink(self):
        (self.root/'alias').symlink_to(self.root/'x')
        with self.assertRaises(ValueError):build_manifest(self.root,['alias'])
    def test_refuses_absolute_or_parent_inputs(self):
        for name in ('../x',str(self.root/'x')):
            with self.subTest(name=name),self.assertRaises(ValueError):build_manifest(self.root,[name])
    def test_refuses_external_output(self):
        with self.assertRaises(ValueError):write_new_output(self.root,Path('/outside.json'),{})
    def test_version_covers_schema_template_tools_workflow(self):
        paths=version_paths(ROOT)
        for p in ('schemas/claim.schema.json','templates/claim.json','tools/validate.py','docs/workflow.md','evaluation/materials.json'):
            self.assertIn(p,paths)
    def test_default_digest_changes_when_template_changes(self):
        p=self.root/'templates/claim.json';p.parent.mkdir();p.write_text('{}')
        a=self.manifest()['content_digest'];p.write_text('{"x":1}')
        self.assertNotEqual(a,self.manifest()['content_digest'])
    def test_outputs_excluded_from_version(self):
        a=self.manifest();write_new_output(self.root,Path('outputs/f.json'),a)
        self.assertEqual(a['content_digest'],self.manifest()['content_digest'])
    def test_private_files_excluded_by_default(self):
        (self.root/'private').mkdir();(self.root/'private/key').write_text('secret')
        self.assertNotIn('private/key',version_paths(self.root))
    def test_verify_match(self):self.assertTrue(verify_manifest(self.root,self.manifest())['matches'])
    def test_verify_changed(self):
        m=self.manifest();(self.root/'x').write_text('changed');r=verify_manifest(self.root,m)
        self.assertIn('x',r['changed']);self.assertFalse(r['matches'])
    def test_verify_missing(self):
        m=self.manifest();(self.root/'x').unlink();self.assertIn('x',verify_manifest(self.root,m)['missing'])
    def test_verify_new_unfrozen_file(self):
        m=self.manifest();(self.root/'new').write_text('new');r=verify_manifest(self.root,m)
        self.assertIn('new',r['not_frozen']);self.assertFalse(r['matches'])
    def test_selected_scope_reports_outside_without_failing(self):
        m=build_manifest(self.root,['x']);r=verify_manifest(self.root,m)
        self.assertTrue(r['matches']);self.assertIn('README.md',r['not_frozen'])
    def test_manifest_tampering_detected(self):
        m=self.manifest();m['files'][0]['sha256']='0'*64
        self.assertTrue(verify_manifest(self.root,m)['invalid'])
    def test_no_false_timestamp_authentication(self):
        self.assertFalse(self.manifest()['independent_timestamp'])
    def test_run_incomplete_rejected(self):
        with self.assertRaises(ValueError):build_run_manifest(ROOT,'evaluation/run-template.json')
    def test_draft_run_is_explicitly_incomplete(self):
        m=build_run_manifest(ROOT,'evaluation/run-template.json',True)
        self.assertEqual(m['metadata']['readiness'],'draft_incomplete')
        self.assertTrue(m['metadata']['missing_configuration'])
        self.assertEqual(m['metadata']['arm_materials']['B'], sorted(m['metadata']['arm_materials']['B']))

class ProtocolTests(unittest.TestCase):
    def setUp(self):self.m=load_json(ROOT/'evaluation/materials.json')
    def test_materials_valid(self):self.assertEqual(validate_materials(self.m,ROOT),[])
    def test_b_c_exact_delta(self):
        self.assertEqual(set(self.m['arms']['C']['files'])-set(self.m['arms']['B']['files']),set(self.m['codebook_increment_files']))
    def test_missing_contract_from_b_rejected(self):
        self.m['arms']['B']['files'].remove('docs/conditional-contracts.md')
        self.assertTrue(validate_materials(self.m,ROOT))
    def test_extra_c_material_rejected(self):
        self.m['arms']['C']['files'].append('docs/workflow.md');self.assertTrue(validate_materials(self.m,ROOT))
    def test_codebook_leak_to_b_rejected(self):
        self.m['arms']['B']['files'].append(self.m['codebook_increment_files'][0]);self.assertTrue(validate_materials(self.m,ROOT))
    def test_prospective_template_not_ready(self):self.assertTrue(run_readiness(load_json(ROOT/'evaluation/run-template.json')))
    def test_metrics_semantic_dedup_ids(self):
        r=summarize_case([{'id':'e1','assessment':'missed'},{'id':'e2','assessment':'met'}],
                         [{'id':'unnecessary-a','severity':1},{'id':'unnecessary-a','severity':2}])
        self.assertEqual(r['omission_rate'],.5);self.assertEqual(r['unsupported_action_count'],1);self.assertTrue(r['severe_overreach_any'])
    def test_na_not_zero(self):
        r=summarize_case([],[],False)
        self.assertIsNone(r['omission_rate']);self.assertIsNone(r['severe_overreach_any'])
    def test_inconclusive_units_reported(self):
        r=summarize_case([{'id':'e','assessment':'unjudgeable'}],[])
        self.assertIsNone(r['omission_rate']);self.assertEqual(r['unjudgeable_required_count'],1)
    def test_required_duplicate_rejected(self):
        with self.assertRaises(ValueError):summarize_case([{'id':'e','assessment':'met'}]*2,[])
    def test_bad_severity_rejected(self):
        with self.assertRaises(ValueError):summarize_case([],[{'id':'a','severity':True}])
    def test_macro_case_not_statement_weighted(self):
        a=summarize_case([{'id':'a','assessment':'missed'}],[])
        b=summarize_case([{'id':str(i),'assessment':'met'} for i in range(100)],[])
        self.assertEqual(aggregate_cases([a,b])['macro_omission_rate'],.5)
    def test_supports_meaningful_improvement(self):
        self.assertEqual(interpret_comparison([.06,.1],[-.01,.005],.05,.01),'supports_improvement')
    def test_rules_out_meaningful_improvement(self):
        self.assertEqual(interpret_comparison([-.02,.03],[-.01,.005],.05,.01),'rules_out_acceptable_improvement')
    def test_information_insufficient(self):
        self.assertEqual(interpret_comparison([-.02,.1],[-.01,.04],.05,.01),'inconclusive')
    def test_unacceptable_harm(self):
        self.assertEqual(interpret_comparison([.06,.1],[.02,.04],.05,.01),'rules_out_acceptable_improvement')
    def test_thresholds_not_invented(self):
        with self.assertRaises(ValueError):interpret_comparison([0,.1],[0,.1],None,None)
    def test_reversed_interval_rejected(self):
        with self.assertRaises(ValueError):interpret_comparison([.1,0],[0,.1],.05,.01)
    def test_working_registry_can_grow(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);clone_repo(r);p=r/'data/cases.json';v=load_json(p)
            c=copy.deepcopy(v['cases'][0]);c['id']='NEW01';c['cohort']='new-development';v['cases'].append(c)
            p.write_text(json.dumps(v),encoding='utf-8');self.assertTrue(validate_repo(r)['passed'])
    def test_verification_upgrade_allowed_with_trace(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);clone_repo(r);p=r/'data/cases.json';v=load_json(p)
            c=v['cases'][0];c['verification_status']='source_checked';c['verification_record']={'source_version':'test','locator':'test-only','action':'synthetic test change','date':'2026-09-30'}
            p.write_text(json.dumps(v));self.assertTrue(validate_repo(r)['passed'])
    def test_verification_upgrade_without_trace_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);clone_repo(r);p=r/'data/cases.json';v=load_json(p)
            v['cases'][0]['verification_status']='source_checked';p.write_text(json.dumps(v))
            self.assertFalse(validate_repo(r)['passed'])

class RunSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);clone_repo(self.root)
        (self.root/'private').mkdir()
        (self.root/'private/case.md').write_text('Synthetic unit-test case, no real trial.')
        (self.root/'private/key.md').write_text('Synthetic evaluator key.')
        (self.root/'private/stats.md').write_text('Test-only declared statistical plan, not preregistered.')
        (self.root/'private/sample.md').write_text('One synthetic unit fixture, not powered.')
        self.config=load_json(self.root/'evaluation/run-template.json')
        self.config.update(run_id='UNIT-ONLY',phase='pilot',case_inputs=['private/case.md'],
            reference_inputs=['private/key.md'],dataset_identifiers=['synthetic-unit-case'],
            stopping_rule='single unit test, not an experimental stopping policy',source_cutoff='2026-09-30',
            statistical_protocol='private/stats.md',sample_plan='private/sample.md')
        self.config['budget']={k:10 for k in self.config['budget']}
        self.config['implementation'].update(git_commit='a'*40,model_id='no-api-unit-stub',executor_version='unit-only')
        self.config['randomization']['seed']=7
        self.config['acceptance'].update(minimum_meaningful_omission_improvement=.05,maximum_tolerated_severe_overreach_increase=.01)
        self.save()
    def save(self):
        (self.root/'private/run.json').write_text(json.dumps(self.config),encoding='utf-8')
    def test_declared_ready_run_can_be_frozen(self):
        m=build_run_manifest(self.root,'private/run.json')
        self.assertEqual(m['metadata']['readiness'],'declared_configuration_ready')
        self.assertEqual(m['metadata']['execution_status'],'not_run_by_freeze_tool')
    def test_reference_keys_not_in_arm_materials(self):
        m=build_run_manifest(self.root,'private/run.json')
        for files in m['metadata']['arm_materials'].values():
            self.assertNotIn('private/key.md',files);self.assertIn('private/case.md',files)
    def test_run_includes_implementation_and_statistical_plan(self):
        m=build_run_manifest(self.root,'private/run.json');files={e['path'] for e in m['files']}
        for name in ('tools/records.py','private/stats.md','private/sample.md','private/key.md','private/run.json'):
            self.assertIn(name,files)
    def test_run_budget_change_changes_digest(self):
        a=build_run_manifest(self.root,'private/run.json')
        self.config['budget']['tool_calls']=11;self.save()
        self.assertNotEqual(a['content_digest'],build_run_manifest(self.root,'private/run.json')['content_digest'])
    def test_run_rejects_evaluator_key_as_input(self):
        self.config['case_inputs'].append('private/key.md');self.save()
        with self.assertRaises(ValueError):build_run_manifest(self.root,'private/run.json',True)
    def test_run_missing_statistical_plan_needs_configuration(self):
        self.config['statistical_protocol']=None;self.save()
        with self.assertRaises(ValueError):build_run_manifest(self.root,'private/run.json')
    def test_run_verify_reports_input_changes(self):
        m=build_run_manifest(self.root,'private/run.json')
        (self.root/'private/case.md').write_text('changed')
        self.assertIn('private/case.md',verify_manifest(self.root,m)['changed'])

class MalformedBoundaryTests(unittest.TestCase):
    def test_invalid_material_arm_is_reported(self):
        self.assertTrue(validate_materials({'arms': {'A': [], 'B': {}, 'C': {}}}))
    def test_invalid_run_identifier_is_reported(self):
        self.assertIn('run_id',run_readiness({'run_id':42}))
    def test_nonobject_claim_template_is_reported(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);clone_repo(root);(root/'templates/claim.json').write_text('[]')
            result=validate_repo(root)
            self.assertFalse(result['passed']);self.assertTrue(any('non-object' in x for x in result['errors']))

if __name__=='__main__':unittest.main()
