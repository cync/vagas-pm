#!/usr/bin/env python3
"""
Pipeline autônomo: busca vagas PM via Tavily + extrai com Claude API + gera site.
Roda no GitHub Actions 2x ao dia (sem precisar do computador ligado).
"""
import os, json, re, sys
from datetime import date, datetime
from pathlib import Path

from tavily import TavilyClient
from anthropic import Anthropic

# ── Configurações ────────────────────────────────────────────────────────────
TAVILY_API_KEY   = os.environ["TAVILY_API_KEY"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

SCRIPT_DIR  = Path(__file__).parent
VAGAS_DIR   = SCRIPT_DIR / "vagas"
HISTORY_FILE = VAGAS_DIR / "url_history.json"

TODAY = date.today().isoformat()

# ── Clientes ─────────────────────────────────────────────────────────────────
tavily  = TavilyClient(api_key=TAVILY_API_KEY)
claude  = Anthropic(api_key=ANTHROPIC_API_KEY)

# ── Histórico de URLs já encontradas ─────────────────────────────────────────
def load_history() -> set:
    if HISTORY_FILE.exists():
        return set(json.loads(HISTORY_FILE.read_text(encoding="utf-8")))
    return set()

def save_history(history: set):
    HISTORY_FILE.write_text(
        json.dumps(sorted(history), indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

# ── Buscas Tavily ─────────────────────────────────────────────────────────────
SEARCHES = [
    # (query, include_domains, max_results)
    ("product manager remote LATAM Brazil", ["jobs.lever.co"], 15),
    ("product manager remote LATAM Brazil", ["jobs.ashbyhq.com"], 15),
    ("product manager remote LATAM Brazil", ["boards.greenhouse.io", "job-boards.greenhouse.io"], 15),
    ("product manager remote LATAM", ["jobs.smartrecruiters.com"], 10),
    ("product manager remote LATAM Brazil", ["weworkremotely.com"], 10),
    ("product manager remote LATAM", ["remotive.com", "himalayas.app"], 10),
]

def search_all() -> list[dict]:
    """Executa todas as buscas e retorna lista de resultados brutos."""
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
                h["_source_domains"] = domains
            results.extend(hits)
            print(f"  [{domains[0]}] {len(hits)} resultados", flush=True)
        except Exception as e:
            print(f"  ERRO [{domains}]: {e}", flush=True)
    return results

# ── Extração via Claude ───────────────────────────────────────────────────────
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

def extract_vagas(raw_results: list[dict]) -> list[dict]:
    """Usa Claude Haiku para extrair vagas estruturadas dos resultados brutos."""
    if not raw_results:
        return []
    
    # Formata contexto para o modelo
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
    # Remove markdown code fences se presentes
    text = re.sub(r'^```(?:json)?\n?', '', text)
    text = re.sub(r'\n?```$', '', text)
    
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        print(f"  ERRO ao parsear JSON do Claude: {e}\n  Resposta: {text[:200]}", flush=True)
        return []

# ── Geração do Markdown ───────────────────────────────────────────────────────
ATS_EMOJI = {
    "Lever": "🔷",
    "Ashby": "🔶",
    "Greenhouse": "🟢",
    "SmartRecruiters": "🔴",
    "WWR": "🟡",
    "Remotive": "⚪",
    "Himalayas": "⚪",
    "Outro": "⚫",
}

def group_by_ats(vagas: list[dict]) -> dict:
    groups = {}
    for v in vagas:
        ats = v.get("ats", "Outro")
        # Normaliza variações
        if "Ashby" in ats:
            ats = "Ashby"
        elif "Greenhouse" in ats:
            ats = "Greenhouse"
        elif "SmartRecruiters" in ats or "Smart" in ats:
            ats = "SmartRecruiters"
        elif "WWR" in ats or "WeWork" in ats or "We Work" in ats:
            ats = "WWR"
        groups.setdefault(ats, []).append(v)
    return groups

def generate_markdown(vagas: list[dict], prev_count: int) -> str:
    now = datetime.now().strftime("%d de %B de %Y").lower()
    # Fix first letter capitalization
    now = now[0].upper() + now[1:]
    
    total = prev_count + len(vagas)
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
        ats_label = "Ashby HQ" if ats == "Ashby" else ("We Work Remotely" if ats == "WWR" else ats)
        lines.append(f"### {emoji} {ats_label}")
        lines.append("")
        lines.append("| Empresa | Cargo | Link |")
        lines.append("|---------|-------|------|")
        for v in items:
            company = v.get("company", "?")
            role = v.get("role", "?")
            url = v.get("url", "#")
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
        "",
    ]
    
    return "\n".join(lines)

# ── Geração dos destaques via Claude ─────────────────────────────────────────
def generate_highlights(vagas: list[dict]) -> str:
    if not vagas:
        return ""
    
    vagas_text = "\n".join([
        f"- {v.get('company')} | {v.get('role')} | {v.get('url')}"
        for v in vagas
    ])
    
    msg = claude.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1500,
        messages=[{
            "role": "user",
            "content": f"""Você é um especialista em Product Management internacional.
Abaixo estão vagas encontradas hoje. Selecione as 5-10 mais relevantes para um PM sênior brasileiro
buscando trabalho remoto internacional bem remunerado. Para cada uma, escreva 1 linha explicando
por que é relevante (empresa, produto, escopo). Use numeração 1. 2. 3. etc.
Formato exato:
1. **Empresa – Cargo** → [motivo em ~15 palavras]

Vagas:
{vagas_text}"""
        }]
    )
    
    highlights = msg.content[0].text.strip()
    return f"\n## 🔍 Destaques desta execução\n\nAs vagas mais relevantes para perfil sênior internacional / remote-first:\n\n{highlights}\n\n---\n\n"

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print(f"🔍 Iniciando busca de vagas PM — {TODAY}", flush=True)
    VAGAS_DIR.mkdir(exist_ok=True)
    
    history = load_history()
    prev_count = len(history)
    print(f"📚 Histórico: {prev_count} URLs conhecidas", flush=True)
    
    # 1. Buscar
    print("\n🌐 Buscando nos ATS...", flush=True)
    raw = search_all()
    print(f"  Total bruto: {len(raw)} resultados", flush=True)
    
    # 2. Extrair
    print("\n🤖 Extraindo vagas com Claude...", flush=True)
    all_vagas = extract_vagas(raw)
    print(f"  Extraídas: {len(all_vagas)} vagas de PM", flush=True)
    
    # 3. Filtrar duplicatas
    new_vagas = [v for v in all_vagas if v.get("url") not in history]
    print(f"  Novas (não no histórico): {len(new_vagas)}", flush=True)
    
    if not new_vagas:
        print("✅ Nenhuma vaga nova encontrada.", flush=True)
        # Ainda regenera o site para manter atualizado
    else:
        # 4. Gerar highlights
        print("\n✨ Gerando destaques...", flush=True)
        highlights = generate_highlights(new_vagas)
        
        # 5. Salvar markdown
        md_filename = VAGAS_DIR / f"vagas_pm_{TODAY}.md"
        # Checar se já existe (exec2)
        if md_filename.exists():
            md_filename = VAGAS_DIR / f"vagas_pm_{TODAY}_exec2.md"
        
        md_content = generate_markdown(new_vagas, prev_count)
        # Inserir highlights antes do último ---
        md_content = md_content.rstrip("\n") + "\n" + highlights + "*Gerado automaticamente via busca em ATS internacionais*\n"
        
        md_filename.write_text(md_content, encoding="utf-8")
        print(f"\n💾 Salvo: {md_filename.name}", flush=True)
        
        # 6. Atualizar histórico
        new_urls = {v["url"] for v in new_vagas if v.get("url")}
        history.update(new_urls)
        save_history(history)
    
    # 7. Regenerar site
    print("\n🏗️  Regenerando site...", flush=True)
    generate_site_path = SCRIPT_DIR / "generate_site.py"
    if generate_site_path.exists():
        import subprocess
        result = subprocess.run(
            [sys.executable, str(generate_site_path)],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print("  ✅ Site regenerado com sucesso", flush=True)
        else:
            print(f"  ⚠️  Erro ao regenerar site: {result.stderr[:200]}", flush=True)
    
    print(f"\n✅ Pipeline concluído — {len(new_vagas)} novas vagas adicionadas.", flush=True)

if __name__ == "__main__":
    main()
