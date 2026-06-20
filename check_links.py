#!/usr/bin/env python3
"""check_links.py -- Verifica URLs de vagas e atualiza broken_links.json.
Usa link_checker.py para validação centralizada.
Re-verifica URLs "ok" com mais de 14 dias.
"""
import re, sys, time
from datetime import date, timedelta
from pathlib import Path

from link_checker import BrokenCache, is_dead_url, normalize_url

SITE_DIR    = Path(__file__).parent
VAGAS_DIR   = SITE_DIR / "vagas"
BROKEN_PATH = SITE_DIR / "broken_links.json"
STALE_DAYS  = 14

def collect_urls():
    urls = set()
    for pattern in ["vagas_pm_*.md", "vagas_uiux_*.md"]:
        for f in VAGAS_DIR.glob(pattern):
            try:
                text = f.read_bytes().rstrip(b'\x00').decode("utf-8", errors="replace")
                for u in re.findall(r'\[(?:Ver vaga|Aplicar|Apply)\]\((https?://[^)]+)\)', text):
                    urls.add(normalize_url(u))
            except Exception:
                pass
    return urls

def main():
    recheck_all = "--all" in sys.argv
    today_str   = date.today().isoformat()
    cutoff      = (date.today() - timedelta(days=STALE_DAYS)).isoformat()
    cache       = BrokenCache(BROKEN_PATH)
    all_urls    = collect_urls()

    stale_ok = cache.ok & all_urls if recheck_all else {
        u for u in cache.ok if u in all_urls
        and cache._checked_at.get(u, "0000-00-00") < cutoff
    }
    to_check = (all_urls - cache.broken - cache.ok) | stale_ok
    print(f"URLs: {len(all_urls)} total | {len(cache.broken)} broken | {len(to_check)} to check")

    newly_broken = []
    for i, url in enumerate(sorted(to_check), 1):
        print(f"  [{i}/{len(to_check)}] {url[:75]}", end=" ... ", flush=True)
        if is_dead_url(url):
            print("QUEBRADO")
            cache.mark_broken(url)
            newly_broken.append(url)
        else:
            print("ok")
            cache.mark_ok(url, today_str)
        time.sleep(0.3)

    cache.prune_stale(all_urls)
    cache.save()
    print(f"\nResultado: {len(newly_broken)} novos quebrados")
    for u in newly_broken:
        print("  QUEBRADO:", u)

if __name__ == "__main__":
    main()
