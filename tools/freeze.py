#!/usr/bin/env python3
"""Create a local content manifest; NOT a trusted timestamp or preregistration."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULTS = ['VERSION', 'docs/framework.md', 'docs/codebook.md', 'docs/evidence-profiles.md',
            'docs/conditional-contracts.md', 'evaluation/pilot-protocol.md', 'evaluation/rubric.md',
            'evaluation/workflow-prompts.md', 'evaluation/plan.json', 'evaluation/development-cases.json']


def build_manifest(root: Path, paths: list[str]) -> dict:
    root = root.resolve()
    if not paths: raise ValueError('at least one input is required')
    entries = []
    seen = set()
    for name in paths:
        p = (root / name).resolve()
        try: rel = p.relative_to(root).as_posix()
        except ValueError as exc: raise ValueError('path escapes repository') from exc
        if rel in seen: raise ValueError(f'duplicate input: {rel}')
        if not p.is_file(): raise ValueError(f'not a regular file: {rel}')
        seen.add(rel)
        data = p.read_bytes()
        entries.append({'path': rel, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
    entries.sort(key=lambda e: e['path'])
    digest = hashlib.sha256(json.dumps(entries, ensure_ascii=False, sort_keys=True,
                                       separators=(',', ':')).encode()).hexdigest()
    return {'kind': 'local_content_freeze', 'external_preregistration': False,
            'independent_timestamp': False, 'files': entries, 'content_digest': digest}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('paths', nargs='*')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    try: result = build_manifest(ROOT, args.paths or DEFAULTS)
    except (OSError, ValueError) as exc: parser.error(str(exc))
    output = args.out.resolve()
    if output in {(ROOT / e['path']).resolve() for e in result['files']}:
        parser.error('output cannot overwrite a frozen input')
    result['generated_at_utc'] = datetime.now(timezone.utc).isoformat()
    result['clock_note'] = 'Local runtime clock, not a trusted time authority.'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(result['content_digest'])

if __name__ == '__main__': main()
