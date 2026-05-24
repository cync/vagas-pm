#!/usr/bin/env python3
"""
Gerador do site de vagas PM internacionais — Mastercard Design System
"""
import os, re, json
from datetime import datetime, timedelta, date
from pathlib import Path
from collections import defaultdict

VAGAS_DIR = Path(__file__).parent.parent
SITE_DIR  = Path(__file__).parent

# ── Parse markdown files ─────────────────────────────────
def parse_md_file(filepath):
    text = filepath.read_text(encoding="utf-8")
    m = re.search(r'vagas_pm_(\d{4}-\d{2}-\d{2})', filepath.name)
    if not m:
        return None
    date_str = m.group(1)
    exec_n   = "2" if "_exec2" in filepath.name else "1"
    novas_m  = re.search(r'Novas encontradas\*\*:\s*(\d+)', text)
    novas    = int(novas_m.group(1)) if novas_m else 0
    jobs = []
    current_ats = "Outros"
    for line in text.splitlines():
        header_m = re.match(r'^###\s+[^\s]+\s+(.+)', line)
        if header_m:
            current_ats = header_m.group(1).strip()
            continue
        row_m = re.match(r'\|\s*\*\*(.+?)\*\*\s*\|\s*(.+?)\s*\|\s*\[Ver vaga\]\((.+?)\)', line)
        if row_m:
            jobs.append({
                "company": row_m.group(1).strip(),
                "role":    row_m.group(2).strip(),
                "url":     row_m.group(3).strip(),
                "ats":     current_ats,
                "date":    date_str,
                "exec":    exec_n,
                "file":    filepath.name,
            })
    return {"date": date_str, "exec": exec_n, "file": filepath.name, "novas": novas, "jobs": jobs}

md_files = sorted(VAGAS_DIR.glob("vagas_pm_*.md"))
runs = []
for f in md_files:
    r = parse_md_file(f)
    if r:
        runs.append(r)

if runs:
    runs[-1]["is_latest"] = True
    latest_date = runs[-1]["date"]
else:
    latest_date = ""

all_jobs = []
for run in runs:
    is_latest = run.get("is_latest", False)
    for j in run["jobs"]:
        j["is_latest"] = is_latest
        all_jobs.append(j)

# Week helpers
def week_start(d):
    """Monday of the week containing d"""
    if isinstance(d, str):
        d = date.fromisoformat(d)
    return d - timedelta(days=d.weekday())

today      = date.today()
this_week  = week_start(today)
last_week  = this_week - timedelta(weeks=1)

def week_label(d_str):
    ws = week_start(d_str)
    if ws == this_week:
        return "this_week"
    if ws == last_week:
        return "last_week"
    return "earlier"

total_jobs   = len(all_jobs)
latest_count = runs[-1]["novas"] if runs else 0
total_runs   = len(runs)

now_str = datetime.now().strftime("%d %b %Y · %H:%M")
jobs_json = json.dumps(all_jobs, ensure_ascii=False)
runs_json = json.dumps(runs,     ensure_ascii=False)

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PM Jobs · Felipe Saraiva</title>
<style>
/* ── Mastercard Design System ── */
:root {{
  --cream:   #FDF8F0;
  --cream2:  #F5EDD8;
  --red:     #EB001B;
  --orange:  #F79E1B;
  --amber:   #FF5F00;
  --dark:    #1A1108;
  --navy:    #01386A;
  --gray:    #6B5E4E;
  --lgray:   #EDE8DF;
  --border:  #DDD5C4;
  --white:   #FFFFFF;
  --pill:    999px;
  --r-card:  20px;
  --r-btn:   999px;
}}
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background: var(--cream);
  color: var(--dark);
  min-height: 100vh;
}}

/* ── Header ── */
header {{
  background: var(--dark);
  padding: 0 32px;
  display: flex;
  align-items: stretch;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}}
.header-brand {{
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px 0;
}}
.mc-logo {{
  position: relative;
  width: 48px;
  height: 30px;
  flex-shrink: 0;
}}
.mc-logo .c1 {{
  position: absolute; left: 0; top: 0;
  width: 22px; height: 22px; border-radius: 50%;
  background: var(--red); opacity: 0.95;
  top: 4px;
}}
.mc-logo .c2 {{
  position: absolute; left: 14px; top: 4px;
  width: 22px; height: 22px; border-radius: 50%;
  background: var(--orange); opacity: 0.95;
  mix-blend-mode: normal;
}}
.mc-logo .c-overlap {{
  position: absolute; left: 14px; top: 4px;
  width: 8px; height: 22px;
  background: var(--amber); opacity: 0.85;
  clip-path: ellipse(8px 11px at 0% 50%);
}}
.brand-text h1 {{ font-size: 1.1rem; font-weight: 800; color: #fff; letter-spacing: -0.3px; }}
.brand-text p  {{ font-size: 0.75rem; color: #a89880; margin-top: 1px; }}
.header-right {{
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 20px 0;
}}
.stat-pill {{
  background: rgba(255,255,255,0.07);
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: var(--pill);
  padding: 6px 16px;
  text-align: center;
}}
.stat-pill .num {{ font-size: 1.2rem; font-weight: 800; color: var(--orange); line-height: 1; }}
.stat-pill .lbl {{ font-size: 0.65rem; color: #a89880; text-transform: uppercase; letter-spacing: 0.5px; }}
.personal-link {{
  display: flex;
  align-items: center;
  gap: 8px;
  text-decoration: none;
  background: rgba(247,158,27,0.15);
  border: 1px solid rgba(247,158,27,0.35);
  border-radius: var(--pill);
  padding: 8px 18px;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--orange);
  transition: background 0.2s;
}}
.personal-link:hover {{ background: rgba(247,158,27,0.25); }}

/* ── Controls bar ── */
.controls {{
  background: var(--white);
  border-bottom: 1px solid var(--border);
  padding: 12px 32px;
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
  position: sticky;
  top: 0;
  z-index: 100;
  box-shadow: 0 2px 12px rgba(26,17,8,0.06);
}}
.search-wrap {{
  flex: 1;
  min-width: 180px;
  position: relative;
}}
.search-wrap input {{
  width: 100%;
  padding: 9px 16px 9px 36px;
  border: 1.5px solid var(--border);
  border-radius: var(--pill);
  font-size: 0.875rem;
  background: var(--cream);
  color: var(--dark);
  outline: none;
  transition: border-color .2s;
}}
.search-wrap input:focus {{ border-color: var(--orange); }}
.search-wrap::before {{
  content: '🔍';
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 0.8rem;
  pointer-events: none;
}}
.ctl-select {{
  padding: 9px 14px;
  border: 1.5px solid var(--border);
  border-radius: var(--pill);
  font-size: 0.8rem;
  background: var(--cream);
  color: var(--dark);
  cursor: pointer;
  outline: none;
}}
.ctl-select:focus {{ border-color: var(--orange); }}
.toggle-new {{
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.8rem;
  color: var(--gray);
  cursor: pointer;
  padding: 8px 14px;
  border: 1.5px solid var(--border);
  border-radius: var(--pill);
  background: var(--cream);
  user-select: none;
  transition: border-color .2s, background .2s;
}}
.toggle-new.active {{
  background: #FEF3C7;
  border-color: var(--orange);
  color: #92400e;
  font-weight: 600;
}}
.toggle-new input {{ display: none; }}
.count-pill {{
  background: var(--cream2);
  border: 1px solid var(--border);
  border-radius: var(--pill);
  padding: 6px 14px;
  font-size: 0.78rem;
  font-weight: 700;
  color: var(--amber);
  white-space: nowrap;
}}

/* ── Main ── */
main {{ max-width: 1000px; margin: 0 auto; padding: 28px 16px; }}

/* Week pills navigation */
.week-nav {{
  display: flex;
  gap: 8px;
  margin-bottom: 24px;
  flex-wrap: wrap;
}}
.week-pill {{
  padding: 8px 20px;
  border-radius: var(--pill);
  font-size: 0.8rem;
  font-weight: 700;
  cursor: pointer;
  border: 2px solid transparent;
  transition: all .2s;
  display: flex;
  align-items: center;
  gap: 6px;
}}
.week-pill.tw  {{ background: var(--amber); color: #fff; }}
.week-pill.lw  {{ background: var(--dark); color: var(--orange); }}
.week-pill.old {{ background: var(--cream2); color: var(--gray); border-color: var(--border); }}
.week-pill:hover {{ opacity: 0.85; transform: translateY(-1px); }}

/* Timeline sections */
.section-label {{
  font-size: 0.68rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: var(--gray);
  margin-bottom: 12px;
  padding-left: 2px;
  display: flex;
  align-items: center;
  gap: 8px;
}}
.section-label::after {{
  content: '';
  flex: 1;
  height: 1px;
  background: var(--border);
}}

.week-section {{ margin-bottom: 32px; }}
.week-header {{
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
}}
.week-title {{
  font-size: 1.05rem;
  font-weight: 800;
  color: var(--dark);
}}
.week-sub {{
  font-size: 0.78rem;
  color: var(--gray);
}}
.month-group {{ margin-bottom: 12px; }}
.month-label {{
  font-size: 0.72rem;
  font-weight: 700;
  color: var(--amber);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 8px;
  padding-left: 2px;
}}

/* Run cards */
.run-card {{
  background: var(--white);
  border: 1.5px solid var(--border);
  border-radius: var(--r-card);
  margin-bottom: 10px;
  overflow: hidden;
  transition: box-shadow .2s, transform .2s;
}}
.run-card:hover {{ box-shadow: 0 4px 20px rgba(26,17,8,0.08); transform: translateY(-1px); }}
.run-header {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  cursor: pointer;
  gap: 8px;
}}
.run-header:hover {{ background: var(--cream); }}
.run-date {{ font-weight: 700; font-size: 0.9rem; color: var(--dark); }}
.run-exec {{ font-size: 0.75rem; color: var(--gray); margin-left: 4px; }}
.run-badges {{ display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }}
.badge {{
  font-size: 0.7rem;
  font-weight: 700;
  padding: 3px 10px;
  border-radius: var(--pill);
  white-space: nowrap;
}}
.badge-latest  {{ background: linear-gradient(135deg, var(--red), var(--orange)); color: #fff; }}
.badge-count   {{ background: var(--cream2); color: var(--amber); border: 1px solid var(--border); }}
.chevron {{ font-size: 0.7rem; color: var(--gray); transition: transform .2s; margin-left: 4px; }}
.run-card.open .chevron {{ transform: rotate(180deg); }}

/* Jobs table */
.jobs-panel {{ display: none; border-top: 1.5px solid var(--border); }}
.run-card.open .jobs-panel {{ display: block; }}
.jobs-panel table {{ width: 100%; border-collapse: collapse; font-size: 0.82rem; }}
.jobs-panel th {{
  background: var(--cream);
  text-align: left;
  padding: 9px 16px;
  font-size: 0.68rem;
  color: var(--gray);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  font-weight: 700;
}}
.jobs-panel td {{ padding: 9px 16px; border-top: 1px solid var(--border); vertical-align: middle; }}
.jobs-panel tr:hover td {{ background: #FDFAF5; }}
.co {{ font-weight: 700; color: var(--navy); }}
.role-text {{ color: var(--dark); }}
.ats-tag {{
  display: inline-block;
  font-size: 0.68rem;
  padding: 2px 9px;
  border-radius: var(--pill);
  background: var(--cream2);
  color: var(--amber);
  font-weight: 600;
  border: 1px solid var(--border);
  white-space: nowrap;
}}
a.apply-btn {{
  display: inline-block;
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--amber);
  text-decoration: none;
  border: 1.5px solid var(--amber);
  border-radius: var(--pill);
  padding: 3px 12px;
  white-space: nowrap;
  transition: all .15s;
}}
a.apply-btn:hover {{ background: var(--amber); color: #fff; }}

.empty {{ text-align: center; padding: 56px 16px; color: var(--gray); font-size: 0.9rem; }}

/* Footer */
footer {{
  border-top: 1px solid var(--border);
  padding: 24px 32px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 0.75rem;
  color: var(--gray);
  background: var(--white);
}}
footer a {{ color: var(--amber); text-decoration: none; font-weight: 600; }}
footer a:hover {{ text-decoration: underline; }}
</style>
</head>
<body>

<header>
  <div class="header-brand">
    <div class="mc-logo">
      <div class="c1"></div>
      <div class="c2"></div>
      <div class="c-overlap"></div>
    </div>
    <div class="brand-text">
      <h1>PM Jobs Internacional</h1>
      <p>curated by Felipe Saraiva · AI Product Builder</p>
    </div>
  </div>
  <div class="header-right">
    <div class="stat-pill"><div class="num" id="vis-count">{total_jobs}</div><div class="lbl">vagas</div></div>
    <div class="stat-pill"><div class="num">{total_runs}</div><div class="lbl">execuções</div></div>
    <div class="stat-pill"><div class="num">{latest_count}</div><div class="lbl">hoje</div></div>
    <a class="personal-link" href="https://felipesaraiva.com" target="_blank" rel="noopener">
      ↗ felipesaraiva.com
    </a>
  </div>
</header>

<div class="controls">
  <div class="search-wrap">
    <input type="text" id="search" placeholder="Buscar empresa, cargo…" oninput="applyFilter()">
  </div>
  <select class="ctl-select" id="sel-year"  onchange="applyFilter()"><option value="">Todos os anos</option></select>
  <select class="ctl-select" id="sel-month" onchange="applyFilter()"><option value="">Todos os meses</option></select>
  <select class="ctl-select" id="sel-ats"   onchange="applyFilter()"><option value="">Todas as plataformas</option></select>
  <label class="toggle-new" id="toggle-new-label">
    <input type="checkbox" id="only-new" onchange="this.closest('.toggle-new').classList.toggle('active',this.checked);applyFilter()">
    ✨ Só novas
  </label>
  <span class="count-pill" id="count-lbl">{total_jobs} vagas</span>
</div>

<main>
  <div class="week-nav" id="week-nav"></div>
  <div id="content"></div>
</main>

<footer>
  <span>Atualizado em {now_str} · {total_jobs} vagas · {total_runs} execuções</span>
  <span>Criado por <a href="https://felipesaraiva.com" target="_blank">Felipe Saraiva</a> · <a href="https://github.com/cync/vagas-pm" target="_blank">GitHub</a></span>
</footer>

<script>
const ALL_JOBS = {jobs_json};
const RUNS     = {runs_json};

// ── Populate selects ──
const years  = [...new Set(ALL_JOBS.map(j=>j.date.slice(0,4)))].sort().reverse();
const months = [...new Set(ALL_JOBS.map(j=>{{const d=new Date(j.date+'T12:00:00');return d.toLocaleString('en',{{month:'long'}})+' '+j.date.slice(0,4)}}))].sort((a,b)=>new Date('01 '+b)-new Date('01 '+a));
const atsList= [...new Set(ALL_JOBS.map(j=>j.ats))].sort();

const selYear  = document.getElementById('sel-year');
const selMonth = document.getElementById('sel-month');
const selAts   = document.getElementById('sel-ats');

years.forEach(y => selYear.innerHTML  += `<option>${{y}}</option>`);
months.forEach(m=> selMonth.innerHTML += `<option>${{m}}</option>`);
atsList.forEach(a=> selAts.innerHTML  += `<option>${{a}}</option>`);

// ── Week helpers ──
function weekStart(dateStr) {{
  const d = new Date(dateStr + 'T12:00:00');
  const day = d.getDay() || 7;
  d.setDate(d.getDate() - (day - 1));
  return d.toISOString().slice(0,10);
}}

const today   = new Date().toISOString().slice(0,10);
const thisWeekStart = weekStart(today);
const lwDate  = new Date(thisWeekStart + 'T12:00:00');
lwDate.setDate(lwDate.getDate() - 7);
const lastWeekStart = lwDate.toISOString().slice(0,10);

function weekBucket(dateStr) {{
  const ws = weekStart(dateStr);
  if (ws === thisWeekStart) return 'this_week';
  if (ws === lastWeekStart) return 'last_week';
  return 'earlier';
}}

function fmtDate(s) {{
  const mo = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const [y,m,d] = s.split('-');
  return `${{parseInt(d)}} ${{mo[parseInt(m)-1]}} ${{y}}`;
}}
function fmtWeekRange(startStr) {{
  const s = new Date(startStr+'T12:00:00');
  const e = new Date(startStr+'T12:00:00');
  e.setDate(e.getDate()+6);
  const mo = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  return `${{s.getDate()}} ${{mo[s.getMonth()]}} – ${{e.getDate()}} ${{mo[e.getMonth()]}}`;
}}

// ── Filter ──
let activeWeek = null;

function applyFilter() {{
  const q       = document.getElementById('search').value.toLowerCase();
  const year    = selYear.value;
  const month   = selMonth.value;
  const ats     = selAts.value;
  const onlyNew = document.getElementById('only-new').checked;

  const vis = ALL_JOBS.filter(j => {{
    if (onlyNew && !j.is_latest) return false;
    if (year  && !j.date.startsWith(year))  return false;
    if (ats   && j.ats !== ats)             return false;
    if (month) {{
      const d = new Date(j.date+'T12:00:00');
      const jm = d.toLocaleString('en',{{month:'long'}})+' '+j.date.slice(0,4);
      if (jm !== month) return false;
    }}
    if (activeWeek && weekBucket(j.date) !== activeWeek) return false;
    if (q) {{
      if (!(j.company+' '+j.role+' '+j.ats).toLowerCase().includes(q)) return false;
    }}
    return true;
  }});

  document.getElementById('vis-count').textContent = vis.length;
  document.getElementById('count-lbl').textContent  = vis.length + ' vagas';

  // Map file → visible jobs
  const runMap = {{}};
  vis.forEach(j => {{
    if (!runMap[j.file]) runMap[j.file] = [];
    runMap[j.file].push(j);
  }});

  // Bucket runs
  const buckets = {{ this_week: [], last_week: [], earlier: [] }};
  RUNS.forEach(run => {{
    const jobs = runMap[run.file];
    if (!jobs || jobs.length === 0) return;
    const b = (activeWeek && activeWeek !== 'all') ? activeWeek : weekBucket(run.date);
    const bucket = buckets[b] || buckets.earlier;
    bucket.push({{...run, visJobs: jobs}});
  }});

  // ── Render week nav ──
  const tweekCount = ALL_JOBS.filter(j=>weekBucket(j.date)==='this_week').length;
  const lweekCount = ALL_JOBS.filter(j=>weekBucket(j.date)==='last_week').length;
  const olderCount = ALL_JOBS.filter(j=>weekBucket(j.date)==='earlier').length;

  const nav = document.getElementById('week-nav');
  nav.innerHTML = `
    <button class="week-pill tw ${{activeWeek==='this_week'?'active':''}}" onclick="setWeek('this_week')">
      🟠 Esta semana <span style="opacity:.8;font-size:.7rem">(${{tweekCount}})</span>
    </button>
    <button class="week-pill lw ${{activeWeek==='last_week'?'active':''}}" onclick="setWeek('last_week')">
      ◑ Semana passada <span style="opacity:.8;font-size:.7rem">(${{lweekCount}})</span>
    </button>
    <button class="week-pill old ${{activeWeek==='earlier'?'active':''}}" onclick="setWeek('earlier')">
      📅 Anteriores <span style="opacity:.8;font-size:.7rem">(${{olderCount}})</span>
    </button>
    ${{activeWeek ? '<button class="week-pill old" onclick="setWeek(null)" style="background:#fff">✕ Ver tudo</button>' : ''}}
  `;

  // ── Render content ──
  const bucketLabels = {{
    this_week: {{ title: '🟠 Esta Semana', sub: fmtWeekRange(thisWeekStart) }},
    last_week: {{ title: '◑ Semana Passada', sub: fmtWeekRange(lastWeekStart) }},
    earlier:   {{ title: '📅 Execuções Anteriores', sub: '' }},
  }};

  const orderedBuckets = activeWeek ? [activeWeek] : ['this_week','last_week','earlier'];

  let html = '';
  orderedBuckets.forEach(bkey => {{
    const bRuns = buckets[bkey];
    if (!bRuns || bRuns.length === 0) return;
    bRuns.sort((a,b) => b.date.localeCompare(a.date));
    const info = bucketLabels[bkey];

    // Group by month for "earlier"
    if (bkey === 'earlier') {{
      html += `<div class="week-section">
        <div class="week-header">
          <span class="week-title">${{info.title}}</span>
        </div>`;
      const byMonth = {{}};
      bRuns.forEach(r => {{
        const d = new Date(r.date+'T12:00:00');
        const mk = d.toLocaleString('en',{{month:'long'}})+' '+r.date.slice(0,4);
        if (!byMonth[mk]) byMonth[mk]=[];
        byMonth[mk].push(r);
      }});
      Object.keys(byMonth).sort((a,b)=>new Date('01 '+b)-new Date('01 '+a)).forEach(mk => {{
        html += `<div class="month-group"><div class="month-label">${{mk}}</div>`;
        byMonth[mk].forEach(run => {{ html += renderCard(run); }});
        html += '</div>';
      }});
      html += '</div>';
    }} else {{
      html += `<div class="week-section">
        <div class="week-header">
          <span class="week-title">${{info.title}}</span>
          ${{info.sub ? `<span class="week-sub">${{info.sub}}</span>` : ''}}
        </div>`;
      bRuns.forEach(run => {{ html += renderCard(run); }});
      html += '</div>';
    }}
  }});

  if (!html) html = '<div class="empty">Nenhuma vaga encontrada para os filtros selecionados.</div>';
  document.getElementById('content').innerHTML = html;

  // Auto-open latest
  const latest = RUNS.filter(r=>r.is_latest)[0];
  if (latest && runMap[latest.file]) {{
    const card = document.getElementById('card-'+latest.file.replace(/\\./g,'_'));
    if (card) card.classList.add('open');
  }}
}}

function renderCard(run) {{
  const id = run.file.replace(/\\./g,'_');
  const rows = run.visJobs.map(j => `
    <tr>
      <td><div class="co">${{j.company}}</div></td>
      <td><div class="role-text">${{j.role}}</div></td>
      <td><span class="ats-tag">${{j.ats}}</span></td>
      <td><a class="apply-btn" href="${{j.url}}" target="_blank" rel="noopener">Ver vaga ↗</a></td>
    </tr>`).join('');
  const latestBadge = run.is_latest ? '<span class="badge badge-latest">✨ mais recente</span>' : '';
  return `
  <div class="run-card" id="card-${{id}}">
    <div class="run-header" onclick="toggle('${{id}}')">
      <div>
        <span class="run-date">${{fmtDate(run.date)}}</span>
        <span class="run-exec">· exec ${{run.exec}}</span>
      </div>
      <div class="run-badges">
        ${{latestBadge}}
        <span class="badge badge-count">${{run.visJobs.length}} vagas</span>
        <span class="chevron">▼</span>
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

function setWeek(w) {{
  activeWeek = w;
  applyFilter();
}}

function toggle(id) {{
  document.getElementById('card-'+id)?.classList.toggle('open');
}}

// Init
applyFilter();
</script>
</body>
</html>"""

out = SITE_DIR / "index.html"
out.write_text(html, encoding="utf-8")
print(f"OK — {total_runs} execuções · {total_jobs} vagas")
