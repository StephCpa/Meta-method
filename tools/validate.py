#!/usr/bin/env python3
"""Working-record integrity; use --snapshot for immutable release comparison.

Uses the actual claim JSON Schema, with separate referential and review checks.
Does not adjudicate scientific truth or run a prospective study.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import unquote
from records import assess_claim, load_json, schema_errors
from protocol import validate_materials
from freeze import write_new_output, relative_file, version_paths

ROOT = Path(__file__).resolve().parents[1]
PROFILES = {'theory', 'explanation', 'algorithm', 'system', 'data_evaluation', 'decision'}
CODES = {f'M{i}' for i in range(1, 15)}
ROLES = {'author', 'review', 'proposal'}
load = load_json


def validate_claim(c: object, source_ids: set[str]) -> list[str]:
    """Compatibility API: errors only. Use assess_claim to retain needs_review."""
    return assess_claim(c, source_ids)['errors']


def duplicate_ids(items: list[dict]) -> list[str]:
    ids = [x.get('id') for x in items if isinstance(x, dict) and isinstance(x.get('id'), str)]
    return [key for key, n in Counter(ids).items() if n > 1]


def check_links(root: Path) -> list[str]:
    errors = []
    for path in root.rglob('*.md'):
        if any(p in {'archive', 'outputs', '.git', 'private', '.venv'} for p in path.relative_to(root).parts):
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


def validate_snapshot(root: Path, snapshot: dict) -> dict:
    errors = []
    listed = set()
    for item in snapshot.get('files', []):
        name = item.get('path', '')
        if name in listed:
            errors.append('Duplicate snapshot path: ' + name)
        listed.add(name)
        try:
            p = relative_file(root, name)
            data = p.read_bytes()
            if len(data) != item.get('bytes') or hashlib.sha256(data).hexdigest() != item.get('sha256'):
                errors.append('Changed: ' + name)
        except (OSError, ValueError) as exc:
            errors.append(str(exc))
    if not listed:
        errors.append('Empty release snapshot')
    extra = sorted(set(version_paths(root)) - listed)
    return {'scope': 'explicit_release_snapshot', 'passed': not errors and not extra,
            'version': snapshot.get('version'), 'errors': errors, 'not_in_snapshot': extra}


def validate_repo(root: Path = ROOT) -> dict:
    errors, reviews = [], []
    version = (root / 'VERSION').read_text().strip()
    def collection(name, key):
        value = load(root / name)
        items = value.get(key) if isinstance(value, dict) else None
        if not isinstance(items, list) or not all(isinstance(i, dict) and isinstance(i.get('id'), str) for i in items):
            errors.append(f'{name}: expected a list of records with string IDs')
            return []
        if duplicate_ids(items):
            errors.append(f'{name}: duplicate IDs')
        return items
    sources = collection('data/sources.json', 'sources')
    source_ids = {s['id'] for s in sources}
    cases = collection('data/cases.json', 'cases')
    rules = collection('data/rules.json', 'rules')
    examples = collection('examples/claims.json', 'claims')
    fixtures = collection('evaluation/development-cases.json', 'cases')
    for c in cases:
        refs = c.get('source_ids')
        if not isinstance(refs, list) or not refs or any(x not in source_ids for x in refs):
            errors.append(f"{c['id']}: unknown / missing source")
        if c.get('dataset_role') not in ('development', 'holdout_candidate', 'holdout', 'operational'):
            errors.append(f"{c['id']}: invalid dataset role")
        # Development may never silently be relabelled as held out. New records
        # may be added without changing validators or historical snapshot counts.
        if c.get('dataset_role') in ('holdout', 'holdout_candidate'):
            from records import assess_holdout
            h = assess_holdout(c)
            if h['status'] == 'ineligible': errors.append(f"{c['id']}: contaminated holdout")
            elif h['status'] == 'needs_review': reviews.append(f"{c['id']}: holdout independence needs review")
            if set(refs or []) & {'SRC-MAS', 'SRC-OPD', 'SRC-CROSS', 'SRC-V02'}:
                errors.append(f"{c['id']}: inherited development material cannot become holdout")
        if any(code not in CODES for code in c.get('candidate_codes', [])) or c.get('coding_role') not in ROLES:
            errors.append(f"{c['id']}: invalid coding")
        # Real source verification is allowed to grow; require a traceable record.
        if c.get('verification_status') not in ('not_reverified_in_v0.3', 'unverified', 'pending') or c.get('award_verified_in_release'):
            v = c.get('verification_record', {})
            if not all(isinstance(v.get(k), str) and v[k].strip() for k in ('source_version', 'locator', 'action', 'date')):
                errors.append(f"{c['id']}: verification upgrade needs source_version/locator/action/date")
    for r in rules:
        if any(x not in CODES for x in r.get('codes', [])): errors.append(f"{r['id']}: unknown M code")
        if any(x not in source_ids for x in r.get('source_ids', [])): errors.append(f"{r['id']}: unknown source")
    schema = load(root / 'schemas/claim.schema.json')
    for c in examples + [load(root / 'templates/claim.json')]:
        result = assess_claim(c, source_ids, schema)
        cid = c.get('id', '?') if isinstance(c, dict) else '<non-object>'
        errors.extend(f"{cid}: {x}" for x in result['errors'])
        reviews.extend(f"{cid}: {x}" for x in result['review_required'])
    for c in fixtures:
        if c.get('dataset_role') != 'development': errors.append(f"{c['id']}: public development fixture cannot be holdout")
        if c.get('profile') not in PROFILES: errors.append(f"{c['id']}: unknown profile")
    errors.extend(validate_materials(load(root / 'evaluation/materials.json'), root))
    plan = load(root / 'evaluation/plan.json')
    if plan.get('prospective_results_available') and not plan.get('results_record'):
        errors.append('Prospective results require a traceable results_record')
    if plan.get('formal_preregistration') and not plan.get('preregistration_record'):
        errors.append('Preregistration requires a traceable record')
    for path in root.rglob('*.json'):
        if any(p in {'outputs', 'private', '.git', '.venv'} for p in path.relative_to(root).parts): continue
        try: load(path)
        except (ValueError, UnicodeError) as exc: errors.append(f'{path.relative_to(root)}: {exc}')
    for item in load(root / 'archive/manifest.json')['files']:
        name = item.get('repository_copy')
        if name and hashlib.sha256(relative_file(root, name).read_bytes()).hexdigest() != item['sha256']:
            errors.append(f'{name}: archived bytes changed')
    from generation import check_records
    generation_report = check_records(root)
    errors.extend(generation_report['errors'])
    errors.extend(check_links(root))
    return {'version': version, 'scope': 'engineering_integrity_only', 'passed': not errors,
            'status': 'invalid' if errors else 'needs_review' if reviews else 'valid',
            'case_counts': dict(Counter(c.get('cohort', 'unspecified') for c in cases)),
            'example_cards': len(examples), 'development_fixtures': len(fixtures), 'rules': len(rules),
            'errors': errors, 'review_required': reviews,
            'author_move_records': generation_report['author_records'], 'generative_cards': generation_report['move_cards'],
            'scientific_validity_tested': False, 'prospective_effectiveness_tested': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--claim', type=Path)
    group.add_argument('--snapshot', type=Path)
    parser.add_argument('--json-out', type=Path)
    args = parser.parse_args()
    try:
        if args.claim:
            refs = {s['id'] for s in load(args.root / 'data/sources.json')['sources']}
            report = assess_claim(load(args.claim), refs, load(args.root / 'schemas/claim.schema.json'))
        elif args.snapshot:
            report = validate_snapshot(args.root, load(args.snapshot))
        else: report = validate_repo(args.root)
        if args.json_out:
            write_new_output(args.root, args.json_out, report)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        report = {'passed': False, 'status': 'invalid', 'errors': [str(exc)]}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report.get('errors') or report.get('passed') is False: return 1
    return 2 if report.get('status') == 'needs_review' else 0

if __name__ == '__main__': raise SystemExit(main())
