#!/usr/bin/env python3
"""
Gerador do site de vagas PM — Mastercard Design System (fiel ao DESIGN.md)
Tipografia: Sofia Sans (substituto oficial do MarkForMC)
"""
import re, json
from datetime import datetime, timedelta, date
from pathlib import Path
from collections import defaultdict

_vagas_sub = Path(__file__).parent / "vagas"
VAGAS_DIR = _vagas_sub if (_vagas_sub.exists() and any(_vagas_sub.glob("vagas_pm_*.md"))) else Path(__file__).parent.parent
SITE_DIR  = Path(__file__).parent

def parse_md_file(filepath):
    text = filepath.read_text(encoding="utf-8")
    m = re.search(r'vagas_pm_(\d{4}-\d{2}-\d{2})', filepath.name)
    if not m:
        return None
    date_str = m.group(1)
    exec_n   = "2" if "_exec2" in filepath.name else "1"
    novas_m  = re.search(r'Novas encontradas\*\*:\s*(\d+)', text)
    novas    = int(novas_m.group(1)) if novas_m else 0
    jobs, current_ats = [], "Outros"
    for line in text.splitlines():
        hm = re.match(r'^###\s+[^\s]+\s+(.+)', line)
        if hm:
            current_ats = hm.group(1).strip(); continue
        rm = re.match(r'\|\s*\*\*(.+?)\*\*\s*\|\s*(.+?)\s*\|\s*\[Ver vaga\]\((.+?)\)', line)
        if rm:
            jobs.append({"company": rm.group(1).strip(), "role": rm.group(2).strip(),
                         "url": rm.group(3).strip(), "ats": current_ats,
                         "date": date_str, "exec": exec_n, "file": filepath.name})
    return {"date": date_str, "exec": exec_n, "file": filepath.name, "novas": novas, "jobs": jobs}

runs = [r for f in sorted(VAGAS_DIR.glob("vagas_pm_*.md")) if (r := parse_md_file(f))]
if runs: runs[-1]["is_latest"] = True

all_jobs = []
for run in runs:
    for j in run["jobs"]:
        j["is_latest"] = run.get("is_latest", False)
        all_jobs.append(j)

today      = date.today()
this_week  = today - timedelta(days=today.weekday())
last_week  = this_week - timedelta(weeks=1)

total_jobs   = len(all_jobs)
latest_count = runs[-1]["novas"] if runs else 0
total_runs   = len(runs)
now_str      = datetime.now().strftime("%d %b %Y · %H:%M")
jobs_json    = json.dumps(all_jobs, ensure_ascii=False)
runs_json    = json.dumps(runs,     ensure_ascii=False)
tw_iso       = this_week.isoformat()
lw_iso       = last_week.isoformat()

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PM Jobs · Felipe Saraiva</title>

<!-- Sofia Sans — substituto oficial do MarkForMC (fallback stack Mastercard) -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Sofia+Sans:ital,wght@0,400;0,450;0,500;0,700;1,450&display=swap" rel="stylesheet">

<style>
/* ══════════════════════════════════════════════════════
   MASTERCARD DESIGN SYSTEM — fiel ao DESIGN.md
   Tipografia: Sofia Sans (MarkForMC substitute)
   ══════════════════════════════════════════════════════ */
:root {{
  /* Cores — do Color Palette do DESIGN.md */
  --ink:          #141413;   /* Ink Black — texto, CTA primário, footer */
  --canvas:       #F3F0EE;   /* Canvas Cream — background da página */
  --lifted:       #FCFBFA;   /* Lifted Cream — superfície elevada */
  --white:        #FFFFFF;   /* Nav pill, cards, botões secundários */
  --slate:        #696969;   /* Slate Gray — texto secundário */
  --dust:         #D1CDC7;   /* Dust Taupe — texto fraco / placeholder */
  --signal-org:   #CF4500;   /* Signal Orange — APENAS consent/legal */
  --arc-org:      #F37338;   /* Light Signal Orange — arcos decorativos, acento */
  --clay:         #9A3A0A;   /* Clay Brown — links secundários */
  --link-blue:    #3860BE;   /* Link Blue — links inline */
  --soft-bone:    #F4F4F4;   /* Soft Bone — subregions alternativas */

  /* Raios — escala Mastercard: 20 / 40 / 999 */
  --r-btn:   20px;
  --r-card:  40px;
  --r-pill:  999px;

  /* Sombras atmosféricas */
  --shadow-1: rgba(0,0,0,0.04) 0px 4px 24px 0px;
  --shadow-2: rgba(0,0,0,0.08) 0px 24px 48px 0px;
}}

*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

body {{
  font-family: 'Sofia Sans', SofiaSans, Arial, sans-serif;
  font-weight: 450;            /* Peso 450 — assinatura do sistema */
  background: var(--canvas);   /* Canvas Cream — nunca branco puro */
  color: var(--ink);
  -webkit-font-smoothing: antialiased;
}}

/* ── Eyebrow (h5-level) ── */
.eyebrow {{
  font-size: 14px;
  font-weight: 700;
  line-height: 14px;
  letter-spacing: 0.56px;    /* +4% tracking */
  text-transform: uppercase;
  color: var(--slate);
  display: flex;
  align-items: center;
  gap: 6px;
}}
.eyebrow::before {{
  content: '•';
  color: var(--arc-org);     /* ponto de acento laranja */
  font-size: 10px;
}}

/* ══ HEADER ══════════════════════════════════════════ */
header {{
  background: var(--ink);
  padding: 0 48px;
  display: flex;
  align-items: stretch;
  justify-content: space-between;
  gap: 24px;
  flex-wrap: wrap;
}}
.header-brand {{
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 24px 0;
}}

/* Marca MC: dois círculos sobrepostos */
.mc-mark {{
  position: relative;
  width: 52px;
  height: 32px;
  flex-shrink: 0;
}}
.mc-mark .c-red {{
  position: absolute;
  width: 26px; height: 26px;
  border-radius: 50%;
  background: #EB001B;
  top: 3px; left: 0;
}}
.mc-mark .c-yel {{
  position: absolute;
  width: 26px; height: 26px;
  border-radius: 50%;
  background: #F79E1B;
  top: 3px; left: 16px;
  mix-blend-mode: screen;
  opacity: 0.9;
}}

.brand-copy h1 {{
  /* H2-level no design system: 36px / 500 / -2% tracking */
  font-size: 22px;
  font-weight: 500;
  letter-spacing: -0.44px;   /* -2% de 22px */
  line-height: 28px;
  color: var(--white);
}}
.brand-copy p {{
  font-size: 13px;
  font-weight: 450;
  color: var(--dust);
  margin-top: 2px;
  letter-spacing: 0;
}}

.header-right {{
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 24px 0;
  flex-wrap: wrap;
}}

/* Stats como pills lifted */
.stat-pill {{
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: var(--r-pill);
  padding: 8px 20px;
  text-align: center;
  min-width: 70px;
}}
.stat-pill .num {{
  display: block;
  font-size: 20px;
  font-weight: 500;
  letter-spacing: -0.4px;
  color: var(--arc-org);
  line-height: 1;
}}
.stat-pill .lbl {{
  display: block;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.44px;
  text-transform: uppercase;
  color: var(--dust);
  margin-top: 2px;
}}

/* Link pessoal — botão secundário outlined */
.personal-link {{
  display: inline-flex;
  align-items: center;
  gap: 6px;
  text-decoration: none;
  background: transparent;
  border: 1.5px solid rgba(255,255,255,0.25);
  border-radius: var(--r-btn);     /* 20px — raio de botão */
  padding: 8px 20px;
  font-family: inherit;
  font-size: 14px;
  font-weight: 500;
  letter-spacing: -0.28px;         /* -2% */
  color: var(--white);
  transition: border-color .2s, background .2s;
}}
.personal-link:hover {{
  border-color: var(--arc-org);
  color: var(--arc-org);
}}

/* ══ CONTROLES (nav pill sticky) ══════════════════════ */
.controls {{
  background: var(--white);
  border-bottom: 1px solid rgba(20,20,19,0.1);
  padding: 12px 48px;
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
  position: sticky;
  top: 0;
  z-index: 100;
  box-shadow: var(--shadow-1);    /* sombra atmosférica nivel 1 */
}}
.search-wrap {{ flex: 1; min-width: 200px; position: relative; }}
.search-wrap input {{
  width: 100%;
  padding: 10px 20px 10px 38px;
  border: 1px solid rgba(20,20,19,0.2);
  border-radius: var(--r-pill);
  font-family: inherit;
  font-size: 15px;
  font-weight: 450;
  background: var(--canvas);
  color: var(--ink);
  outline: none;
  transition: border-color .2s;
}}
.search-wrap input:focus {{ border-color: var(--ink); }}
.search-wrap input::placeholder {{ color: var(--slate); }}
.search-wrap::before {{
  content: '⌕';
  position: absolute;
  left: 14px; top: 50%;
  transform: translateY(-50%);
  font-size: 16px;
  color: var(--slate);
  pointer-events: none;
}}
.ctl-select {{
  padding: 10px 16px;
  border: 1px solid rgba(20,20,19,0.2);
  border-radius: var(--r-pill);
  font-family: inherit;
  font-size: 14px;
  font-weight: 450;
  background: var(--canvas);
  color: var(--ink);
  cursor: pointer;
  outline: none;
}}
.ctl-select:focus {{ border-color: var(--ink); }}

.toggle-new {{
  display: flex; align-items: center; gap: 6px;
  font-family: inherit;
  font-size: 14px;
  font-weight: 500;
  color: var(--slate);
  cursor: pointer;
  padding: 10px 18px;
  border: 1px solid rgba(20,20,19,0.2);
  border-radius: var(--r-pill);
  background: var(--canvas);
  user-select: none;
  transition: all .2s;
  letter-spacing: -0.14px;
}}
.toggle-new.on {{
  background: var(--ink);
  border-color: var(--ink);
  color: var(--canvas);
}}
.toggle-new input {{ display: none; }}

/* Contador — eyebrow style */
.count-pill {{
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.52px;
  text-transform: uppercase;
  color: var(--slate);
  white-space: nowrap;
  padding: 10px 16px;
}}

/* ══ MAIN ════════════════════════════════════════════ */
main {{ max-width: 1040px; margin: 0 auto; padding: 40px 24px 80px; }}

/* Week navigation pills */
.week-nav {{
  display: flex;
  gap: 10px;
  margin-bottom: 40px;
  flex-wrap: wrap;
}}
.week-btn {{
  padding: 10px 24px;
  border-radius: var(--r-pill);
  font-family: inherit;
  font-size: 14px;
  font-weight: 500;
  letter-spacing: -0.14px;
  cursor: pointer;
  border: 1.5px solid transparent;
  transition: all .2s;
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--white);
  color: var(--ink);
  border-color: rgba(20,20,19,0.15);
  box-shadow: var(--shadow-1);
}}
.week-btn.active {{
  background: var(--ink);
  color: var(--canvas);
  border-color: var(--ink);
  box-shadow: var(--shadow-2);
}}
.week-btn:hover:not(.active) {{
  border-color: var(--ink);
  box-shadow: var(--shadow-2);
}}
.week-btn .cnt {{
  font-size: 12px;
  font-weight: 700;
  opacity: 0.6;
  letter-spacing: 0;
}}

/* Seção de semana */
.week-section {{ margin-bottom: 48px; }}
.section-header {{ margin-bottom: 20px; }}
.section-title {{
  /* H3 level: 24px / 500 / -2% tracking */
  font-size: 24px;
  font-weight: 500;
  letter-spacing: -0.48px;
  line-height: 28.8px;
  color: var(--ink);
  margin-bottom: 4px;
}}
.section-range {{
  font-size: 14px;
  font-weight: 450;
  color: var(--slate);
}}

/* Month grouping label — eyebrow */
.month-label {{
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0.56px;
  text-transform: uppercase;
  color: var(--arc-org);
  margin-bottom: 12px;
  margin-top: 24px;
  display: flex;
  align-items: center;
  gap: 6px;
}}
.month-label::before {{
  content: '•';
  font-size: 10px;
}}

/* Linha decorativa separadora (orbital) */
.orbit-line {{
  height: 1px;
  background: linear-gradient(90deg, var(--arc-org) 0%, transparent 100%);
  margin: 4px 0 20px;
  opacity: 0.4;
}}

/* ── Run Card — stadium shape (40px radius) ── */
.run-card {{
  background: var(--white);
  border: 1px solid rgba(20,20,19,0.1);
  border-radius: var(--r-card);   /* 40px — stadium */
  margin-bottom: 12px;
  overflow: hidden;
  transition: box-shadow .25s, transform .2s;
}}
.run-card:hover {{
  box-shadow: var(--shadow-2);
  transform: translateY(-2px);
}}
.run-header {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 28px;
  cursor: pointer;
  gap: 12px;
}}
.run-header:hover {{ background: var(--canvas); border-radius: var(--r-card) var(--r-card) 0 0; }}
.run-date {{
  /* Nav/button level: 16px / 500 / -3% tracking */
  font-size: 16px;
  font-weight: 500;
  letter-spacing: -0.48px;
  color: var(--ink);
}}
.run-exec {{
  font-size: 13px;
  font-weight: 450;
  color: var(--slate);
  margin-left: 6px;
}}
.run-badges {{ display: flex; gap: 8px; align-items: center; }}

/* Badges */
.badge {{
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.48px;
  text-transform: uppercase;
  padding: 4px 14px;
  border-radius: var(--r-pill);
  white-space: nowrap;
  line-height: 1;
}}
/* Badge "mais recente" — Ink Black pill com canvas text (CTA primário) */
.badge-latest {{
  background: var(--ink);
  color: var(--canvas);
  border: 1.5px solid var(--ink);
}}
/* Badge contador — outlined */
.badge-count {{
  background: transparent;
  color: var(--slate);
  border: 1px solid rgba(20,20,19,0.2);
}}
.chevron {{
  font-size: 11px;
  color: var(--dust);
  transition: transform .2s;
  margin-left: 4px;
}}
.run-card.open .chevron {{ transform: rotate(180deg); }}

/* Tabela de vagas */
.jobs-panel {{ display: none; border-top: 1px solid rgba(20,20,19,0.08); }}
.run-card.open .jobs-panel {{ display: block; }}
.jobs-panel table {{ width: 100%; border-collapse: collapse; }}
.jobs-panel th {{
  background: var(--canvas);
  text-align: left;
  padding: 10px 28px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.48px;         /* eyebrow tracking */
  text-transform: uppercase;
  color: var(--slate);
}}
.jobs-panel td {{
  padding: 12px 28px;
  border-top: 1px solid rgba(20,20,19,0.06);
  vertical-align: middle;
  font-size: 14px;
  font-weight: 450;
}}
.jobs-panel tr:hover td {{ background: var(--lifted); }}
.col-company {{ font-weight: 500; letter-spacing: -0.14px; color: var(--ink); }}
.col-role    {{ color: var(--ink); }}

/* ATS tag — chip outline */
.ats-tag {{
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.48px;
  text-transform: uppercase;
  padding: 3px 12px;
  border-radius: var(--r-pill);
  background: var(--canvas);
  color: var(--slate);
  border: 1px solid rgba(20,20,19,0.15);
  white-space: nowrap;
}}

/* Botão Apply — CTA primário: Ink Black pill / canvas text */
a.apply-btn {{
  display: inline-block;
  font-family: inherit;
  font-size: 14px;
  font-weight: 500;
  letter-spacing: -0.28px;   /* -2% */
  color: var(--canvas);
  text-decoration: none;
  background: var(--ink);
  border: 1.5px solid var(--ink);
  border-radius: var(--r-btn);   /* 20px */
  padding: 6px 20px;
  white-space: nowrap;
  transition: background .15s, color .15s;
}}
a.apply-btn:hover {{
  background: var(--canvas);
  color: var(--ink);
}}

.empty {{
  text-align: center;
  padding: 80px 24px;
  font-size: 16px;
  font-weight: 450;
  color: var(--slate);
}}

/* ══ FOOTER ══════════════════════════════════════════ */
footer {{
  background: var(--ink);      /* Ink Black footer */
  padding: 48px 48px 64px;
}}
.footer-headline {{
  /* H2 level: 36px / 500 / -2% tracking */
  font-size: 28px;
  font-weight: 500;
  letter-spacing: -0.56px;
  line-height: 36px;
  color: var(--white);
  margin-bottom: 32px;
  max-width: 480px;
}}
.footer-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px,1fr));
  gap: 32px;
  margin-bottom: 40px;
}}
.footer-col-header {{
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.56px;
  text-transform: uppercase;
  color: var(--dust);
  margin-bottom: 14px;
}}
.footer-col a {{
  display: block;
  font-size: 14px;
  font-weight: 450;
  color: rgba(255,255,255,0.7);
  text-decoration: none;
  margin-bottom: 8px;
  transition: color .15s;
}}
.footer-col a:hover {{ color: var(--white); }}
.footer-divider {{
  height: 1px;
  background: rgba(255,255,255,0.12);
  margin-bottom: 24px;
}}
.footer-bottom {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 12px;
  font-weight: 450;
  color: var(--dust);
}}
.footer-bottom a {{
  color: var(--dust);
  text-decoration: none;
}}
.footer-bottom a:hover {{ color: var(--white); }}
.updated-badge {{
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: rgba(255,255,255,0.08);
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: var(--r-pill);
  padding: 4px 14px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.44px;
  text-transform: uppercase;
  color: var(--arc-org);
}}
</style>
</head>
<body>

<!-- ══ HEADER ══════════════════════════════════════════ -->
<header>
  <div class="header-brand">
    <div class="brand-copy">
      <h1>PM Jobs Internacional</h1>
      <p>curated by Felipe Saraiva · AI Product Builder</p>
    </div>
  </div>
  <div class="header-right">
    <div class="stat-pill">
      <span class="num" id="vis-count">{total_jobs}</span>
      <span class="lbl">vagas</span>
    </div>
    <div class="stat-pill">
      <span class="num">{total_runs}</span>
      <span class="lbl">execuções</span>
    </div>
    <div class="stat-pill">
      <span class="num">{latest_count}</span>
      <span class="lbl">hoje</span>
    </div>
    <a class="personal-link" href="https://felipesaraiva.com" target="_blank" rel="noopener">
      felipesaraiva.com ↗
    </a>
  </div>
</header>

<!-- ══ CONTROLS ════════════════════════════════════════ -->
<div class="controls">
  <div class="search-wrap">
    <input type="text" id="search" placeholder="Buscar empresa, cargo, plataforma…" oninput="applyFilter()">
  </div>
  <select class="ctl-select" id="sel-year"  onchange="applyFilter()"><option value="">Todos os anos</option></select>
  <select class="ctl-select" id="sel-month" onchange="applyFilter()"><option value="">Todos os meses</option></select>
  <select class="ctl-select" id="sel-ats"   onchange="applyFilter()"><option value="">Todas as plataformas</option></select>
  <label class="toggle-new" id="lbl-new">
    <input type="checkbox" id="only-new" onchange="document.getElementById('lbl-new').classList.toggle('on',this.checked);applyFilter()">
    ✦ Só novas
  </label>
  <span class="count-pill" id="count-lbl">{total_jobs} vagas</span>
</div>

<!-- ══ MAIN ════════════════════════════════════════════ -->
<main>
  <div class="week-nav" id="week-nav"></div>
  <div id="content"></div>
</main>

<!-- ══ FOOTER ════════════════════════════════════════ -->
<footer>
  <div class="footer-headline">Always here when the right role appears.</div>
  <div class="footer-grid">
    <div class="footer-col">
      <div class="footer-col-header">• Links</div>
      <a href="https://felipesaraiva.com" target="_blank">felipesaraiva.com ↗</a>
      <a href="https://github.com/cync/vagas-pm" target="_blank">GitHub — vagas-pm ↗</a>
      <a href="https://linkedin.com/in/felipesaraiva" target="_blank">LinkedIn ↗</a>
    </div>
    <div class="footer-col">
      <div class="footer-col-header">• Plataformas</div>
      <a href="https://jobs.lever.co" target="_blank">Lever</a>
      <a href="https://jobs.ashbyhq.com" target="_blank">Ashby HQ</a>
      <a href="https://greenhouse.io" target="_blank">Greenhouse</a>
      <a href="https://weworkremotely.com" target="_blank">We Work Remotely</a>
    </div>

  </div>
  <div class="footer-divider"></div>
  <div class="footer-bottom">
    <span>© {datetime.now().year} Felipe Saraiva · Atualizado em {now_str}</span>
    <span class="updated-badge">✦ {total_jobs} vagas · {total_runs} execuções</span>
  </div>
</footer>

<script>
const ALL_JOBS = {jobs_json};
const RUNS     = {runs_json};

// Populate selects
const years   = [...new Set(ALL_JOBS.map(j=>j.date.slice(0,4)))].sort().reverse();
const months  = [...new Set(ALL_JOBS.map(j=>{{const d=new Date(j.date+'T12:00:00');return d.toLocaleString('en',{{month:'long'}})+' '+j.date.slice(0,4)}}))].sort((a,b)=>new Date('01 '+b)-new Date('01 '+a));
const atsList = [...new Set(ALL_JOBS.map(j=>j.ats))].sort();
const selYear = document.getElementById('sel-year');
const selMonth= document.getElementById('sel-month');
const selAts  = document.getElementById('sel-ats');
years.forEach(y  => selYear.innerHTML  += `<option>${{y}}</option>`);
months.forEach(m => selMonth.innerHTML += `<option>${{m}}</option>`);
atsList.forEach(a=> selAts.innerHTML   += `<option>${{a}}</option>`);

// Week helpers
const TW = '{tw_iso}';
const LW = '{lw_iso}';

function weekStart(s) {{
  const d = new Date(s+'T12:00:00');
  d.setDate(d.getDate() - ((d.getDay()+6)%7));
  return d.toISOString().slice(0,10);
}}
function weekBucket(s) {{
  const ws = weekStart(s);
  if (ws >= TW) return 'this_week';
  if (ws >= LW) return 'last_week';
  return 'earlier';
}}
function fmtDate(s) {{
  const [y,m,d]=s.split('-');
  return `${{parseInt(d)}} ${{['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][+m-1]}} ${{y}}`;
}}
function fmtRange(isoMon) {{
  const s=new Date(isoMon+'T12:00:00'),e=new Date(isoMon+'T12:00:00');
  e.setDate(e.getDate()+6);
  const M=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  return `${{s.getDate()}} ${{M[s.getMonth()]}} – ${{e.getDate()}} ${{M[e.getMonth()]}}`;
}}

let activeWeek = null;

function applyFilter() {{
  const q      = document.getElementById('search').value.toLowerCase();
  const year   = selYear.value;
  const month  = selMonth.value;
  const ats    = selAts.value;
  const onlyNew= document.getElementById('only-new').checked;

  const vis = ALL_JOBS.filter(j => {{
    if (onlyNew && !j.is_latest) return false;
    if (year  && !j.date.startsWith(year)) return false;
    if (ats   && j.ats !== ats) return false;
    if (month) {{
      const d=new Date(j.date+'T12:00:00');
      if (d.toLocaleString('en',{{month:'long'}})+' '+j.date.slice(0,4)!==month) return false;
    }}
    if (activeWeek && weekBucket(j.date)!==activeWeek) return false;
    if (q && !(j.company+' '+j.role+' '+j.ats).toLowerCase().includes(q)) return false;
    return true;
  }});

  document.getElementById('vis-count').textContent = vis.length;
  document.getElementById('count-lbl').textContent  = vis.length + ' vagas';

  const runMap={{}};
  vis.forEach(j=>{{ if(!runMap[j.file]) runMap[j.file]=[]; runMap[j.file].push(j); }});

  // Count per bucket (unfiltered by week for nav badges)
  const twN=ALL_JOBS.filter(j=>weekBucket(j.date)==='this_week').length;
  const lwN=ALL_JOBS.filter(j=>weekBucket(j.date)==='last_week').length;
  const olN=ALL_JOBS.filter(j=>weekBucket(j.date)==='earlier').length;

  // Week nav
  const navData=[
    {{key:'this_week', label:'Esta semana',    cnt:twN}},
    {{key:'last_week', label:'Semana passada', cnt:lwN}},
    {{key:'earlier',   label:'Anteriores',     cnt:olN}},
  ];
  document.getElementById('week-nav').innerHTML = navData.map(n=>`
    <button class="week-btn${{activeWeek===n.key?' active':''}}" onclick="setWeek('${{n.key}}')">
      ${{n.label}} <span class="cnt">(${{n.cnt}})</span>
    </button>`).join('')
    + (activeWeek ? `<button class="week-btn" onclick="setWeek(null)">✕ Ver tudo</button>` : '');

  // Build content
  const buckets={{'this_week':[],'last_week':[],'earlier':[]}};
  RUNS.forEach(run=>{{
    const jobs=runMap[run.file];
    if(!jobs||!jobs.length) return;
    const b=weekBucket(run.date);
    buckets[b].push({{...run,visJobs:jobs}});
  }});

  const order = activeWeek ? [activeWeek] : ['this_week','last_week','earlier'];
  const labels = {{
    this_week: {{title:'Esta Semana',   range:fmtRange(TW)}},
    last_week: {{title:'Semana Passada',range:fmtRange(LW)}},
    earlier:   {{title:'Execuções Anteriores', range:''}},
  }};

  let html='';
  order.forEach(bk=>{{
    const bRuns=buckets[bk];
    if(!bRuns||!bRuns.length) return;
    bRuns.sort((a,b)=>b.date.localeCompare(a.date));
    const lbl=labels[bk];
    html+=`<div class="week-section">
      <div class="section-header">
        <div class="section-title">${{lbl.title}}</div>
        ${{lbl.range ? `<div class="section-range">${{lbl.range}}</div>` : ''}}
      </div>
      <div class="orbit-line"></div>`;

    if(bk==='earlier') {{
      const byM={{}};
      bRuns.forEach(r=>{{
        const d=new Date(r.date+'T12:00:00');
        const mk=d.toLocaleString('en',{{month:'long'}})+' '+r.date.slice(0,4);
        if(!byM[mk]) byM[mk]=[];
        byM[mk].push(r);
      }});
      Object.keys(byM).sort((a,b)=>new Date('01 '+b)-new Date('01 '+a)).forEach(mk=>{{
        html+=`<div class="month-label">${{mk}}</div>`;
        byM[mk].forEach(r=>{{ html+=card(r); }});
      }});
    }} else {{
      bRuns.forEach(r=>{{ html+=card(r); }});
    }}
    html+='</div>';
  }});

  if(!html) html='<div class="empty">Nenhuma vaga encontrada para os filtros selecionados.</div>';
  document.getElementById('content').innerHTML=html;

  // Auto-open latest
  const lat=RUNS.find(r=>r.is_latest);
  if(lat&&runMap[lat.file]) {{
    const el=document.getElementById('card-'+lat.file.replace(/\\./g,'_'));
    if(el) el.classList.add('open');
  }}
}}

function card(run) {{
  const id=run.file.replace(/\\./g,'_');
  const rows=run.visJobs.map(j=>`
    <tr>
      <td><div class="col-company">${{j.company}}</div></td>
      <td><div class="col-role">${{j.role}}</div></td>
      <td><span class="ats-tag">${{j.ats}}</span></td>
      <td><a class="apply-btn" href="${{j.url}}" target="_blank" rel="noopener">Ver vaga ↗</a></td>
    </tr>`).join('');
  return `
  <div class="run-card" id="card-${{id}}">
    <div class="run-header" onclick="toggle('${{id}}')">
      <div>
        <span class="run-date">${{fmtDate(run.date)}}</span>
        <span class="run-exec">· execução ${{run.exec}}</span>
      </div>
      <div class="run-badges">
        ${{run.is_latest ? '<span class="badge badge-latest">✦ mais recente</span>' : ''}}
        <span class="badge badge-count">${{run.visJobs.length}} vagas</span>
        <span class="chevron">▾</span>
      </div>
    </div>
    <div class="jobs-panel">
      <table>
        <thead><tr><th>Empresa</th><th>Cargo</th><th>Plataforma</th><th>Link</th></tr></thead>
        <tbody>${{rows}}</tbody>
      </table>
    </div>
  </div>`;
}}

function setWeek(w) {{ activeWeek=w; applyFilter(); }}
function toggle(id) {{ document.getElementById('card-'+id)?.classList.toggle('open'); }}
applyFilter();
</script>
</body>
</html>"""

(SITE_DIR / "index.html").write_text(html, encoding="utf-8")
print(f"OK — {total_runs} execuções · {total_jobs} vagas")
