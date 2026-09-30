#!/usr/bin/env python3
"""Structural checks and arithmetic for supplied human ratings, never creativity grading."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from records import load_json, schema_errors
from freeze import relative_file

ROOT = Path(__file__).resolve().parents[1]


def check_opportunity(record: object, root: Path = ROOT) -> list[str]:
    errors = schema_errors(record, load_json(root / 'schemas/opportunity.schema.json'))
    if errors:
        return errors
    sources = {x['id'] for x in load_json(root / 'data/sources.json')['sources']}
    cards = {x['id'] for x in load_json(root / 'data/generative-cards.json')['cards']}
    if any(x not in sources for x in record.get('source_ids', [])):
        errors.append('Unknown source id')
    if any(x not in cards for x in record.get('move_cards', [])):
        errors.append('Unknown move-card id')
    if record.get('combination_lift', {}).get('status') == 'supported' and not record.get('evidence_refs'):
        errors.append('Supported lift needs traceable evidence references, not just a label')
    return errors


def check_records(root: Path = ROOT) -> dict:
    errors = []
    authors = load_json(root / 'data/author-moves.json')
    cases = {x['id'] for x in load_json(root / 'data/cases.json')['cases']}
    sources = {x['id'] for x in load_json(root / 'data/sources.json')['sources']}
    records = authors['records']
    ids = set()
    schema = load_json(root / 'schemas/author-move.schema.json')
    for r in records:
        e = schema_errors(r, schema)
        if e:
            errors.extend(e)
            continue
        if r['id'] in ids:
            errors.append('Duplicate author record id')
        ids.add(r['id'])
        if r['case_id'] not in cases:
            errors.append('Unknown case for author annotation')
        if any(x not in sources for x in r['source_ids']):
            errors.append('Unknown author source id')
        if r.get('independent_second_coder') and not r.get('independent_review_record'):
            errors.append('Independent recoding needs a review record')
    cards = load_json(root / 'data/generative-cards.json')['cards']
    card_ids = set()
    for c in cards:
        for field in ('id', 'trigger', 'transformation', 'expected_product', 'first_step', 'do_not_apply'):
            if not isinstance(c.get(field), str) or not c[field].strip():
                errors.append('Missing move-card field: ' + field)
        if c['id'] in card_ids:
            errors.append('Duplicate move-card id')
        card_ids.add(c['id'])
        if not c.get('source_author_move_ids') or any(x not in ids for x in c['source_author_move_ids']):
            errors.append('Unknown or absent author-move anchor')
    rules = {x['id']: x for x in load_json(root / 'data/rules.json')['rules']}
    links = load_json(root / 'data/rule-lineage.json')['links']
    link_ids = {x['id'] for x in links}
    if len(link_ids) != len(links):
        errors.append('Duplicate lineage id')
    for x in links:
        if x['rule'] not in rules or any(c not in cases for c in x['case_ids']):
            errors.append('Unknown lineage rule/case')
        if x.get('effectiveness_tested') and not x.get('effectiveness_record'):
            errors.append('Rule effectiveness needs independent result record')
    for rule in rules.values():
        if any(x not in link_ids for x in rule.get('lineage_refs', [])):
            errors.append('Broken rule lineage reference')
    crosswalk = load_json(root / 'data/external-review-crosswalk.json')
    if crosswalk.get('coverage_recomputed') and not crosswalk.get('recomputation_record'):
        errors.append('External coverage cannot be upgraded without a recomputation record')
    import hashlib
    review = relative_file(root, crosswalk['source_file'])
    if hashlib.sha256(review.read_bytes()).hexdigest() != crosswalk['source_sha256']:
        errors.append('External review source bytes changed')
    for x in [load_json(root / 'templates/opportunity.json')] + load_json(root / 'examples/opportunities.json')['records']:
        errors.extend(check_opportunity(x, root))
    materials = load_json(root / 'evaluation/generation/materials.json')
    for spec in materials['arms'].values():
        for name in spec['files']:
            relative_file(root, name)
            if not name.startswith('evaluation/generation/inputs/'):
                errors.append('Generation participant materials must exclude source-paper answer cards')
    plan = load_json(root / 'evaluation/generation/plan.json')
    if plan.get('prospective_results_available') and not plan.get('results_record'):
        errors.append('Generation effectiveness needs a results record')
    return {'passed': not errors, 'scope': 'structural_integrity_only', 'errors': errors,
            'author_records': len(records), 'move_cards': len(cards),
            'independent_second_coders': sum(r.get('independent_second_coder') is True for r in records),
            'scientific_quality_assessed': False, 'generation_effectiveness_tested': False}


def summarize_candidates(rows: list[dict], k: int = 3) -> dict:
    """Use reviewer-assigned semantic IDs and judgments; unresolved != failure.

Counts submitted candidates against k before deduplication. Missing outputs and
transport failures belong in the study execution ledger, not in this helper.
"""
    if type(k) is not int or k < 1 or not isinstance(rows, list) or len(rows) > k:
        raise ValueError('Provide a fixed positive k and no more than k submitted candidates')
    by_concept, seen = {}, set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('Candidate rating must be an object')
        uid, concept, q = row.get('id'), row.get('concept_id'), row.get('qualification')
        if not isinstance(uid, str) or not uid or uid in seen or not isinstance(concept, str) or not concept:
            raise ValueError('Unique candidate IDs and reviewer-assigned concept IDs required')
        if q not in ('qualified', 'not_qualified', 'unjudgeable'):
            raise ValueError('Human qualification missing')
        seen.add(uid)
        if concept in by_concept and by_concept[concept] != q:
            raise ValueError('Resolve inconsistent ratings of one semantic candidate before aggregation')
        by_concept[concept] = q
    good = sum(q == 'qualified' for q in by_concept.values())
    unresolved = sum(q == 'unjudgeable' for q in by_concept.values())
    any_good = True if good else None if unresolved else False
    return {'submitted_count': len(rows), 'unique_count': len(by_concept),
            'qualified_count_known': good, 'unresolved_count': unresolved,
            'any_qualified_at_k': any_good, 'possible_range': [int(good > 0), int(good > 0 or unresolved > 0)],
            'k': k, 'scientific_grading_performed': False}


def assess_selection(pool: list[dict], selected: list[str], slots: int) -> dict:
    """Retention from a fixed, fully adjudicated pool. Not selecting all good ideas is not failure."""
    if type(slots) is not int or slots < 0 or not isinstance(selected, list) or len(selected) > slots:
        raise ValueError('Invalid selection budget')
    if any(not isinstance(x, str) or not x for x in selected) or len(set(selected)) != len(selected):
        raise ValueError('Selection IDs must be unique strings')
    p = {}
    for r in pool:
        if not isinstance(r, dict) or not isinstance(r.get('id'), str) or not r['id'] or r['id'] in p:
            raise ValueError('Pool IDs must be unique strings')
        if r.get('qualification') not in ('qualified', 'not_qualified'):
            raise ValueError('Selection benchmark requires resolved independent ratings')
        p[r['id']] = r['qualification']
    if any(x not in p for x in selected):
        raise ValueError('Selected candidate is not in the frozen pool')
    eligible = {k for k, v in p.items() if v == 'qualified'}
    return {'eligible_count': len(eligible), 'selected_count': len(selected),
            'retains_at_least_one': bool(eligible & set(selected)) if eligible else None,
            'ineligible_selected': sum(x not in eligible for x in selected),
            'budget': slots, 'scientific_grading_performed': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['check'])
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--opportunity', type=Path)
    args = parser.parse_args()
    try:
        if args.opportunity:
            e = check_opportunity(load_json(args.opportunity), args.root)
            result = {'passed': not e, 'errors': e, 'scope': 'structural_integrity_only'}
        else:
            result = check_records(args.root)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        result = {'passed': False, 'errors': [str(exc)], 'scope': 'structural_integrity_only'}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['passed'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
