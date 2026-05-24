#!/usr/bin/env python3
"""
Gerador do site de vagas PM internacionais.
Lê todos os arquivos vagas_pm_*.md e gera index.html com timeline por data.
"""
import os, re, json
from datetime import datetime, timedelta
from pathlib import Path

VAGAS_DIR = Path(__file__).parent.parent  # VagasInternacionais/
SITE_DIR  = Path(__file__).parent         # VagasInternacionais/site/

# ──────────────────────────────────────────────
# 1. Parse markdown files
# ──────────────────────────────────────────────
def parse_md_file(filepath):
    text = filepath.read_text(encoding="utf-8")
    
    # Extract date from filename: vagas_pm_YYYY-MM-DD[_exec2].md
    m = re.search(r'vagas_pm_(\d{4}-\d{2}-\d{2})', filepath.name)
    if not m:
        return None
    date_str = m.group(1)
    exec_n   = "2" if "_exec2" in filepath.name else "1"
    
    # Extract count line
    novas_m = re.search(r'Novas encontradas\*\*:\s*(\d+)', text)
    novas   = int(novas_m.group(1)) if novas_m else 0

    # Determine if this is the LATEST file (for "new" badge)
    is_latest = False  # filled later

    # Extract jobs from table rows: | **Company** | Role | [Ver vaga](url) |
    jobs = []
    # Current ATS platform being parsed
    current_ats = "Outros"
    for line in text.splitlines():
        # Section headers like "### 🔷 Lever"
        header_m = re.match(r'^###\s+[^\s]+\s+(.+)', line)
        if header_m:
            current_ats = header_m.group(1).strip()
            continue
        # Table row
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
    
    return {
        "date":   date_str,
        "exec":   exec_n,
        "file":   filepath.name,
        "novas":  novas,
        "jobs":   jobs,
    }

# ──────────────────────────────────────────────
# 2. Load all data
# ──────────────────────────────────────────────
md_files = sorted(VAGAS_DIR.glob("vagas_pm_*.md"))
runs = []
for f in md_files:
    result = parse_md_file(f)
    if result:
        runs.append(result)

# Mark latest run
if runs:
    runs[-1]["is_latest"] = True
    latest_date = runs[-1]["date"]
else:
    latest_date = ""

# Flatten all jobs
all_jobs = []
for run in runs:
    is_latest = run.get("is_latest", False)
    for j in run["jobs"]:
        j["is_latest"] = is_latest
        all_jobs.append(j)

# Group by year → month → day
from collections import defaultdict
by_year = defaultdict(lambda: defaultdict(list))
for run in runs:
    dt = datetime.strptime(run["date"], "%Y-%m-%d")
    year  = str(dt.year)
    month = dt.strftime("%B %Y")   # e.g. "May 2026"
    by_year[year][month].append(run)

total_jobs = len(all_jobs)
latest_count = runs[-1]["novas"] if runs else 0
total_runs   = len(runs)

# ──────────────────────────────────────────────
# 3. Generate HTML
# ──────────────────────────────────────────────
def esc(s):
    return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"','&quot;')

# Build JS data blob
jobs_json = json.dumps(all_jobs, ensure_ascii=False)

html_parts = []

html_parts.append(f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Vagas PM Internacional · @cync</title>
<style>
  :root {{
    --navy:  #1a2e4a;
    --blue:  #2563eb;
    --lblue: #eff6ff;
    --green: #16a34a;
    --lgreen:#dcfce7;
    --gray:  #64748b;
    --lgray: #f1f5f9;
    --border:#e2e8f0;
    --white: #ffffff;
    --text:  #1e293b;
    --badge: #f59e0b;
    --lbadge:#fef3c7;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: var(--lgray); color: var(--text); }}
  
  header {{ background: var(--navy); color: white; padding: 20px 32px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; }}
  header h1 {{ font-size: 1.3rem; font-weight: 700; letter-spacing: -0.3px; }}
  header h1 span {{ color: #60a5fa; }}
  .stats {{ display: flex; gap: 24px; }}
  .stat {{ text-align: center; }}
  .stat-num {{ font-size: 1.5rem; font-weight: 800; color: #60a5fa; }}
  .stat-lbl {{ font-size: 0.7rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px; }}

  .controls {{ background: white; border-bottom: 1px solid var(--border); padding: 12px 32px; display: flex; gap: 12px; flex-wrap: wrap; align-items: center; position: sticky; top: 0; z-index: 100; box-shadow: 0 1px 4px rgba(0,0,0,.06); }}
  .controls input {{ flex: 1; min-width: 180px; padding: 7px 12px; border: 1px solid var(--border); border-radius: 6px; font-size: 0.875rem; }}
  .controls select {{ padding: 7px 12px; border: 1px solid var(--border); border-radius: 6px; font-size: 0.875rem; background: white; cursor: pointer; }}
  .controls label {{ font-size: 0.8rem; color: var(--gray); display: flex; align-items: center; gap: 6px; cursor: pointer; }}
  .count-badge {{ background: var(--lblue); color: var(--blue); font-size: 0.75rem; font-weight: 600; padding: 2px 8px; border-radius: 999px; }}

  main {{ max-width: 960px; margin: 0 auto; padding: 24px 16px; }}

  .year-block {{ margin-bottom: 32px; }}
  .year-label {{ font-size: 1.1rem; font-weight: 800; color: var(--navy); padding: 6px 0; border-bottom: 2px solid var(--blue); margin-bottom: 16px; }}

  .month-block {{ margin-bottom: 20px; }}
  .month-label {{ font-size: 0.8rem; font-weight: 700; color: var(--blue); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 10px; padding-left: 4px; }}

  .run-card {{ background: white; border: 1px solid var(--border); border-radius: 10px; margin-bottom: 12px; overflow: hidden; }}
  .run-header {{ display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; cursor: pointer; gap: 8px; }}
  .run-header:hover {{ background: var(--lgray); }}
  .run-date {{ font-weight: 700; font-size: 0.925rem; color: var(--navy); }}
  .run-meta {{ font-size: 0.8rem; color: var(--gray); }}
  .run-badges {{ display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }}
  .badge {{ font-size: 0.72rem; font-weight: 600; padding: 2px 8px; border-radius: 999px; white-space: nowrap; }}
  .badge-new  {{ background: var(--lbadge); color: #92400e; border: 1px solid #fcd34d; }}
  .badge-count{{ background: var(--lgreen); color: var(--green); }}
  .chevron {{ font-size: 0.75rem; color: var(--gray); transition: transform .2s; }}
  .run-card.open .chevron {{ transform: rotate(180deg); }}

  .jobs-table {{ display: none; border-top: 1px solid var(--border); }}
  .run-card.open .jobs-table {{ display: block; }}
  
  .jobs-table table {{ width: 100%; border-collapse: collapse; font-size: 0.82rem; }}
  .jobs-table th {{ background: var(--lgray); text-align: left; padding: 8px 12px; font-size: 0.72rem; color: var(--gray); text-transform: uppercase; letter-spacing: 0.4px; font-weight: 600; }}
  .jobs-table td {{ padding: 8px 12px; border-top: 1px solid var(--border); vertical-align: top; }}
  .jobs-table tr:hover td {{ background: #f8fafc; }}
  .company {{ font-weight: 600; color: var(--navy); }}
  .role    {{ color: var(--text); }}
  .ats-tag {{ display: inline-block; font-size: 0.68rem; padding: 1px 6px; border-radius: 4px; background: var(--lblue); color: var(--blue); font-weight: 500; white-space: nowrap; }}
  a.apply  {{ display: inline-block; font-size: 0.75rem; font-weight: 600; color: var(--blue); text-decoration: none; border: 1px solid var(--blue); border-radius: 5px; padding: 2px 10px; white-space: nowrap; }}
  a.apply:hover {{ background: var(--blue); color: white; }}

  .no-results {{ text-align: center; padding: 48px 16px; color: var(--gray); }}

  footer {{ text-align: center; padding: 24px; font-size: 0.75rem; color: var(--gray); }}
</style>
</head>
<body>

<header>
  <h1>Vagas <span>PM Internacional</span></h1>
  <div class="stats">
    <div class="stat"><div class="stat-num" id="vis-count">{total_jobs}</div><div class="stat-lbl">vagas</div></div>
    <div class="stat"><div class="stat-num">{total_runs}</div><div class="stat-lbl">execuções</div></div>
    <div class="stat"><div class="stat-num">{latest_count}</div><div class="stat-lbl">última busca</div></div>
  </div>
</header>

<div class="controls">
  <input type="text" id="search" placeholder="🔍  Buscar empresa, cargo…" oninput="filter()">
  <select id="sel-year" onchange="filter()"><option value="">Todos os anos</option></select>
  <select id="sel-ats"  onchange="filter()"><option value="">Todas as plataformas</option></select>
  <label><input type="checkbox" id="only-new" onchange="filter()"> Só novas <span class="badge badge-new">✨ novo</span></label>
  <span class="count-badge" id="count-lbl">{total_jobs} vagas</span>
</div>

<main id="main-content"></main>

<footer>Atualizado em {datetime.now().strftime("%d/%m/%Y %H:%M")} · {total_jobs} vagas · {total_runs} execuções</footer>

<script>
const ALL_JOBS = {jobs_json};
const RUNS = {json.dumps(runs, ensure_ascii=False)};

// Populate selects
const years  = [...new Set(ALL_JOBS.map(j=>j.date.slice(0,4)))].sort().reverse();
const atsList = [...new Set(ALL_JOBS.map(j=>j.ats))].sort();
const selYear = document.getElementById('sel-year');
const selAts  = document.getElementById('sel-ats');
years.forEach(y  => selYear.innerHTML += `<option>${{y}}</option>`);
atsList.forEach(a => selAts.innerHTML  += `<option>${{a}}</option>`);

function getFilters() {{
  return {{
    q:       document.getElementById('search').value.toLowerCase(),
    year:    selYear.value,
    ats:     selAts.value,
    onlyNew: document.getElementById('only-new').checked,
  }};
}}

function matchJob(j, f) {{
  if (f.onlyNew && !j.is_latest) return false;
  if (f.year && !j.date.startsWith(f.year)) return false;
  if (f.ats  && j.ats !== f.ats) return false;
  if (f.q) {{
    const hay = (j.company+' '+j.role+' '+j.ats).toLowerCase();
    if (!hay.includes(f.q)) return false;
  }}
  return true;
}}

function weekOf(dateStr) {{
  const d = new Date(dateStr + 'T12:00:00');
  const day = d.getDay(); // 0=Sun
  const diff = d.getDate() - day + (day === 0 ? -6 : 1);
  const mon = new Date(d.setDate(diff));
  return mon.toISOString().slice(0,10);
}}

function fmt(dateStr) {{
  const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const [y,m,d] = dateStr.split('-');
  return `${{parseInt(d)}} ${{months[parseInt(m)-1]}} ${{y}}`;
}}

function filter() {{
  const f   = getFilters();
  const vis = ALL_JOBS.filter(j => matchJob(j, f));
  document.getElementById('vis-count').textContent = vis.length;
  document.getElementById('count-lbl').textContent  = vis.length + ' vagas';

  // Group visible jobs by run file
  const runMap = {{}};
  vis.forEach(j => {{
    if (!runMap[j.file]) runMap[j.file] = [];
    runMap[j.file].push(j);
  }});

  // Group runs by year → month
  const byYear = {{}};
  RUNS.forEach(run => {{
    const jobs = runMap[run.file];
    if (!jobs || jobs.length === 0) return;
    const y = run.date.slice(0,4);
    const dt = new Date(run.date + 'T12:00:00');
    const monthKey = dt.toLocaleString('en',{{month:'long'}}) + ' ' + y;
    if (!byYear[y]) byYear[y] = {{}};
    if (!byYear[y][monthKey]) byYear[y][monthKey] = [];
    byYear[y][monthKey].push({{...run, visJobs: jobs}});
  }});

  const main = document.getElementById('main-content');
  if (Object.keys(byYear).length === 0) {{
    main.innerHTML = '<div class="no-results">Nenhuma vaga encontrada para os filtros selecionados.</div>';
    return;
  }}

  let html = '';
  Object.keys(byYear).sort().reverse().forEach(year => {{
    html += `<div class="year-block"><div class="year-label">📅 ${{year}}</div>`;
    const months = byYear[year];
    Object.keys(months).sort((a,b) => new Date('01 '+b) - new Date('01 '+a)).forEach(month => {{
      html += `<div class="month-block"><div class="month-label">${{month}}</div>`;
      months[month].sort((a,b) => b.date.localeCompare(a.date)).forEach(run => {{
        const runId = run.file.replace(/\./g,'_');
        const isNew = run.is_latest;
        const jobRows = run.visJobs.map(j => `
          <tr>
            <td><div class="company">${{j.company}}</div></td>
            <td><div class="role">${{j.role}}</div></td>
            <td><span class="ats-tag">${{j.ats}}</span></td>
            <td><a class="apply" href="${{j.url}}" target="_blank" rel="noopener">Ver vaga ↗</a></td>
          </tr>`).join('');
        html += `
        <div class="run-card" id="card-${{runId}}">
          <div class="run-header" onclick="toggle('${{runId}}')">
            <div>
              <span class="run-date">${{fmt(run.date)}}</span>
              <span class="run-meta"> · execução ${{run.exec}}</span>
            </div>
            <div class="run-badges">
              ${{isNew ? '<span class="badge badge-new">✨ mais recente</span>' : ''}}
              <span class="badge badge-count">${{run.visJobs.length}} vagas</span>
              <span class="chevron">▼</span>
            </div>
          </div>
          <div class="jobs-table">
            <table>
              <thead><tr><th>Empresa</th><th>Cargo</th><th>Plataforma</th><th>Link</th></tr></thead>
              <tbody>${{jobRows}}</tbody>
            </table>
          </div>
        </div>`;
      }});
      html += '</div>';
    }});
    html += '</div>';
  }});
  main.innerHTML = html;

  // Auto-open latest run
  if (f.onlyNew || (!f.q && !f.year && !f.ats)) {{
    const latestRun = RUNS.filter(r=>r.is_latest)[0];
    if (latestRun) {{
      const id = latestRun.file.replace(/\./g,'_');
      const card = document.getElementById('card-'+id);
      if (card) card.classList.add('open');
    }}
  }}
}}

function toggle(id) {{
  document.getElementById('card-'+id)?.classList.toggle('open');
}}

// Init
filter();
</script>
</body>
</html>
""")

# Write the file
out = SITE_DIR / "index.html"
out.write_text(''.join(html_parts), encoding="utf-8")
print(f"Site gerado: {out}")
print(f"Total de execuções: {total_runs}")
print(f"Total de vagas: {total_jobs}")
