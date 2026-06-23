#!/usr/bin/env python3
"""clean_ashby.py -- Remove broken URLs from all vagas files
using broken_links.json as source of truth."""
import re
from pathlib import Path

from link_checker import BrokenCache, normalize_url

site = Path(__file__).parent
BROKEN_PATH = site / "broken_links.json"
URL_RE = re.compile(r'\[(?:Ver vaga|Aplicar|Apply)\]\((https?://[^)]+)\)')

cache = BrokenCache(BROKEN_PATH)
removed = 0

for f in list((site / 'vagas').glob('vagas_pm_*.md')) + list((site / 'vagas').glob('vagas_uiux_*.md')):
    try:
        text = f.read_bytes().rstrip(b'\x00').decode('utf-8', errors='replace')
    except Exception:
        continue
    lines = text.split('\n')
    clean = []
    for l in lines:
        drop = False
        urls = URL_RE.findall(l)
        for url in urls:
            if cache.is_broken(url):
                drop = True
                break
        if not drop:
            clean.append(l)
    if len(clean) != len(lines):
        removed += len(lines) - len(clean)
        f.write_text('\n'.join(clean), encoding='utf-8')

print(f'clean_ashby: removed {removed} broken rows.')
