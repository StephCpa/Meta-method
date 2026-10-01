#!/usr/bin/env python3
"""One-time lossless import of the user-approved analysis library.

No downloads, eval, model requests, or extraction of executable archives.
The payload is a bounded XZ-compressed JSON map of UTF-8 text files.
"""
from pathlib import Path, PurePosixPath
import hashlib
import json
import lzma

ROOT = Path(__file__).resolve().parents[1]
TRANSFER = ROOT / '.library-transfer'


def no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key')
        result[key] = value
    return result


def checked_bytes(path, expected):
    if path.is_symlink() or not path.is_file():
        raise ValueError('Expected a regular file')
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError('SHA-256 mismatch: ' + str(path.relative_to(ROOT)))
    return data


def main():
    spec = json.loads((TRANSFER / 'manifest.json').read_text())
    if spec['files'] != 334 or spec['bytes'] != 111336 or spec['decoded_bytes'] != 1418202:
        raise ValueError('Unexpected import scope')
    if (ROOT / 'paper-library').exists() or (ROOT / 'paper-library').is_symlink():
        raise ValueError('Refusing to replace an existing library')
    chunks = []
    for index, item in enumerate(spec['chunks']):
        name = f'.library-transfer/part-{index:03d}'
        if item['path'] != name:
            raise ValueError('Unexpected chunk path or order')
        data = (ROOT / name).read_bytes()
        git_sha = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        if len(data) != item['bytes'] or git_sha != item['sha']:
            raise ValueError('Chunk integrity failure')
        chunks.append(data)
    packed = b''.join(chunks)
    if len(packed) != spec['bytes'] or hashlib.sha256(packed).hexdigest() != spec['sha256']:
        raise ValueError('Archive integrity failure')
    decoder = lzma.LZMADecompressor(memlimit=128 * 1024 * 1024)
    decoded = decoder.decompress(packed, max_length=spec['decoded_bytes'] + 1)
    if len(decoded) != spec['decoded_bytes'] or not decoder.eof or decoder.unused_data:
        raise ValueError('Decoded size or stream mismatch')
    payload = json.loads(decoded.decode('utf-8'), object_pairs_hook=no_duplicates)
    if not isinstance(payload, dict) or len(payload) != spec['files']:
        raise ValueError('Unexpected file map')
    for name, content in payload.items():
        p = PurePosixPath(name)
        if (not isinstance(content, str) or not name or p.is_absolute()
                or str(p) != name or '..' in p.parts or '\\' in name
                or any(x in {'.git', '.github', 'private', 'outputs', '__pycache__'} for x in p.parts)
                or any(x.startswith('.env') for x in p.parts)):
            raise ValueError('Unsafe library path')
    checked_bytes(ROOT / 'README.md', spec['readme_original_sha256'])
    readme = checked_bytes(TRANSFER / 'README.final.txt', spec['readme_final_sha256'])
    ci = checked_bytes(TRANSFER / 'ci.final.txt', spec['ci_sha256'])
    target_ci = ROOT / '.github/workflows/validate-paper-library.yml'
    if target_ci.exists() or target_ci.is_symlink():
        raise ValueError('Refusing to replace existing library workflow')
    for name, content in payload.items():
        target = ROOT / 'paper-library' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(content.encode('utf-8'))
    (ROOT / 'README.md').write_bytes(readme)
    with target_ci.open('xb') as stream:
        stream.write(ci)
    print(json.dumps({'files_imported': len(payload), 'archive_sha256': spec['sha256'],
                      'framework_version': (ROOT / 'VERSION').read_text().strip(),
                      'scope': 'user_approved_analysis_library_only'}))


if __name__ == '__main__':
    main()
