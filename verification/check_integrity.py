"""Verify release files and the documented display-name changes against V2."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
records = json.loads((ROOT / 'verification/source-integrity.json').read_text())
failures = []
for record in records:
    path = ROOT / record['file']
    if not path.is_file():
        failures.append(record['file'])
        continue
    content = path.read_bytes()
    expected = record.get('published_sha256', record['sha256'])
    if hashlib.sha256(content).hexdigest() != expected:
        failures.append(record['file'])
        continue
    if record.get('display_replacements'):
        restored = content.decode()
        for replacement in record['display_replacements']:
            restored = restored.replace(replacement['after'], replacement['before'])
        if hashlib.sha256(restored.encode()).hexdigest() != record['sha256']:
            failures.append(record['file'])
if failures:
    raise SystemExit('Changed or missing release files: ' + ', '.join(failures))
print(f'PASS: {len(records)} application/dependency files verified; only documented display-name changes differ from V2.')
