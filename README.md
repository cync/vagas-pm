# Vagas PM Internacional

🌐 **Acesse o site:** [https://cync.github.io/vagas-pm/](https://cync.github.io/vagas-pm/)

Tracker de vagas internacionais para **Product Manager** — atualizado automaticamente 2× ao dia via GitHub Actions, sem depender do computador local.

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
| Remotive | Vagas remotas por categoria |
| Wellfound | Product Manager remoto com foco LATAM/global |

---

## Como funciona — pipeline GitHub Actions

O pipeline roda automaticamente na nuvem, sem precisar do computador ligado:

```
GitHub Actions (cron 06:00 e 15:00 BRT)
       ↓
search_and_generate.py
       ↓
APIs/páginas públicas — Greenhouse, Lever, Ashby, Remotive e Wellfound
       ↓
Filtro local determinístico de cargo/região/remoto
       ↓
Filtra URLs já vistas em vagas/url_history.json
       ↓
Salva vagas/vagas_pm_YYYY-MM-DD.md  (horário BRT)
       ↓
generate_site.py → gera index.html atualizado
       ↓
git commit + push → GitHub Pages atualizado
```

### Agendamento

| Horário BRT | Horário UTC | Dias |
|---|---|---|
| 06:00 | 09:00 | Segunda a sábado |
| 18:00 | 21:00 | Segunda a sábado |

Para rodar fora do agendamento: **Actions → "Vagas PM – Busca automática" → Run workflow**

---

## Estrutura do repositório

```
vagas-pm/
├── .github/
│   └── workflows/
│       └── vagas-pm.yml        ← workflow GitHub Actions (cron 2×/dia)
├── vagas/
│   ├── vagas_pm_YYYY-MM-DD.md  ← arquivos diários de vagas
│   └── url_history.json        ← histórico de URLs para deduplicação
├── index.html                  ← site gerado (GitHub Pages)
├── generate_site.py            ← lê os .md e gera o HTML
├── search_and_generate.py      ← pipeline principal (coleta direta + filtro + geração)
├── direct_sources.json         ← fontes ATS monitoradas
├── requirements.txt            ← dependências Python
├── broken_links.json           ← URLs inválidas detectadas
└── README.md                   ← este arquivo
```

---

## Configuração (primeira vez)

### 1. Secrets necessários

Nenhum secret é necessário para buscar vagas. As fontes atuais usam APIs públicas dos ATS.

Para notificações push, configure `ONESIGNAL_APP_ID` e `ONESIGNAL_REST_API_KEY` em **Settings → Secrets → Actions**.

### 2. GitHub Pages

Em **Settings → Pages**, confirme que a fonte é o branch `main`, pasta raiz `/`.

---

## Execução local (manual)

```powershell
# Na pasta raiz do repositório clonado:

# Instalar dependências
pip install -r requirements.txt

# Buscar vagas e regenerar site
python search_and_generate.py

# Publicar manualmente
git add vagas/ index.html
git commit -m "update manual"
git push
```

---

## Stack

| Componente | Tecnologia |
|---|---|
| Busca | APIs/páginas públicas diretas (`direct_sources.json`) |
| Extração | Filtro local determinístico |
| Geração HTML | Python puro (sem frameworks) |
| Hospedagem | GitHub Pages (branch `main`) |
| Automação | GitHub Actions (cron) |
| Deduplicação | `url_history.json` com todas as URLs já encontradas |

---

## Repositório

[github.com/cync/vagas-pm](https://github.com/cync/vagas-pm) — GitHub Pages branch: `main`
