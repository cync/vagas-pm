# 🧭 Vagas PM Internacional

🌐 **[Acesse o site →](https://cync.github.io/vagas-pm/)**

> Tracker diário de vagas **remote-first para Product Manager** abertas a candidatos do Brasil e LATAM — buscadas diretamente nos ATS das empresas, sem intermediários.

---

## Por que este projeto existe

A maioria dos job boards agrega vagas com atraso, duplica anúncios e mistura posições que não aceitam candidatos fora dos EUA. Este tracker faz buscas diárias direto nos sistemas de recrutamento (Lever, Ashby, Greenhouse etc.), filtra por critérios de elegibilidade (remote, LATAM, Brazil, global) e remove URLs já vistas em execuções anteriores — entregando apenas o que é genuinamente novo.

---

## O site

- **Organizado por data** → cada execução diária é uma seção própria
- **Filtros por ATS** → Lever, Ashby, Greenhouse, SmartRecruiters, WWR...
- **Busca por texto** → filtre por empresa, cargo ou palavra-chave
- **Deduplicação automática** → vagas já exibidas anteriormente não reaparecem
- **Verificação de links** → URLs quebradas ou expiradas são removidas antes de publicar

---

## Fontes monitoradas

| Plataforma ATS | Por que monitorar |
|---|---|
| **Lever** | Usado por startups de série B/C, fintechs, empresas LATAM-first |
| **Ashby HQ** | Favorito de empresas remote-first modernas (PLG, AI, SaaS) |
| **Greenhouse** | Usado por scale-ups e empresas públicas (Coinbase, Remote.com) |
| **SmartRecruiters** | Empresas globais de médio/grande porte (Wise, Canva) |
| **We Work Remotely** | Board curado de vagas 100% remotas, "anywhere" |
| **Remotive / Himalayas** | Agregadores com foco em LATAM e remote global |
| **Workable / Bamboo** | PMEs tech com abertura a contratação internacional |

---

## Critérios de busca

As vagas são filtradas por combinação de termos. Só entram no tracker se atenderem **todos** os critérios:

- **Cargo:** `product manager` (Senior, Staff, Principal, Group, Head)
- **Localização:** `Brazil`, `Brasil`, `LATAM`, `South America`, `EMEA`, `global`, `international`
- **Modalidade:** `remote`, `home office`, `anywhere`, `work from home`
- **Excluídos:** `site:remoterocketship.com` e outros agregadores secundários

---

## Como funciona (fluxo automático)

```
┌─────────────────────────────────────────────────────┐
│  Tarefa agendada: VagasPM (diária, via Cowork)       │
│                                                      │
│  1. Lê histórico de URLs já encontradas              │
│  2. Busca vagas nos ATS com query estruturada        │
│  3. Filtra apenas URLs novas                         │
│  4. Verifica se os links ainda estão ativos          │
│  5. Salva vagas_pm_YYYY-MM-DD.md                    │
│  6. Roda generate_site.py → atualiza index.html      │
└─────────────────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────────────────┐
│  Tarefa agendada: VagasPM-GitPush (logo depois)      │
│                                                      │
│  git add index.html README.md                        │
│  git commit -m "update: vagas PM — <data>"           │
│  git push → GitHub Pages atualizado                  │
└─────────────────────────────────────────────────────┘
```

---

## Estrutura do repositório

```
vagas-pm/                        ← este repositório (GitHub Pages)
├── index.html                   ← site completo (gerado automaticamente)
├── generate_site.py             ← script Python que lê os .md e gera o HTML
├── broken_links.json            ← cache de URLs inválidas já detectadas
├── push_update.bat              ← script de push manual (Windows)
└── README.md                    ← este arquivo

VagasInternacionais/             ← pasta local (não versionada)
├── vagas_pm_2026-05-27.md
├── vagas_pm_2026-05-26.md
├── vagas_pm_2026-05-26_exec2.md
└── ...
```

---

## Execução manual

```powershell
# Na pasta site/, regenerar o HTML a partir dos arquivos .md locais:
python generate_site.py

# Commitar e publicar no GitHub Pages:
git add index.html README.md
git commit -m "update manual"
git push
```

---

## Stack

- **Busca:** Google Search (operadores `site:` + filtros de texto)
- **Geração do site:** Python + `generate_site.py` (HTML puro, zero dependências)
- **Hospedagem:** GitHub Pages (branch `main`)
- **Automação:** Cowork (Claude AI) + Windows Task Scheduler

---

## Estatísticas

| Métrica | Valor |
|---|---|
| Execuções realizadas | 19+ |
| Vagas únicas encontradas | 160+ |
| Plataformas monitoradas | 30+ ATS |
| Frequência de atualização | Diária |

---

## Aviso

As vagas listadas são coletadas automaticamente. Sempre verifique o link original antes de candidatar-se — algumas podem expirar entre a coleta e o acesso. Links quebrados são removidos automaticamente na próxima execução.

---

[github.com/cync/vagas-pm](https://github.com/cync/vagas-pm)
