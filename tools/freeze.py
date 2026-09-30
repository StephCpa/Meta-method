#!/usr/bin/env python3
"""Version/run/selected-file content snapshots with no-clobber output and verification.

Standard library only. Content hashes are neither authentication nor trusted
external timestamps. Run snapshots record inputs; they do not execute trials.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {'.git', '__pycache__', '.pytest_cache', '.venv', 'outputs', 'private', 'node_modules'}


def canonical(obj) -> bytes:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def relative_file(root: Path, name: str) -> Path:
    root = root.resolve()
    p = Path(name)
    if p.is_absolute() or '..' in p.parts or '\\' in name:
        raise ValueError(f'Unsafe relative path: {name}')
    current = root
    for part in p.parts:
        current /= part
        if current.is_symlink():
            raise ValueError(f'Symlink input is not accepted: {name}')
    current.resolve().relative_to(root)
    if not current.is_file():
        raise ValueError(f'Not a regular file: {name}')
    return current


def version_paths(root: Path) -> list[str]:
    names = []
    for p in root.rglob('*'):
        rel = p.relative_to(root)
        if any(x in EXCLUDED for x in rel.parts) or p.name == '.DS_Store' or p.name.startswith('.env'):
            continue
        if p.is_symlink():
            raise ValueError(f'Symlink in version scope: {rel}')
        if p.is_file() and not p.name.endswith(('.pyc', '.tmp')):
            names.append(rel.as_posix())
    return sorted(names)


def build_manifest(root: Path, paths: list[str], snapshot_type: str = 'selected_files', metadata: dict | None = None) -> dict:
    if not paths:
        raise ValueError('At least one input is required')
    if snapshot_type not in ('version', 'run', 'selected_files'):
        raise ValueError('Unknown snapshot type')
    entries, seen = [], set()
    for name in paths:
        p = relative_file(root, name)
        rel = p.relative_to(root.resolve()).as_posix()
        if rel in seen:
            raise ValueError(f'Duplicate input: {rel}')
        seen.add(rel)
        data = p.read_bytes()
        entries.append({'path': rel, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
    result = {'format_version': 2, 'kind': 'local_content_freeze', 'snapshot_type': snapshot_type,
              'external_preregistration': False, 'independent_timestamp': False,
              'scope_note': 'Version excludes .git, runtime outputs, private material and credentials; run uses explicit manifests.',
              'files': sorted(entries, key=lambda e: e['path']), 'metadata': metadata or {}}
    result['content_digest'] = hashlib.sha256(canonical(result)).hexdigest()
    return result


def build_run_manifest(root: Path, config_path: str, allow_draft: bool = False) -> dict:
    from protocol import validate_materials, run_readiness
    config = json.loads(relative_file(root, config_path).read_text(encoding='utf-8'))
    gaps = run_readiness(config)
    if gaps and not allow_draft:
        raise ValueError('Run is not ready; set parameters or explicitly use --draft: ' + ', '.join(gaps))
    if not isinstance(config, dict):
        raise ValueError('Run config must be an object')
    mpath = config.get('material_manifest', '')
    materials = json.loads(relative_file(root, mpath).read_text(encoding='utf-8'))
    errors = validate_materials(materials, root)
    if errors:
        raise ValueError('; '.join(errors))
    inputs = set(config.get('case_inputs', []))
    references = set(config.get('reference_inputs', []))
    arm_files = {a: sorted(set(d['files']) | inputs) for a, d in materials['arms'].items()}
    if any(references & set(files) for files in arm_files.values()):
        raise ValueError('Evaluator references leaked into participant materials')
    paths = {config_path, mpath, config['evaluation_rule'], 'VERSION', 'schemas/claim.schema.json',
             'tools/freeze.py', 'tools/protocol.py', 'tools/records.py', 'tools/validate.py',
             'tools/evaluate.py', 'requirements.txt'} | references
    for key in ('statistical_protocol', 'sample_plan'):
        if isinstance(config.get(key), str) and config[key]:
            paths.add(config[key])
    for files in arm_files.values():
        paths.update(files)
    return build_manifest(root, sorted(paths), 'run', {
        'run_config': config, 'arm_materials': arm_files, 'evaluator_only': sorted(references),
        'readiness': 'draft_incomplete' if gaps else 'declared_configuration_ready',
        'missing_configuration': gaps,
        'execution_status': 'not_run_by_freeze_tool'})


def write_new_output(root: Path, output: Path, result: dict, protected: list[str] | None = None) -> Path:
    """Write only a NEW regular file below outputs/. No --force or source override."""
    root = root.resolve()
    output = output if output.is_absolute() else root / output
    if '..' in output.parts:
        raise ValueError('Output traversal is not allowed')
    try:
        rel = output.relative_to(root)
    except ValueError as exc:
        raise ValueError('Output must be inside repository outputs/') from exc
    if len(rel.parts) < 2 or rel.parts[0] != 'outputs':
        raise ValueError('Source and record paths are protected; write below outputs/')
    current = root
    for part in rel.parts:
        current /= part
        if current.is_symlink():
            raise ValueError('Symlink output paths are not accepted')
    if output.resolve() in {(root / p).resolve() for p in protected or []}:
        raise ValueError('Output cannot overwrite a frozen input')
    if output.exists():
        raise FileExistsError(f'Output already exists: {rel}')
    payload = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    output.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(output, flags, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as stream:
        stream.write(payload)
    return output


def verify_manifest(root: Path, manifest: object) -> dict:
    report = {'matches': False, 'missing': [], 'changed': [], 'not_frozen': [], 'invalid': [],
              'external_timestamp_verified': False}
    if not isinstance(manifest, dict) or manifest.get('format_version') != 2 or not isinstance(manifest.get('files'), list):
        report['invalid'].append('Expected a format_version=2 manifest; legacy snapshots use validate --snapshot.')
        return report
    body = {k: v for k, v in manifest.items() if k not in ('content_digest', 'generated_at_utc', 'clock_note')}
    try:
        if hashlib.sha256(canonical(body)).hexdigest() != manifest.get('content_digest'):
            report['invalid'].append('Manifest content digest mismatch')
    except (ValueError, TypeError):
        report['invalid'].append('Manifest is not valid JSON')
    listed = set()
    for entry in manifest['files']:
        if not isinstance(entry, dict) or not isinstance(entry.get('path'), str):
            report['invalid'].append('Malformed entry'); continue
        name = entry['path']
        if name in listed:
            report['invalid'].append('Duplicate path: ' + name); continue
        listed.add(name)
        try:
            p = relative_file(root, name)
        except ValueError as exc:
            raw = root / name
            if not Path(name).is_absolute() and '..' not in Path(name).parts and not raw.exists() and not raw.is_symlink():
                report['missing'].append(name)
            else:
                report['invalid'].append(str(exc))
            continue
        data = p.read_bytes()
        if len(data) != entry.get('bytes') or hashlib.sha256(data).hexdigest() != entry.get('sha256'):
            report['changed'].append(name)
    try:
        report['not_frozen'] = sorted(set(version_paths(root)) - listed)
    except ValueError as exc:
        report['invalid'].append(str(exc))
    report['matches'] = not (report['missing'] or report['changed'] or report['invalid'] or
                            (manifest.get('snapshot_type') == 'version' and report['not_frozen']))
    report['scope'] = manifest.get('snapshot_type')
    report['note'] = 'not_frozen means outside declared file scope, not evidence of prior absence or authenticity.'
    return report


def main():
    argv = sys.argv[1:]
    if not argv or argv[0] not in ('create', 'verify'):
        argv.insert(0, 'create')  # Backwards compatible invocation, safer default scope.
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    create = sub.add_parser('create')
    create.add_argument('paths', nargs='*')
    create.add_argument('--kind', choices=('version', 'run'), default='version')
    create.add_argument('--config')
    create.add_argument('--draft', action='store_true')
    create.add_argument('--out', type=Path)
    verify = sub.add_parser('verify')
    verify.add_argument('manifest', type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == 'verify':
            report = verify_manifest(ROOT, json.loads(args.manifest.read_text(encoding='utf-8')))
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0 if report['matches'] else 1
        if args.kind == 'run':
            if not args.config or args.paths:
                raise ValueError('Run freeze needs --config and no positional paths')
            result = build_run_manifest(ROOT, args.config, args.draft)
        else:
            if args.config or args.draft:
                raise ValueError('--config / --draft only apply to run snapshots')
            result = build_manifest(ROOT, args.paths or version_paths(ROOT),
                                    'selected_files' if args.paths else 'version')
        result['generated_at_utc'] = datetime.now(timezone.utc).isoformat()
        result['clock_note'] = 'Local clock only, not trusted external preregistration.'
        output = args.out or Path('outputs/freezes') / (uuid.uuid4().hex + '.json')
        saved = write_new_output(ROOT, output, result, [e['path'] for e in result['files']])
        print(json.dumps({'path': str(saved), 'content_digest': result['content_digest'],
                          'files': len(result['files']), 'scope': result['snapshot_type']}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.error(str(exc))

if __name__ == '__main__':
    raise SystemExit(main())
