#!/usr/bin/env python3
"""apply_patch.py -- Patches generate_site.py with null-byte safe broken-link filter.
Idempotent: detects v1 and upgrades to v2. Skips if already patched."""
from pathlib import Path

SITE_DIR = Path(__file__).parent
target = SITE_DIR / "generate_site.py"

OLD = (
    '_broken_path = SITE_DIR / "broken_links.json"\n'
    '_broken: set = set()\n'
    'if _broken_path.exists():\n'
    '    _broken = set(json.loads(_broken_path.read_text(encoding="utf-8")).get("broken", []))\n'
    '    for r in runs:\n'
    '        r["jobs"] = [j for j in r["jobs"] if j.get("url") not in _broken]\n'
    '        r["novas"] = len(r["jobs"])\n'
    '    for r in uiux_runs:\n'
    '        r["jobs"] = [j for j in r["jobs"] if j.get("url") not in _broken]\n'
    '        r["novas"] = len(r["jobs"])'
)
NEW = (
    '_broken_path = SITE_DIR / "broken_links.json"\n'
    '_broken: set = set()\n'
    'from urllib.parse import unquote as _unquote\n'
    'if _broken_path.exists():\n'
    '    try:\n'
    '        _raw = _broken_path.read_bytes().rstrip(b"\\x00").decode("utf-8")\n'
    '        _broken_raw = set(json.loads(_raw).get("broken", []))\n'
    '        _broken = _broken_raw | {_unquote(u) for u in _broken_raw}\n'
    '    except Exception:\n'
    '        pass\n'
    'def _is_broken(url):\n'
    '    return bool(_broken) and (url in _broken or _unquote(url) in _broken)\n'
    'for r in runs:\n'
    '    r["jobs"] = [j for j in r["jobs"] if not _is_broken(j.get("url", ""))]\n'
    '    r["novas"] = len(r["jobs"])\n'
    'for r in uiux_runs:\n'
    '    r["jobs"] = [j for j in r["jobs"] if not _is_broken(j.get("url", ""))]\n'
    '    r["novas"] = len(r["jobs"])'
)

try:
    content = target.read_bytes().rstrip(b'\x00').decode('utf-8', errors='replace')
except Exception as e:
    print(f'apply_patch: cannot read generate_site.py: {e}'); exit(1)

if NEW in content:
    print('apply_patch: already patched (v2), nothing to do.')
elif OLD in content:
    patched = content.replace(OLD, NEW)
    target.write_text(patched, encoding='utf-8')
    print('apply_patch: upgraded v1 -> v2.')
else:
    print('apply_patch: WARNING -- pattern not found (file may be truncated).')
