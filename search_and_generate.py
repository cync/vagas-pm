#!/usr/bin/env python3
"""
Pipeline autônomo: busca vagas PM direto em ATS públicos + filtra localmente + gera site.
"""
import html, os, json, re, sys
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone, timedelta
from pathlib import Path

from link_checker import (
    BrokenCache, check_urls_parallel, is_dead_url, is_specific_job_url,
    normalize_url,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ── Configurações ────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = ""

SCRIPT_DIR   = Path(__file__).parent
VAGAS_DIR    = SCRIPT_DIR / "vagas"
HISTORY_FILE = VAGAS_DIR / "url_history.json"
BROKEN_FILE  = SCRIPT_DIR / "broken_links.json"
SOURCES_FILE = SCRIPT_DIR / "direct_sources.json"
BRT = timezone(timedelta(hours=-3))

TODAY = datetime.now(BRT).date().isoformat()

# ── Histórico ─────────────────────────────────────────────────────────────────
def load_history() -> set:
    history = set()
    if HISTORY_FILE.exists():
        history |= set(json.loads(HISTORY_FILE.read_text(encoding="utf-8")))
    url_re = re.compile(r'\[(?:Ver vaga|Aplicar|Apply|Verificar|Ver)\]\((https?://[^)]+)\)')
    for md_file in VAGAS_DIR.glob("vagas_*.md"):
        try:
            text = md_file.read_text(encoding="utf-8", errors="replace")
            history.update(normalize_url(u) for u in url_re.findall(text))
        except Exception:
            pass
    return history

def save_history(history: set):
    HISTORY_FILE.write_text(
        json.dumps(sorted(history), indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

# ── Validação de links ─────────────────────────────────────────────────────────
def filter_live_vagas(vagas: list[dict]) -> list[dict]:
    """Remove vagas with dead/expired links (parallel check)."""
    from datetime import date as _date
    cache = BrokenCache(BROKEN_FILE)
    today_str = _date.today().isoformat()

    to_check = [v for v in vagas if normalize_url(v.get("url", "")) not in cache.broken]

    if not to_check:
        return []

    print(f"  🔍 Validando {len(to_check)} links novos...", flush=True)
    urls_to_check = [normalize_url(v["url"]) for v in to_check if v.get("url")]
    results = check_urls_parallel(urls_to_check)

    live = []
    newly_broken = set()
    newly_alive = set()
    for v in to_check:
        nurl = normalize_url(v["url"])
        if results.get(nurl, False):
            newly_broken.add(nurl)
            print(f"    💀 {v.get('company','?')} — {nurl}", flush=True)
        else:
            live.append(v)
            newly_alive.add(nurl)

    if newly_broken:
        cache.add_broken_batch(newly_broken)
    if newly_alive:
        cache.add_ok_batch(newly_alive, today_str)
    cache.save()

    if newly_broken:
        print(f"  ✅ {len(live)} links vivos | 💀 {len(newly_broken)} removidos", flush=True)
    else:
        print(f"  ✅ Todos os {len(live)} links válidos", flush=True)

    return live

# ── Buscas ────────────────────────────────────────────────────────────────────
HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 vagas-pm-bot/2.0 (+https://cync.github.io/vagas-pm/)",
    "Accept": "application/json,text/html;q=0.8,*/*;q=0.5",
}

REMOTE_RE = re.compile(
    r"\b(remote|remoto|anywhere|worldwide|global|distributed|work from anywhere|wfa)\b",
    re.I,
)
REGION_RE = re.compile(
    r"\b(latam|latin america|brazil|brasil|south america|argentina|colombia|mexico|"
    r"peru|chile|portugal|emea|europe|european|apac|worldwide|global|anywhere)\b",
    re.I,
)
US_ONLY_RE = re.compile(
    r"\b(us only|u\.s\. only|united states only|usa only|must be based in the united states)\b",
    re.I,
)

def _strip_html(value: str) -> str:
    value = re.sub(r"<(script|style).*?</\1>", " ", value or "", flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()

def _get_json(url: str) -> dict | list:
    req = urllib.request.Request(url, headers=HTTP_HEADERS)
    with urllib.request.urlopen(req, timeout=25) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    return json.loads(raw)

def load_sources() -> list[dict]:
    if not SOURCES_FILE.exists():
        return []
    data = json.loads(SOURCES_FILE.read_text(encoding="utf-8"))
    return [s for s in data if s.get("ats") and (s.get("board") or s.get("category"))]

def _job(company: str, role: str, url: str, ats: str, content: str = "", location: str = "") -> dict:
    text = " ".join(p for p in [role, location, content] if p)
    return {
        "title": role,
        "company": company,
        "role": role,
        "url": normalize_url(url),
        "ats": ats,
        "content": _strip_html(text),
    }

def _accept_direct_job(job: dict) -> bool:
    text = f"{job.get('title','')} {job.get('content','')}"
    if not PM_KEYWORDS.search(text):
        return False
    if EXCLUDE_KEYWORDS.search(job.get("title", "")):
        return False
    if US_ONLY_RE.search(text):
        return False
    return bool(REMOTE_RE.search(text) or REGION_RE.search(text))

def _fetch_greenhouse(source: dict) -> list[dict]:
    board = source["board"]
    url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true"
    data = _get_json(url)
    jobs = []
    for item in data.get("jobs", []):
        location = (item.get("location") or {}).get("name", "")
        absolute_url = item.get("absolute_url") or f"https://boards.greenhouse.io/{board}/jobs/{item.get('id')}"
        jobs.append(_job(
            source.get("company") or board,
            item.get("title", ""),
            absolute_url,
            "Greenhouse",
            item.get("content", ""),
            location,
        ))
    return jobs

def _fetch_lever(source: dict) -> list[dict]:
    board = source["board"]
    url = f"https://api.lever.co/v0/postings/{board}?mode=json"
    data = _get_json(url)
    jobs = []
    for item in data if isinstance(data, list) else []:
        categories = item.get("categories") or {}
        location = " ".join(str(v) for v in categories.values() if v)
        content = " ".join(
            _strip_html(section.get("content", ""))
            for section in item.get("lists", [])
            if isinstance(section, dict)
        )
        jobs.append(_job(
            source.get("company") or board,
            item.get("text", ""),
            item.get("hostedUrl") or item.get("applyUrl") or "",
            "Lever",
            content,
            location,
        ))
    return jobs

def _fetch_ashby(source: dict) -> list[dict]:
    board = urllib.parse.quote(source["board"], safe="")
    url = f"https://api.ashbyhq.com/posting-api/job-board/{board}?ashby_source=job_board&limit=500"
    data = _get_json(url)
    jobs = []
    for item in data.get("jobs", []):
        location = item.get("locationName") or item.get("location", "")
        jobs.append(_job(
            source.get("company") or source["board"],
            item.get("title", ""),
            item.get("jobUrl") or item.get("hostedUrl") or f"https://jobs.ashbyhq.com/{source['board']}/{item.get('id')}",
            "Ashby",
            item.get("descriptionHtml") or item.get("descriptionPlain") or "",
            location,
        ))
    return jobs

def _fetch_remotive(source: dict) -> list[dict]:
    category = source.get("category", "")
    url = "https://remotive.com/api/remote-jobs"
    if category:
        url += f"?category={urllib.parse.quote(category)}"
    data = _get_json(url)
    jobs = []
    for item in data.get("jobs", []):
        jobs.append(_job(
            item.get("company_name") or "Remotive",
            item.get("title", ""),
            item.get("url", ""),
            "Remotive",
            item.get("description", ""),
            item.get("candidate_required_location", ""),
        ))
    return jobs

FETCHERS = {
    "greenhouse": _fetch_greenhouse,
    "lever": _fetch_lever,
    "ashby": _fetch_ashby,
    "remotive": _fetch_remotive,
}

def _fetch_source(source: dict) -> tuple[dict, list[dict], str | None]:
    fetcher = FETCHERS.get(source.get("ats", "").lower())
    if not fetcher:
        return source, [], f"ATS sem fetcher: {source.get('ats')}"
    try:
        jobs = [j for j in fetcher(source) if j.get("url") and _accept_direct_job(j)]
        return source, jobs, None
    except Exception as e:
        return source, [], f"{type(e).__name__}: {e}"

def search_all() -> list[dict] | None:
    sources = load_sources()
    if not sources:
        print("  direct_sources.json vazio ou ausente; mantendo site existente.", flush=True)
        return None

    results: list[dict] = []
    failures = 0
    with ThreadPoolExecutor(max_workers=min(8, len(sources))) as pool:
        futures = {pool.submit(_fetch_source, s): s for s in sources}
        for future in as_completed(futures):
            source, jobs, error = future.result()
            label = source.get("company") or source.get("board") or source.get("category")
            if error:
                failures += 1
                print(f"  ERRO [{source.get('ats')}:{label}] {error}", flush=True)
                continue
            results.extend(jobs)
            print(f"  [{source.get('ats')}:{label}] {len(jobs)} vagas candidatas", flush=True)

    if failures == len(sources):
        print("  Todas as fontes diretas falharam; mantendo site existente.", flush=True)
        return None
    return results

# ── Detecção ATS pela URL ──────────────────────────────────────────────────────
def detect_ats(url: str) -> str:
    if "lever.co"            in url: return "Lever"
    if "ashbyhq.com"         in url: return "Ashby"
    if "greenhouse.io"       in url: return "Greenhouse"
    if "smartrecruiters.com" in url: return "SmartRecruiters"
    if "weworkremotely.com"  in url: return "WWR"
    if "remotive.com"        in url: return "Remotive"
    if "himalayas.app"       in url: return "Himalayas"
    if "workable.com"        in url: return "Workable"
    return "Outro"

# ── Extração com Claude (opcional) ───────────────────────────────────────────
EXTRACT_PROMPT = """Você vai receber resultados de busca de vagas de emprego (título + URL + snippet).

Para CADA resultado, determine se é uma vaga de **Product Manager** remota que aceita candidatos do Brasil/LATAM.

Retorne um JSON array. Cada item deve ter:
- "company": nome da empresa
- "role": título do cargo
- "url": URL exata da vaga
- "ats": plataforma ATS (Lever / Ashby / Greenhouse / SmartRecruiters / WWR / Remotive / Himalayas / Workable / Outro)
- "latam_friendly": true se menciona LATAM, Brazil, remote-anywhere, ou não restringe a US/EU

Inclua SOMENTE vagas de PM (Product Manager, Product Owner, Head of Product). Exclua engineering, design, marketing, etc.
Se não houver vagas válidas, retorne [].

Resultados de busca:
"""

def extract_with_claude(raw_results: list[dict]) -> list[dict] | None:
    """Tenta extrair via Claude API. Retorna None se indisponível."""
    if not ANTHROPIC_API_KEY:
        return None
    try:
        from anthropic import Anthropic
        claude = Anthropic(api_key=ANTHROPIC_API_KEY)

        context_lines = []
        for r in raw_results:
            context_lines.append(f"Título: {r.get('title', '')}")
            context_lines.append(f"URL: {r.get('url', '')}")
            context_lines.append(f"Snippet: {r.get('content', '')[:300]}")
            context_lines.append("---")
        context = "\n".join(context_lines)

        msg = claude.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": EXTRACT_PROMPT + context + "\n\nRetorne apenas o JSON array, sem explicações."
            }]
        )
        text = msg.content[0].text.strip()
        text = re.sub(r'^```(?:json)?\n?', '', text)
        text = re.sub(r'\n?```$', '', text)
        return json.loads(text)

    except Exception as e:
        print(f"  ⚠️  Claude indisponível ({type(e).__name__}): {e}", flush=True)
        return None

# ── Extração por regex (fallback) ─────────────────────────────────────────────
PM_KEYWORDS = re.compile(
    r'\bproduct\s+manager\b|\bproduct\s+owner\b|\bhead\s+of\s+product\b|'
    r'\bsenior\s+pm\b|\bprincipal\s+pm\b|\bgroup\s+pm\b|\bstaff\s+pm\b',
    re.IGNORECASE
)
EXCLUDE_KEYWORDS = re.compile(
    r'\bengineer\b|\bdeveloper\b|\bdesigner\b|\bmarketing\b|\bsales\b|'
    r'\bdata\s+scientist\b|\banalyst\b|\baccountant\b|\brecruiter\b',
    re.IGNORECASE
)

def extract_company_from_title(title: str, url: str) -> str:
    """Tenta extrair nome da empresa do título ou domínio."""
    for sep in [" – ", " - ", " | ", " at "]:
        if sep in title:
            parts = title.split(sep)
            for i, part in enumerate(parts):
                if PM_KEYWORDS.search(part):
                    other = parts[1-i] if len(parts) == 2 else parts[-1]
                    return other.strip()
    domain = re.search(r'(?:jobs\.|boards\.|job-boards\.)([^./]+)', url)
    if domain:
        return domain.group(1).replace("-", " ").title()
    return "?"

def extract_with_regex(raw_results: list[dict]) -> list[dict]:
    """Extração heurística sem LLM."""
    vagas = []
    for r in raw_results:
        title   = r.get("title", "")
        url     = r.get("url", "")
        content = r.get("content", "")
        full_text = f"{title} {content}"

        if not PM_KEYWORDS.search(full_text):
            continue
        if EXCLUDE_KEYWORDS.search(title):
            continue

        if not is_specific_job_url(url):
            print(f"    ⏭️  URL não é vaga específica: {url[:80]}", flush=True)
            continue

        company = r.get("company") or extract_company_from_title(title, url)
        ats     = r.get("ats") or detect_ats(url)

        role = r.get("role") or title
        for sep in [" – ", " - ", " | ", " at "]:
            if sep in title:
                parts = title.split(sep)
                for part in parts:
                    if PM_KEYWORDS.search(part):
                        role = part.strip()
                        break
                break

        vagas.append({
            "company": company,
            "role":    role,
            "url":     url,
            "ats":     ats,
            "latam_friendly": bool(re.search(r'LATAM|Brazil|Brasil|remote.anywhere|anywhere', full_text, re.I)),
        })
    return vagas

def extract_vagas(raw_results: list[dict]) -> list[dict]:
    result = extract_with_regex(raw_results)
    print(f"  ✅ Filtro local manteve {len(result)} vagas", flush=True)
    return result

# ── Markdown ──────────────────────────────────────────────────────────────────
ATS_EMOJI = {
    "Lever": "🔷", "Ashby": "🔶", "Greenhouse": "🟢",
    "SmartRecruiters": "🔴", "WWR": "🟡",
    "Remotive": "⚪", "Himalayas": "⚪", "Workable": "⚫", "Outro": "⚫",
}
ATS_LABEL = {
    "Ashby": "Ashby HQ", "WWR": "We Work Remotely",
}

def group_by_ats(vagas):
    groups = {}
    for v in vagas:
        ats = v.get("ats", "Outro")
        if "Ashby" in ats: ats = "Ashby"
        elif "Greenhouse" in ats: ats = "Greenhouse"
        elif "Smart" in ats: ats = "SmartRecruiters"
        elif "WeWork" in ats or "We Work" in ats or ats == "WWR": ats = "WWR"
        elif "Workable" in ats: ats = "Workable"
        groups.setdefault(ats, []).append(v)
    return groups

def generate_markdown(vagas, prev_count) -> str:
    months_pt = ["janeiro","fevereiro","março","abril","maio","junho",
                 "julho","agosto","setembro","outubro","novembro","dezembro"]
    d = date.today()
    now = f"{d.day} de {months_pt[d.month-1]} de {d.year}"

    total  = prev_count + len(vagas)
    groups = group_by_ats(vagas)

    lines = [
        f"# 🆕 Vagas PM Internacionais – {now}",
        "",
        f"> **Execução automática** | Busca em ATS internacionais (Lever, Ashby, Greenhouse, SmartRecruiters, WWR, Remotive, Workable)",
        f"> **Histórico:** {prev_count} vagas anteriores ignoradas | **Novas encontradas:** {len(vagas)}",
        "",
        "---",
        "",
        "## ✅ NOVAS VAGAS (não encontradas em execuções anteriores)",
        "",
    ]

    if not vagas:
        lines.append("*Nenhuma vaga nova encontrada nesta execução.*")
    else:
        ATS_ORDER = ["Lever", "Ashby", "Greenhouse", "SmartRecruiters", "WWR", "Remotive", "Himalayas", "Workable", "Outro"]
        for ats in ATS_ORDER:
            bucket = groups.get(ats, [])
            if not bucket:
                continue
            emoji = ATS_EMOJI.get(ats, "⚫")
            label = ATS_LABEL.get(ats, ats)
            lines += [
                f"### {emoji} {label}",
                "",
                "| Empresa | Cargo | Link |",
                "|---------|-------|------|",
            ]
            for v in bucket:
                company = v.get("company", "?").replace("|", "\\|")
                role    = v.get("role",    "?").replace("|", "\\|")
                url     = v.get("url",     "#")
                lines.append(f"| **{company}** | {role} | [Ver vaga]({url}) |")
            lines.append("")

    lines += [
        "---",
        "",
        "## 📊 Resumo desta execução",
        "",
        f"- **Data:** {TODAY}",
        f"- **Vagas no histórico (anteriores):** {prev_count}",
        f"- **Novas vagas encontradas:** {len(vagas)}",
        f"- **Total acumulado:** {total}",
        "",
        "---",
        "",
        "*Gerado automaticamente via busca em ATS internacionais*",
    ]

    return "\n".join(lines) + "\n"


# ── Main ──────────────────────────────────────────────────────────────────────
def _revalidate_historical_urls():
    """Spot-check a sample of historical URLs from existing .md files."""
    if os.environ.get("REVALIDATE_HISTORICAL_LINKS", "").lower() not in {"1", "true", "yes"}:
        return
    import random as _random

    url_re = re.compile(r'\[(?:Ver vaga|Aplicar|Apply)\]\((https?://[^)]+)\)')
    all_urls: set = set()
    for md_file in sorted(VAGAS_DIR.glob("vagas_*.md")):
        try:
            text = md_file.read_text(encoding="utf-8", errors="replace")
            all_urls.update(url_re.findall(text))
        except Exception:
            pass

    cache = BrokenCache(BROKEN_FILE)
    candidates = [u for u in all_urls if u not in cache.broken]
    if not candidates:
        return

    sample = _random.sample(candidates, min(30, len(candidates)))
    print(f"  🔁 Re-validando {len(sample)} URLs históricas...", flush=True)

    results = check_urls_parallel(sample)
    newly_broken = {u for u, dead in results.items() if dead}

    if newly_broken:
        for u in newly_broken:
            print(f"    💀 Histórico morto: {u[:80]}", flush=True)
        cache.add_broken_batch(newly_broken)
        cache.save()
        print(f"  ✅ {len(newly_broken)} links históricos mortos adicionados ao cache", flush=True)
    else:
        print(f"  ✅ Todos os {len(sample)} links históricos válidos", flush=True)


def main():
    VAGAS_DIR.mkdir(parents=True, exist_ok=True)

    history = load_history()
    prev_count = len(history)

    print(f"📂 Histórico: {prev_count} URLs conhecidas", flush=True)

    print("🔍 Buscando vagas...", flush=True)
    raw = search_all()
    if raw is None:
        print("🌐 Regenerando site sem criar nova execucao...", flush=True)
        import subprocess
        result = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "generate_site.py")],
            capture_output=True, text=True
        )
        if result.stdout:
            print(result.stdout, flush=True)
        if result.returncode != 0:
            print(f"⚠️  generate_site.py retornou código {result.returncode}", flush=True)
            if result.stderr:
                print(result.stderr, flush=True)
            return result.returncode
        print("✅ Concluído — busca indisponivel, site existente regenerado", flush=True)
        return 0

    _revalidate_historical_urls()
    print(f"📋 {len(raw)} resultados brutos obtidos", flush=True)

    print("🤖 Extraindo vagas estruturadas...", flush=True)
    all_vagas = extract_vagas(raw)

    normalized_vagas = []
    for v in all_vagas:
        url = normalize_url(v.get("url", ""))
        if not url:
            continue
        if not is_specific_job_url(url):
            print(f"    ⏭️  URL não é vaga específica: {url[:100]}", flush=True)
            continue
        v["url"] = url
        normalized_vagas.append(v)

    normalized_history = {normalize_url(u) for u in history}
    new_vagas = [v for v in normalized_vagas if v["url"] not in normalized_history]
    seen_urls: set = set()
    deduped: list = []
    for v in new_vagas:
        if v["url"] not in seen_urls:
            seen_urls.add(v["url"])
            deduped.append(v)
    new_vagas = deduped

    print(f"🆕 {len(new_vagas)} vagas novas (após deduplicação)", flush=True)

    if new_vagas:
        print("🔗 Validando links...", flush=True)
        new_vagas = filter_live_vagas(new_vagas)
        print(f"🆕 {len(new_vagas)} vagas novas com links válidos", flush=True)

    if not new_vagas:
        save_history(history)
        print(f"📚 Histórico atualizado: {len(history)} URLs", flush=True)
        print("🌐 Regenerando site sem criar execucao vazia...", flush=True)
        import subprocess
        result = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "generate_site.py")],
            capture_output=True, text=True
        )
        if result.stdout:
            print(result.stdout, flush=True)
        if result.returncode != 0:
            print(f"⚠️  generate_site.py retornou código {result.returncode}", flush=True)
            if result.stderr:
                print(result.stderr, flush=True)
            return result.returncode
        print("✅ Concluído — nenhuma vaga nova encontrada", flush=True)
        return 0

    base = VAGAS_DIR / f"vagas_pm_{TODAY}.md"
    if base.exists():
        n = 2
        while (VAGAS_DIR / f"vagas_pm_{TODAY}_exec{n}.md").exists():
            n += 1
        out_path = VAGAS_DIR / f"vagas_pm_{TODAY}_exec{n}.md"
    else:
        out_path = base

    md = generate_markdown(new_vagas, prev_count)
    out_path.write_text(md, encoding="utf-8")
    print(f"💾 Salvo: {out_path.name}", flush=True)

    new_urls = {v["url"] for v in new_vagas if v.get("url")}
    history |= new_urls
    save_history(history)
    print(f"📚 Histórico atualizado: {len(history)} URLs", flush=True)

    print("🌐 Regenerando site...", flush=True)
    import subprocess
    result = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "generate_site.py")],
        capture_output=True, text=True
    )
    if result.stdout:
        print(result.stdout, flush=True)
    if result.returncode != 0:
        print(f"⚠️  generate_site.py retornou código {result.returncode}", flush=True)
        if result.stderr:
            print(result.stderr, flush=True)

    print(f"✅ Concluído — {len(new_vagas)} novas vagas encontradas", flush=True)


if __name__ == "__main__":
    raise SystemExit(main() or 0)
