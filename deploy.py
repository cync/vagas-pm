#!/usr/bin/env python3
"""
deploy.py - Pipeline completo de deploy do site vagas-pm.

Etapas:
  1. Sincroniza arquivos MD da pasta raiz (VagasInternacionais/) para site/vagas/
  2. Sincroniza o repositorio local com o remoto
  3. Gera o site (generate_site.py)
  4. Envia push notification (notify.py)
  5. Commit + push para o GitHub

Uso:
  python deploy.py                  # executa tudo
  python deploy.py --skip-notify    # pula notificacao
  python deploy.py --skip-git       # pula sync/commit/push
"""

import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

SITE_DIR = Path(__file__).parent.resolve()
ROOT_DIR = SITE_DIR.parent
VAGAS_DIR = SITE_DIR / "vagas"

SKIP_NOTIFY = "--skip-notify" in sys.argv
SKIP_GIT = "--skip-git" in sys.argv

TEXT_EXTENSIONS = {
    ".bat", ".css", ".html", ".js", ".json", ".md",
    ".py", ".txt", ".yaml", ".yml",
}


def log(msg):
    print(f"[deploy] {msg}", flush=True)


def fail(msg):
    log(f"ERRO: {msg}")
    sys.exit(1)


def git(*args, check=False):
    result = subprocess.run(
        ["git"] + list(args),
        cwd=SITE_DIR,
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
        log(f"git {' '.join(args)} falhou:\n{result.stderr.strip()}")
    return result


def _repo_text_files():
    for path in SITE_DIR.rglob("*"):
        if not path.is_file():
            continue
        if any(part in {".git", "__pycache__"} for part in path.parts):
            continue
        if path.suffix.lower() in TEXT_EXTENSIONS:
            yield path


def assert_no_conflict_markers(context):
    unmerged = git("diff", "--name-only", "--diff-filter=U")
    if unmerged.returncode == 0:
        conflicted = [line.strip() for line in unmerged.stdout.splitlines() if line.strip()]
        if conflicted:
            fail(f"conflitos Git pendentes {context}: {', '.join(conflicted)}")

    flagged = []
    pattern = re.compile(r"(?m)^(<<<<<<< |=======|>>>>>>> )")
    for path in _repo_text_files():
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if pattern.search(text):
            flagged.append(str(path.relative_to(SITE_DIR)))

    if flagged:
        fail(f"marcadores de conflito encontrados {context}: {', '.join(flagged)}")


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


def git_sync_remote():
    log("Sincronizando com remote (pull --rebase --autostash)...")
    pull = git("pull", "--rebase", "--autostash")
    if pull.returncode != 0:
        fail(f"pull --rebase falhou:\n{pull.stderr.strip()}")
    assert_no_conflict_markers("apos sincronizar com o remote")


def generate_site():
    log("Gerando site...")
    result = subprocess.run(
        [sys.executable, str(SITE_DIR / "generate_site.py")],
        cwd=SITE_DIR,
        capture_output=True,
        text=True,
    )
    print(result.stdout, end="")
    if result.returncode != 0:
        print(result.stderr, end="")
        fail("generate_site.py falhou.")
    assert_no_conflict_markers("apos gerar o site")


def read_latest_run():
    pm_files = sorted(VAGAS_DIR.glob("vagas_pm_*.md"), key=lambda f: f.name)
    if not pm_files:
        return 0, ""

    text = pm_files[-1].read_text(encoding="utf-8", errors="replace")
    count_match = re.search(r"[Nn]ovas[^\d]*(\d+)", text)
    count = int(count_match.group(1)) if count_match else 0

    novas_section = re.split(
        r"##\s+.*(?:Ja Vistas|J[aá] Vistas|Already|ignoradas)",
        text,
        flags=re.IGNORECASE,
    )[0]
    companies = re.findall(r"\|\s*([^|*\[\]#<>\n]+?)\s*\|", novas_section)

    seen, unique = set(), []
    for company in companies:
        company = company.strip()
        if company and company not in {"Empresa", "Company", "---"} and company not in seen:
            seen.add(company)
            unique.append(company)
    return count, ", ".join(unique[:5])


def send_notification(count, companies):
    if count == 0:
        log("Nenhuma vaga nova; notificacao ignorada.")
        return

    log(f"Enviando notificacao: {count} vagas ({companies})...")
    result = subprocess.run(
        [sys.executable, str(SITE_DIR / "notify.py"), str(count), companies],
        cwd=SITE_DIR,
        capture_output=True,
        text=True,
    )
    print(result.stdout, end="")
    if result.returncode != 0:
        log(f"notify.py aviso: {result.stderr.strip()}")


def git_deploy():
    assert_no_conflict_markers("antes do commit")

    log("Staged changes...")
    git("add", "-A")

    today = date.today().isoformat()
    commit = git("commit", "-m", f"auto: vagas PM {today}")
    if "nothing to commit" in (commit.stdout + commit.stderr):
        log("Nada novo para commitar.")
        return

    log("Fazendo push...")
    push = git("push")
    if push.returncode != 0:
        fail(f"push falhou:\n{push.stderr.strip()}")
    log("Push OK.")


if __name__ == "__main__":
    log("=== deploy.py iniciado ===")

    log("1/5  Sincronizando arquivos MD...")
    sync_md_files()

    if not SKIP_GIT:
        log("2/5  Sincronizando Git antes da geracao...")
        git_sync_remote()
    else:
        log("2/5  Git sync ignorado (--skip-git).")

    log("3/5  Gerando site...")
    generate_site()

    count, companies = read_latest_run()

    if not SKIP_NOTIFY:
        log("4/5  Notificacao...")
        send_notification(count, companies)
    else:
        log("4/5  Notificacao ignorada (--skip-notify).")

    if not SKIP_GIT:
        log("5/5  Git deploy...")
        git_deploy()
    else:
        log("5/5  Git ignorado (--skip-git).")

    log("=== Deploy concluido ===")
