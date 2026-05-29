#!/usr/bin/env python3
"""
Pipeline autônomo: busca vagas PM via Tavily + extrai com Claude API (fallback: regex) + gera site.
"""
import os, json, re, sys
from datetime import date, datetime, timezone, timedelta
from pathlib import Path

from tavily import TavilyClient

# ── Configurações ────────────────────────────────────────────────────────────
TAVILY_API_KEY    = os.environ["TAVILY_API_KEY"]
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

SCRIPT_DIR   = Path(__file__).parent
VAGAS_DIR    = SCRIPT_DIR / "vagas"
HISTORY_FILE = VAGAS_DIR / "url_history.json"
BRT = timezone(timedelta(hours=-3))
TODAY = datetime.now(BRT).date().isoformat()

tavily = TavilyClient(api_key=TAVILY_API_KEY)

# ── Histórico ─────────────────────────────────────────────────────────────────
def load_history() -> set:
    if HISTORY_FILE.exists():
        return set(json.loads(HISTORY_FILE.read_text(encoding="utf-8")))
    return set()

def save_history(history: set):
    HISTORY_FILE.write_text(
        json.dumps(sorted(history), indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

# ── Buscas ────────────────────────────────────────────────────────────────────
SEARCHES = [
    ("product manager remote LATAM Brazil",   ["jobs.lever.co"],                                    15),
    ("product manager remote LATAM Brazil",   ["jobs.ashbyhq.com"],                                 15),
    ("product manager remote LATAM Brazil",   ["boards.greenhouse.io","job-boards.greenhouse.io"],  15),
    ("product manager remote LATAM",          ["jobs.smartrecruiters.com"],                         10),
    ("product manager remote LATAM Brazil",   ["weworkremotely.com"],                               10),
    ("product manager remote LATAM",          ["remotive.com","himalayas.app"],                     10),
]

def search_all() -> list[dict]:
    results = []
    for query, domains, n in SEARCHES:
        try:
            resp = tavily.search(
                query=query,
                include_domains=domains,
                max_results=n,
                search_depth="advanced",
            )
            hits = resp.get("results", [])
            for h in hits:
                h["_domains"] = domains
            results.extend(hits)
            print(f"  [{domains[0]}] {len(hits)} resultados", flush=True)
        except Exception as e:
            print(f"  ERRO [{domains[0]}]: {e}", flush=True)
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
    return "Outro"

# ── Extração com Claude (opcional) ───────────────────────────────────────────
EXTRACT_PROMPT = """Você vai receber resultados de busca de vagas de emprego (título + URL + snippet).

Para CADA resultado, determine se é uma vaga de **Product Manager** remota que aceita candidatos do Brasil/LATAM.

Retorne um JSON array. Cada item deve ter:
- "company": nome da empresa
- "role": título do cargo
- "url": URL exata da vaga
- "ats": plataforma ATS (Lever / Ashby / Greenhouse / SmartRecruiters / WWR / Remotive / Himalayas / Outro)
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
        from anthropic import Anthropic, BadRequestError, APIStatusError
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
    # Padrão "Empresa – Cargo" ou "Empresa | Cargo"
    for sep in [" – ", " - ", " | ", " at "]:
        if sep in title:
            parts = title.split(sep)
            # Geralmente cargo vem antes em sites como WWR, empresa depois
            # Testa qual parte parece cargo de PM
            for i, part in enumerate(parts):
                if PM_KEYWORDS.search(part):
                    other = parts[1-i] if len(parts) == 2 else parts[-1]
                    return other.strip()
    # Fallback: extrair do domínio
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

        # Filtro: deve mencionar PM e não ser cargo excluído
        if not PM_KEYWORDS.search(full_text):
            continue
        if EXCLUDE_KEYWORDS.search(title):
            continue

        company = extract_company_from_title(title, url)
        ats     = detect_ats(url)

        # Limpa o role: tenta pegar a parte do título que é o cargo
        role = title
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

# ── Extração (Claude se disponível, senão regex) ──────────────────────────────
def extract_vagas(raw_results: list[dict]) -> list[dict]:
    print("  Tentando Claude API...", flush=True)
    result = extract_with_claude(raw_results)
    if result is not None:
        print(f"  ✅ Claude extraiu {len(result)} vagas", flush=True)
        return result
    print("  🔄 Fallback: extração por regex", flush=True)
    result = extract_with_regex(raw_results)
    print(f"  ✅ Regex extraiu {len(result)} vagas", flush=True)
    return result

# ── Markdown ──────────────────────────────────────────────────────────────────
ATS_EMOJI = {
    "Lever": "🔷", "Ashby": "🔶", "Greenhouse": "🟢",
    "SmartRecruiters": "🔴", "WWR": "🟡",
    "Remotive": "⚪", "Himalayas": "⚪", "Outro": "⚫",
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
        f"> **Execução automática** | Busca em ATS internacionais (Lever, Ashby, Greenhouse, SmartRecruiters, WWR, Remotive)",
        f"> **Histórico:** {prev_count} vagas anteriores ignoradas | **Novas encontradas:** {len(vagas)}",
        "",
        "---",
        "",
        "## ✅ NOVAS VAGAS (não encontradas em execuções anteriores)",
        "",
    ]
    for ats, items in groups.items():
        emoji = ATS_EMOJI.get(ats, "⚫")
        label = ATS_LABEL.get(ats, ats)
        lines += [
            f"### {emoji} {label}", "",
            "| Empresa | Cargo | Link |",
            "|---------|-------|------|",
        ]
        for v in items:
            lines.append(f"| **{v.get('company','?')}** | {v.get('role','?')} | [Ver vaga]({v.get('url','#')}) |")
        lines.append("")

    lines += [
        "---", "",
        "## 📊 Resumo desta execução", "",
        f"- **Data:** {TODAY}",
        f"- **Vagas no histórico (anteriores):** {prev_count}",
        f"- **Novas vagas encontradas:** {len(vagas)}",
        f"- **Total acumulado:** {total}",
        "", "---", "",
        "*Gerado automaticamente via busca em ATS internacionais*", "",
    ]
    return "\n".join(lines)

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print(f"🔍 Iniciando busca de vagas PM — {TODAY}", flush=True)
    VAGAS_DIR.mkdir(exist_ok=True)

    history    = load_history()
    prev_count = len(history)
    print(f"📚 Histórico: {prev_count} URLs conhecidas", flush=True)

    print("\n🌐 Buscando nos ATS...", flush=True)
    raw = search_all()
    print(f"  Total bruto: {len(raw)} resultados", flush=True)

    print("\n🤖 Extraindo vagas...", flush=True)
    all_vagas = extract_vagas(raw)
    print(f"  Total extraído: {len(all_vagas)} vagas de PM", flush=True)

    new_vagas = [v for v in all_vagas if v.get("url") not in history]
    print(f"  Novas (não no histórico): {len(new_vagas)}", flush=True)

    if new_vagas:
        md_filename = VAGAS_DIR / f"vagas_pm_{TODAY}.md"
        if md_filename.exists():
            md_filename = VAGAS_DIR / f"vagas_pm_{TODAY}_exec2.md"

        md_filename.write_text(generate_markdown(new_vagas, prev_count), encoding="utf-8")
        print(f"\n💾 Salvo: {md_filename.name}", flush=True)

        history.update(v["url"] for v in new_vagas if v.get("url"))
        save_history(history)
    else:
        print("✅ Nenhuma vaga nova encontrada.", flush=True)

    print("\n🏗️  Regenerando site...", flush=True)
    gen = SCRIPT_DIR / "generate_site.py"
    if gen.exists():
        import subprocess
        r = subprocess.run([sys.executable, str(gen)], capture_output=True, text=True)
        if r.returncode == 0:
            print("  ✅ Site regenerado", flush=True)
        else:
            print(f"  ⚠️  Erro: {r.stderr[:300]}", flush=True)

    print(f"\n✅ Pipeline concluído — {len(new_vagas)} novas vagas adicionadas.", flush=True)

if __name__ == "__main__":
    main()
