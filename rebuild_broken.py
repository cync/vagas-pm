#!/usr/bin/env python3
"""rebuild_broken.py -- Rebuild broken_links.json by actually checking all URLs.
No more blanket marking by date or company. Every URL is verified via API/HTTP."""
import re, json, sys
from pathlib import Path
from datetime import date

from link_checker import BrokenCache, check_urls_parallel, normalize_url

SITE_DIR    = Path(__file__).parent
VAGAS_SUB   = SITE_DIR / "vagas"
VAGAS_ROOT  = SITE_DIR.parent
BROKEN_PATH = SITE_DIR / "broken_links.json"

URL_RE = re.compile(r'\[(?:Ver vaga|Aplicar|Apply)\]\((https?://[^)]+)\)')

def collect_all_urls():
    urls = set()
    for folder in [VAGAS_SUB, VAGAS_ROOT]:
        for pattern in ['vagas_pm_*.md', 'vagas_uiux_*.md']:
            for f in folder.glob(pattern):
                try:
                    text = f.read_bytes().rstrip(b'\x00').decode('utf-8', errors='replace')
                    for u in URL_RE.findall(text):
                        urls.add(normalize_url(u.strip()))
                except Exception:
                    pass
    return urls

def main():
    do_check = "--check" in sys.argv
    all_urls = collect_all_urls()
    cache = BrokenCache(BROKEN_PATH)

    if do_check:
        print(f"Checking {len(all_urls)} URLs via API/HTTP...")
        results = check_urls_parallel(sorted(all_urls))
        newly_broken = {u for u, dead in results.items() if dead}
        newly_alive = {u for u, dead in results.items() if not dead}

        # Remove URLs from broken cache that are now alive
        recovered = cache.broken & newly_alive
        for u in recovered:
            cache.mark_ok(u, date.today().isoformat())

        cache.add_broken_batch(newly_broken)
        cache.save()

        print(f"Results: {len(newly_alive)} alive, {len(newly_broken)} dead")
        if recovered:
            print(f"  {len(recovered)} URLs recovered from broken cache")
        for u in sorted(newly_broken):
            print(f"  DEAD: {u}")
    else:
        # Without --check, just prune broken cache to only URLs that still exist in .md files
        stale = cache.broken - all_urls
        if stale:
            for u in stale:
                cache._broken.discard(u)
            cache.save()
            print(f"Pruned {len(stale)} stale URLs from broken cache")
        print(f"Total URLs in .md files: {len(all_urls)}")
        print(f"Total in broken cache: {len(cache.broken)}")
        print(f"Run with --check to verify all URLs via API/HTTP")

if __name__ == '__main__':
    main()
