"""Schema-driven structure plus separate record-consistency / holdout review.

The JSON Schema is authoritative for types, fields and uniqueness. These functions
cannot verify scientific truth or actual independence from a declared history.
"""
from __future__ import annotations
import json
import math
from pathlib import Path
from typing import Any
try:
    from jsonschema import Draft202012Validator
except ImportError as exc:
    raise ImportError('Install requirements.txt: python3 -m pip install -r requirements.txt') from exc

ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path) -> Any:
    def reject_constant(value: str):
        raise ValueError(f'Non-JSON numeric constant: {value}')
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f'Duplicate JSON object key: {key}')
            result[key] = value
        return result
    return json.loads(path.read_text(encoding='utf-8'), parse_constant=reject_constant,
                      object_pairs_hook=unique_object)


def json_domain_errors(value: Any, path: str = '$') -> list[str]:
    if value is None or type(value) in (bool, str, int):
        return []
    if type(value) is float:
        return [] if math.isfinite(value) else [f'{path}: non-finite number is not JSON']
    if type(value) is list:
        return [e for i, v in enumerate(value) for e in json_domain_errors(v, f'{path}/{i}')]
    if type(value) is dict:
        errors = []
        for key, v in value.items():
            if type(key) is not str:
                errors.append(f'{path}: JSON object keys must be strings')
            errors.extend(json_domain_errors(v, f'{path}/{key}'))
        return errors
    return [f'{path}: value is not a JSON type']


def schema_errors(value: Any, schema: dict) -> list[str]:
    # Never resolve remote schemas as a side effect of inspecting a record.
    def check_refs(node):
        if isinstance(node, dict):
            for key, item in node.items():
                if key in ('$ref', '$dynamicRef') and not item.startswith('#'):
                    raise ValueError('Only document-local schema references are supported')
                check_refs(item)
        elif isinstance(node, list):
            for item in node:
                check_refs(item)
    check_refs(schema)
    Draft202012Validator.check_schema(schema)
    errors = json_domain_errors(value)
    if errors:
        return errors
    for err in sorted(Draft202012Validator(schema).iter_errors(value),
                      key=lambda e: (tuple(map(str, e.absolute_path)), e.message)):
        location = '$' + ''.join('/' + str(p) for p in err.absolute_path)
        errors.append(f'{location}: {err.message}')
    return errors


def assess_holdout(c: dict) -> dict:
    """Eligibility from declared facts, not proof of independence."""
    if c.get('dataset_role') not in ('holdout_candidate', 'holdout'):
        return {'status': 'not_requested', 'reasons': []}
    p = c.get('provenance', {})
    blocked = []
    if c.get('selection_history') or p.get('development_history') or p.get('development_use') == 'yes':
        blocked.append('material was used in development or selection')
    if p.get('family_overlap') == 'yes':
        blocked.append('problem family overlaps development materials')
    if p.get('analyst_exposure') == 'yes':
        blocked.append('analysis workflow was exposed to this case or answers')
    if p.get('independence_review', {}).get('status') == 'rejected':
        blocked.append('independence review rejected the case')
    if blocked:
        return {'status': 'ineligible', 'reasons': blocked}
    pending = []
    for key in ('generation_method', 'visibility', 'development_use', 'problem_family',
                'family_overlap', 'analyst_exposure'):
        if not p.get(key) or p.get(key) == 'unknown':
            pending.append(f'missing or unknown {key}')
    if 'development_history' not in p:
        pending.append('development history was not explicitly declared')
    review = p.get('independence_review', {})
    if review.get('status') != 'approved' or not review.get('reviewer') or not review.get('basis'):
        pending.append('documented human independence review required')
    if pending:
        return {'status': 'needs_review', 'reasons': pending}
    return {'status': 'candidate_only', 'reasons': [
        'Declared separation conditions met; novelty, training exposure and independence are not mechanically proven.']}


def assess_claim(c: Any, source_ids: set[str], schema: dict | None = None) -> dict:
    schema = schema if schema is not None else load_json(ROOT / 'schemas/claim.schema.json')
    errors = schema_errors(c, schema)
    reviews: list[str] = []
    holdout = {'status': 'not_assessed', 'reasons': []}
    if errors:
        return {'status': 'invalid', 'structurally_valid': False, 'errors': errors,
                'review_required': reviews, 'holdout': holdout}
    for sid in c['source_ids']:
        if sid not in source_ids:
            errors.append(f'Unknown source: {sid}')
    p = c.get('provenance', {})
    if p.get('generation_method') in ('synthetic', 'observed') and 'is_synthetic' in c:
        if c['is_synthetic'] != (p['generation_method'] == 'synthetic'):
            errors.append('is_synthetic conflicts with provenance.generation_method')
    holdout = assess_holdout(c)
    if holdout['status'] == 'ineligible':
        errors.extend('Holdout: ' + r for r in holdout['reasons'])
    elif holdout['status'] == 'needs_review':
        reviews.extend('Holdout: ' + r for r in holdout['reasons'])
    refs = c.get('evidence_refs', [])
    ids = [e['id'] for e in refs]
    if len(set(ids)) != len(ids):
        errors.append('Duplicate evidence id')
    for e in refs:
        if e['claim_id'] != c['id']:
            errors.append(f"{e['id']}: wrong claim_id")
        if e['source_id'] not in source_ids or e['source_id'] not in c['source_ids']:
            errors.append(f"{e['id']}: source must exist and be declared on the claim")
        if e['status'] == 'checked' and e['evidence_outcome'] == 'not_evaluated':
            reviews.append(f"{e['id']}: checked action needs an explicit interpretation (including inconclusive)")
        if e['status'] == 'planned' and e['evidence_outcome'] != 'not_evaluated':
            errors.append(f"{e['id']}: a planned check cannot already have an observed outcome")
    for branch in c.get('decision_branches', []):
        if any(x not in ids for x in branch.get('evidence_ids', [])):
            errors.append('Decision branch refers to missing evidence')
    for change in c.get('revision_effect', []):
        if any(x not in ids for x in change['affected_evidence_ids']):
            errors.append('Revision refers to missing evidence; retain superseded evidence records')
    status, outcome = c.get('claim_status'), c.get('evidence_outcome')
    if status == 'supported' and outcome == 'refutes':
        errors.append('Claim status supported conflicts with aggregate outcome refutes')
    if status == 'refuted' and outcome == 'supports':
        errors.append('Claim status refuted conflicts with aggregate outcome supports')
    # Checked does not itself confer support; no science is inferred from words.
    if c['work_status'] == 'complete' or status in ('supported', 'refuted'):
        if status is None:
            reviews.append('End-state record needs claim_status separate from work_status')
        if outcome is None or outcome == 'not_evaluated':
            reviews.append('End-state record needs explicit evidence_outcome')
        if not refs or not any(e['status'] == 'checked' for e in refs):
            reviews.append('End-state record needs traceable checked evidence (not necessarily supporting evidence)')
    recheck = c.get('measurement_recheck')
    if recheck:
        state = recheck['status']
        if state == 'not_triggered' and recheck['trigger_uses']:
            errors.append('M14 recheck: declared use triggers cannot be not_triggered')
        if state != 'not_triggered' and not recheck['trigger_uses']:
            errors.append('M14 recheck: triggered states need a use trigger')
        rids = recheck.get('evidence_ids', [])
        if any(x not in ids for x in rids):
            errors.append('M14 recheck refers to missing evidence')
        if state == 'revalidated' and (not rids or any(
                e['status'] != 'checked' for e in refs if e['id'] in rids)):
            errors.append('M14 revalidated requires checked evidence references; success is not inferred')
        if state == 'triggered_pending':
            reviews.append('M14 recheck triggered: old validity cannot be automatically carried forward')
        if state == 'inconclusive':
            reviews.append('M14 recheck inconclusive: keep validity claims limited')
    return {'status': 'invalid' if errors else 'needs_review' if reviews else 'valid',
            'structurally_valid': True, 'errors': errors, 'review_required': reviews,
            'holdout': holdout, 'scientific_truth_assessed': False}
