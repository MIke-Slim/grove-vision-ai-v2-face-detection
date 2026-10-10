"""Verify every versioned model/firmware artifact using the repository manifest."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
manifest = json.loads((root/'manifest.json').read_text(encoding='utf-8'))
failures = []
for relative, expected in manifest['files'].items():
    path = root / relative
    if not path.is_file():
        failures.append(f'Missing: {relative}')
        continue
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    if path.stat().st_size != expected['bytes'] or digest != expected['sha256']:
        failures.append(f'Mismatch: {relative}')
    else:
        print(f'PASS {relative}')
if failures:
    raise SystemExit('\n'.join(failures))
print(f'All {len(manifest["files"])} artifact checks passed.')
