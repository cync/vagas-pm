# Vagas PM Internacional

🌐 **Acesse o site:** [https://cync.github.io/vagas-pm/](https://cync.github.io/vagas-pm/)

Tracker de vagas internacionais para **Product Manager** — atualizado automaticamente todos os dias via Cowork (Claude AI).

---

## O que é

Um agregador de vagas remote-first para PMs que aceita candidatos do Brasil / LATAM, com foco em empresas internacionais. As vagas são buscadas diretamente nos principais ATS globais (sem depender de job boards agregadores).

O site exibe todas as execuções históricas, organizadas por data, com filtros por plataforma ATS e busca por empresa ou cargo.

---

## Fontes monitoradas

| ATS / Plataforma | Exemplos de empresas |
|---|---|
| Lever | dLocal, Binance, Bluelight, 3Pillar |
| Ashby HQ | Hubstaff, Owner.com, Quora, Hopper |
| Greenhouse | Coinbase, Remote.com, Cloudbeds, QuintoAndar |
| SmartRecruiters | Wise, Canva |
| We Work Remotely | Vagas abertas globalmente |
| Remotive / Himalayas | Vagas LATAM-friendly |

---

## Como funciona

```
1. Tarefa VagasPM (Cowork) roda diariamente
       ↓
2. Busca vagas novas nos ATS (ignora URLs já encontradas)
       ↓
3. Salva vagas_pm_YYYY-MM-DD.md em VagasInternacionais/
       ↓
4. Roda generate_site.py → gera index.html atualizado
       ↓
5. Tarefa VagasPM-GitPush faz git push → GitHub Pages atualizado
```

---

## Estrutura do projeto

```
VagasInternacionais/
├── vagas_pm_YYYY-MM-DD.md   ← arquivos diários de vagas
└── site/
    ├── index.html            ← site gerado (GitHub Pages)
    ├── generate_site.py      ← script que lê os .md e gera o HTML
    ├── push_update.bat       ← push manual para o GitHub
    ├── broken_links.json     ← URLs inválidas detectadas
    └── README.md             ← este arquivo
```

---

## Execução manual

Para rodar fora da tarefa agendada, abra o PowerShell na pasta `site/`:

```powershell
# Regenerar o site
python generate_site.py

# Commitar e publicar
git add index.html README.md
git commit -m "update manual"
git push
```

---

## Repositório

[github.com/cync/vagas-pm](https://github.com/cync/vagas-pm) — GitHub Pages branch: `main`
