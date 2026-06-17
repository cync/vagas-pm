#!/usr/bin/env python3
"""clean_ashby.py -- Remove broken Ashby UUID and known-broken URLs
from all vagas files using broken_links.json as source of truth."""
import re
from pathlib import Path

from link_checker import BrokenCache

site = Path(__file__).parent
BROKEN_PATH = site / "broken_links.json"
UUID = re.compile(r'[a-f0-9]{8}-[a-f0-9]{4}', re.I)
URL_RE = re.compile(r'\[(?:Ver vaga|Aplicar|Apply)\]\((https?://[^)]+)\)')

cache = BrokenCache(BROKEN_PATH)
removed = 0

for folder in [site / 'vagas', site.parent]:
    for f in list(folder.glob('vagas_pm_*.md')) + list(folder.glob('vagas_uiux_*.md')):
        try:
            text = f.read_bytes().rstrip(b'\x00').decode('utf-8', errors='replace')
        except Exception:
            continue
        lines = text.split('\n')
        clean = []
        for l in lines:
            drop = False
            # Ashby URLs with UUIDs are always broken
            if 'ashbyhq.com' in l.lower() and UUID.search(l):
                drop = True
            # Any URL in broken_links.json
            urls = URL_RE.findall(l)
            for url in urls:
                if cache.is_broken(url.strip()):
                    drop = True
                    break
            if not drop:
                clean.append(l)
        if len(clean) != len(lines):
            removed += len(lines) - len(lines)
            f.write_text('\n'.join(clean), encoding='utf-8')

print(f'clean_ashby: removed {removed} broken rows.')
