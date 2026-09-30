#!/usr/bin/env python3
"""Engineering checks for v0.3; never a scientific-validity classifier.

Standard library only. Does not execute inherited research probes, call LLMs,
fetch remote sources, or infer whether a scientific claim is true.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
PROFILES = {'theory', 'explanation', 'algorithm', 'system', 'data_evaluation', 'decision'}
CODES = {f'M{i}' for i in range(1, 15)}
ROLES = {'author', 'review', 'proposal'}
STATES = {'exploring', 'planned', 'active', 'complete', 'paused', 'stopped', 'rewritten'}
REFERENCES = {'truth', 'norm', 'preference', 'proxy', 'mixed', 'not_applicable'}


def load(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def nonempty(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_claim(c: dict, source_ids: set[str]) -> list[str]:
    errors: list[str] = []
    prefix = c.get('id', '<missing-id>')
    def fail(message): errors.append(f'{prefix}: {message}')
    for name in ('id', 'title', 'claim_text', 'object_and_scope'):
        if not nonempty(c.get(name)): fail(f'{name} must be a nonempty string')
    profiles = c.get('contribution_types')
    if not isinstance(profiles, list) or not profiles or any(p not in PROFILES for p in profiles):
        fail('invalid contribution_types')
    elif len(profiles) != len(set(profiles)): fail('duplicate contribution types')
    if c.get('reference_kind') not in REFERENCES: fail('invalid reference_kind')
    criteria = c.get('success_criteria')
    if not isinstance(criteria, list) or not criteria or not all(nonempty(x) for x in criteria):
        fail('success_criteria must contain a criterion')
    plans = c.get('evidence_plan')
    if not isinstance(plans, list) or not plans:
        fail('evidence_plan must be a nonempty list')
    else:
        for plan in plans:
            if not isinstance(plan, dict) or not nonempty(plan.get('method')):
                fail('evidence method missing'); continue
            if plan.get('suffices_for') not in {'next_decision', 'final_claim'}: fail('invalid evidence purpose')
            if plan.get('status') not in {'planned', 'available', 'checked', 'disputed'}: fail('invalid evidence status')
    inapp = c.get('inapplicable_requirements')
    if not isinstance(inapp, list): fail('inapplicable_requirements must be a list')
    else:
        for item in inapp:
            if not isinstance(item, dict) or not all(nonempty(item.get(k)) for k in ('requirement', 'reason')):
                fail('inapplicable requirement needs a reason')
    codings = c.get('codings')
    if not isinstance(codings, list): fail('codings must be a list; an empty list is valid')
    else:
        for coding in codings:
            if not isinstance(coding, dict): fail('coding must be an object'); continue
            if coding.get('code') not in CODES: fail('invalid M code')
            if coding.get('role') not in ROLES: fail('invalid coding role')
            if not nonempty(coding.get('anchor')): fail('coding anchor missing')
            if not nonempty(coding.get('rationale')): fail('coding rationale missing')
    refs = c.get('source_ids')
    if not isinstance(refs, list) or not refs or any(r not in source_ids for r in refs):
        fail('unknown or absent source')
    if c.get('dataset_role') not in {'development', 'holdout', 'operational'}: fail('invalid dataset role')
    if c.get('dataset_role') == 'holdout' and c.get('selection_history'):
        fail('holdout already used for selection: reclassify and record contamination')
    if c.get('is_synthetic') and c.get('dataset_role') == 'holdout':
        fail('public synthetic examples in this release are development only')
    if c.get('work_status') not in STATES: fail('invalid work_status')
    if c.get('work_status') == 'complete' and not nonempty(c.get('completion_basis')):
        fail('complete record needs a completion_basis; this is not a truth check')
    return errors


def duplicate_ids(items: list[dict]) -> list[str]:
    return [key for key, n in Counter(x.get('id') for x in items).items() if n > 1]


def check_links(root: Path) -> list[str]:
    errors = []
    for path in root.rglob('*.md'):
        if any(p in {'archive', 'outputs', '.git'} for p in path.relative_to(root).parts):
            continue  # Historical bytes are not rewritten for modern navigation.
        text = re.sub(r'```.*?```', '', path.read_text(encoding='utf-8'), flags=re.S)
        for match in re.finditer(r'(?<!!)\[[^\]\n]*\]\(([^\s)]+)\)', text):
            target = match.group(1).strip('<>')
            if re.match(r'^[A-Za-z][A-Za-z0-9+.-]*:', target) or target.startswith('#'): continue
            destination = (path.parent / unquote(target.split('#')[0])).resolve()
            try: destination.relative_to(root.resolve())
            except ValueError:
                errors.append(f'{path.relative_to(root)}: link escapes repository'); continue
            if not destination.exists(): errors.append(f'{path.relative_to(root)}: missing {target}')
    return errors


def validate_repo(root: Path = ROOT) -> dict:
    errors: list[str] = []
    version = (root / 'VERSION').read_text().strip()
    sources = load(root / 'data/sources.json')['sources']
    source_ids = {s['id'] for s in sources}
    cases = load(root / 'data/cases.json')['cases']
    rules = load(root / 'data/rules.json')['rules']
    examples = load(root / 'examples/claims.json')['claims']
    fixtures = load(root / 'evaluation/development-cases.json')['cases']
    for label, items in [('sources', sources), ('cases', cases), ('rules', rules), ('examples', examples), ('fixtures', fixtures)]:
        if duplicate_ids(items): errors.append(f'{label}: duplicate ids')
    if len(cases) != 48: errors.append('expected 48 inherited development entries')
    if Counter(c['cohort'] for c in cases) != Counter({'MAS': 10, 'OPD': 24, 'cross_domain': 14}):
        errors.append('cohort sizes changed without migration')
    for c in cases:
        if c.get('dataset_role') != 'development': errors.append(f"{c['id']}: inherited case cannot be holdout")
        if any(s not in source_ids for s in c.get('source_ids', [])): errors.append(f"{c['id']}: unknown source")
        if c.get('verification_status') != 'not_reverified_in_v0.3': errors.append(f"{c['id']}: verification upgrade needs explicit release migration")
        if any(code not in CODES for code in c.get('candidate_codes', [])): errors.append(f"{c['id']}: invalid candidate code")
        if c.get('coding_role') not in ROLES: errors.append(f"{c['id']}: invalid coding role")
        if c['cohort'] == 'cross_domain' and c.get('award_verified_in_release') is not False:
            errors.append(f"{c['id']}: inherited award is not currently verified")
    if {r['id'] for r in rules} != {f'R{i:02}' for i in range(1, 13)}: errors.append('rule IDs incomplete')
    for r in rules:
        if any(x not in CODES for x in r['codes']): errors.append(f"{r['id']}: unknown code")
        if any(x not in source_ids for x in r['source_ids']): errors.append(f"{r['id']}: unknown source")
    for c in examples + [load(root / 'templates/claim.json')]: errors.extend(validate_claim(c, source_ids))
    if {p for c in examples for p in c['contribution_types']} != PROFILES: errors.append('example profiles incomplete')
    if len(fixtures) != 12 or {c['profile'] for c in fixtures} != PROFILES: errors.append('development fixtures incomplete')
    if any(c['dataset_role'] != 'development' for c in fixtures): errors.append('public fixtures are not holdout')
    plan = load(root / 'evaluation/plan.json')
    if plan['prospective_results_available'] or plan['formal_preregistration']: errors.append('pilot status was upgraded without actual evidence')
    for path in root.rglob('*.json'):
        if any(p in {'outputs', '.git'} for p in path.relative_to(root).parts): continue
        try: load(path)
        except (ValueError, UnicodeError) as exc: errors.append(f'{path.relative_to(root)}: {exc}')
    manifest = load(root / 'archive/manifest.json')
    for item in manifest['files']:
        p = item.get('repository_copy')
        if p:
            actual = root / p
            if hashlib.sha256(actual.read_bytes()).hexdigest() != item['sha256']:
                errors.append(f'{p}: historical bytes changed')
    errors.extend(check_links(root))
    return {'version': version, 'scope': 'engineering_integrity_only', 'passed': not errors,
            'case_counts': dict(Counter(c['cohort'] for c in cases)), 'example_cards': len(examples),
            'development_fixtures': len(fixtures), 'rules': len(rules), 'errors': errors,
            'scientific_validity_tested': False, 'prospective_effectiveness_tested': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json-out', type=Path)
    args = parser.parse_args()
    try: report = validate_repo()
    except (OSError, ValueError, KeyError, TypeError) as exc:
        report = {'passed': False, 'scope': 'engineering_integrity_only', 'errors': [str(exc)]}
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(rendered + '\n', encoding='utf-8')
    raise SystemExit(0 if report['passed'] else 1)

if __name__ == '__main__': main()
