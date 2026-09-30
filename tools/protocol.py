"""Check treatment contents and proposed run readiness, not scientific outcomes."""
from __future__ import annotations
from pathlib import Path


def validate_materials(m: object, root: Path | None = None) -> list[str]:
    if not isinstance(m, dict) or not isinstance(m.get('arms'), dict):
        return ['Materials must have an arms object']
    errors = []
    sets = {}
    for arm in ('A', 'B', 'C'):
        spec = m['arms'].get(arm)
        files = spec.get('files') if isinstance(spec, dict) else None
        if not isinstance(files, list) or not files or not all(isinstance(x, str) and x for x in files):
            errors.append(f'{arm}: file manifest missing'); continue
        if len(files) != len(set(files)):
            errors.append(f'{arm}: duplicate material')
        sets[arm] = set(files)
        for name in files:
            p = Path(name)
            if p.is_absolute() or '..' in p.parts:
                errors.append(f'{arm}: unsafe material path'); continue
            if root is not None and not (root / p).is_file():
                errors.append(f'{arm}: missing material {name}')
    if len(sets) != 3:
        return errors
    common = set(m.get('common_files', []))
    if not all(common <= sets[a] for a in sets):
        errors.append('Common instructions must be supplied to all arms')
    increment = set(m.get('codebook_increment_files', []))
    if not increment or sets['C'] - sets['B'] != increment or sets['B'] - sets['C']:
        errors.append('C must equal B plus exactly the declared codebook and coding operations')
    if increment & sets['B']:
        errors.append('Codebook increment leaked into B')
    for name in m.get('shared_contract_files', []):
        if name not in sets['B'] or name not in sets['C']:
            errors.append('Conditional contracts must be identical in B and C')
    return errors


def run_readiness(c: object) -> list[str]:
    if not isinstance(c, dict):
        return ['Run configuration must be an object']
    missing = []
    def require(path, test=lambda x: isinstance(x, str) and bool(x.strip())):
        value = c
        for key in path.split('.'):
            value = value.get(key) if isinstance(value, dict) else None
        if not test(value):
            missing.append(path)
    require('run_id')
    if isinstance(c.get('run_id'), str) and c['run_id'].startswith('TEMPLATE'):
        missing.append('run_id must identify an actual planned run')
    require('phase', lambda x: x in ('pilot', 'confirmation'))
    for key in ('case_inputs', 'reference_inputs', 'dataset_identifiers'):
        require(key, lambda x: isinstance(x, list) and bool(x) and all(isinstance(v, str) and v for v in x))
    for key in ('input_tokens', 'output_tokens', 'tool_calls', 'time_limit_seconds'):
        require('budget.' + key, lambda x: type(x) is int and x >= 0)
    for key in ('git_commit', 'model_id', 'executor_version'):
        require('implementation.' + key)
    require('randomization.unit')
    require('randomization.seed', lambda x: type(x) is int)
    for key in ('stopping_rule', 'source_cutoff', 'evaluation_rule', 'material_manifest', 'statistical_protocol', 'sample_plan'):
        require(key)
    for key in ('minimum_meaningful_omission_improvement', 'maximum_tolerated_severe_overreach_increase'):
        require('acceptance.' + key, lambda x: type(x) in (int, float) and 0 <= x <= 1)
    cases = c.get('case_inputs', [])
    refs = c.get('reference_inputs', [])
    if isinstance(cases, list) and isinstance(refs, list) and all(isinstance(x, str) for x in cases + refs) and set(cases) & set(refs):
        missing.append('Participant inputs overlap evaluator-only references')
    return missing
