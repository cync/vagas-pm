#!/usr/bin/env python3
"""
deploy.py — Pipeline completo de deploy do site vagas-pm.

Etapas:
  1. Sincroniza arquivos MD da pasta raiz (VagasInternacionais/) para site/vagas/
  2. Gera o site (generate_site.py)
  3. Envia push notification (notify.py)
  4. Commit + push para o GitHub com tratamento automático de conflitos

Uso:
  python deploy.py                  # executa tudo
  python deploy.py --skip-notify    # pula notificação
  python deploy.py --skip-git       # pula commit/push (útil para testes)
"""

import sys, re, shutil, subprocess
from datetime import date
from pathlib import Path

SITE_DIR  = Path(__file__).parent.resolve()
ROOT_DIR  = SITE_DIR.parent          # VagasInternacionais/
VAGAS_DIR = SITE_DIR / "vagas"

SKIP_NOTIFY = "--skip-notify" in sys.argv
SKIP_GIT    = "--skip-git"    in sys.argv


def log(msg):
    print(f"[deploy] {msg}", flush=True)


# ── 1. Sincroniza MD files da pasta raiz → site/vagas/ ──────────────────────

def sync_md_files():
    synced = []
    for pattern in ("vagas_pm_*.md", "vagas_uiux_*.md"):
        for src in sorted(ROOT_DIR.glob(pattern)):
            dst = VAGAS_DIR / src.name
            if not dst.exists():
                shutil.copy2(src, dst)
                synced.append(src.name)
                log(f"  Sincronizado: {src.name}")
    if not synced:
        log("  Nenhum arquivo novo para sincronizar.")
    return synced


# ── 2. Gera o site ───────────────────────────────────────────────────────────

def generate_site():
    log("Gerando site...")
    result = subprocess.run(
        [sys.executable, str(SITE_DIR / "generate_site.py")],
        cwd=SITE_DIR, capture_output=True, text=True
    )
    print(result.stdout, end="")
    if result.returncode != 0:
        print(result.stderr, end="")
        log("ERRO: generate_site.py falhou.")
        sys.exit(1)


# ── 3. Lê contagem e empresas do último arquivo PM ───────────────────────────

def read_latest_run():
    pm_files = sorted(VAGAS_DIR.glob("vagas_pm_*.md"), key=lambda f: f.name)
    if not pm_files:
        return 0, ""
    text = pm_files[-1].read_text(encoding="utf-8", errors="replace")
    m = re.search(r'[Nn]ovas[^\d]*(\d+)', text)
    count = int(m.group(1)) if m else 0
    # Extrai empresas da seção de novas vagas (antes de "Já Vistas")
    novas_section = re.split(
        r'##\s+.*(?:Já Vistas|Already|ignoradas)', text, flags=re.IGNORECASE
    )[0]
    companies = re.findall(r'\|\s*([^|*\[\]#<>\n]+?)\s*\|', novas_section)
    seen, unique = set(), []
    for c in companies:
        c = c.strip()
        if c and c not in ("Empresa", "Company", "---", "") and c not in seen:
            seen.add(c)
            unique.append(c)
    return count, ", ".join(unique[:5])


# ── 4. Envia push notification ───────────────────────────────────────────────

def send_notification(count, companies):
    if count == 0:
        log("Nenhuma vaga nova — notificação ignorada.")
        return
    log(f"Enviando notificação: {count} vagas ({companies})...")
    result = subprocess.run(
        [sys.executable, str(SITE_DIR / "notify.py"), str(count), companies],
        cwd=SITE_DIR, capture_output=True, text=True
    )
    print(result.stdout, end="")
    if result.returncode != 0:
        log(f"notify.py aviso: {result.stderr.strip()}")


# ── 5. Git: pull → add → commit → push ──────────────────────────────────────

def git(*args, check=False):
    r = subprocess.run(
        ["git"] + list(args),
        cwd=SITE_DIR, capture_output=True, text=True
    )
    if check and r.returncode != 0:
        log(f"git {' '.join(args)} falhou:\n{r.stderr.strip()}")
    return r


def git_deploy():
    log("Sincronizando com remote (pull --rebase --autostash)...")
    pull = git("pull", "--rebase", "--autostash")
    if pull.returncode != 0:
        log(f"ERRO no pull --rebase:\n{pull.stderr.strip()}")
        sys.exit(1)

    log("Staged changes...")
    git("add", "-A")

    today = date.today().isoformat()
    commit = git("commit", "-m", f"auto: vagas PM {today}")
    if "nothing to commit" in (commit.stdout + commit.stderr):
        log("Nada novo para commitar.")
        return

    log("Fazendo push...")
    push = git("push")
    if push.returncode == 0:
        log("Push OK.")
    else:
        log(f"ERRO no push: {push.stderr.strip()}")
        sys.exit(1)


# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    log("=== deploy.py iniciado ===")

    log("1/4  Sincronizando arquivos MD...")
    sync_md_files()

    log("2/4  Gerando site...")
    generate_site()

    count, companies = read_latest_run()

    if not SKIP_NOTIFY:
        log("3/4  Notificação...")
        send_notification(count, companies)
    else:
        log("3/4  Notificação ignorada (--skip-notify).")

    if not SKIP_GIT:
        log("4/4  Git deploy...")
        git_deploy()
    else:
        log("4/4  Git ignorado (--skip-git).")

    log("=== Deploy concluído ===")
