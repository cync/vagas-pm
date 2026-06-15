#!/usr/bin/env python3
"""clean_ashby.py -- Remove broken Ashby UUID and known-broken Greenhouse rows
from all vagas files in both site/vagas/ and parent folder."""
import re
from pathlib import Path

UUID = re.compile(r'[a-f0-9]{8}-[a-f0-9]{4}', re.I)
BROKEN_GH = re.compile(r'greenhouse\.io/(remotecom|nearform)/', re.I)
site = Path(__file__).parent
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
            if 'ashby' in l.lower() and UUID.search(l):
                drop = True
            if BROKEN_GH.search(l):
                drop = True
            if not drop:
                clean.append(l)
        if len(clean) != len(lines):
            removed += len(lines) - len(clean)
            f.write_text('\n'.join(clean), encoding='utf-8')

print(f'clean_ashby: removed {removed} broken rows.')
