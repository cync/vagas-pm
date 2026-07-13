#!/usr/bin/env python3
"""
link_checker.py -- Módulo compartilhado de validação de links de vagas.
Usado por: generate_site.py, search_and_generate.py, check_links.py, clean_ashby.py.

Fornece:
  - get_url_status(url)        -> "open" | "dead" | "unknown"
  - is_dead_url(url)           -> bool (checagem individual)
  - check_urls_parallel_status(urls) -> dict {url: status} (checagem em lote)
  - check_urls_parallel(urls)  -> dict {url: bool} (compatibilidade)
  - normalize_url(url)         -> str  (normalização de URL)
  - is_specific_job_url(url)   -> bool (rejeita páginas de empresa)
  - BrokenCache                -> classe para ler/escritar broken_links.json
"""
import json
import re
import urllib.request
import urllib.error
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# ── Configuração ──────────────────────────────────────────────────────────────

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

MANUALLY_BLOCKED_URLS = {
    "https://jobs.lever.co/RyzLabs/6a182574-db22-48ca-8a17-7e66d14da5b5",
    "https://jobs.lever.co/oowlish/da056da7-5079-42cb-ab46-d7babc2dd8e1",
}

VALIDATION_POLICY_VERSION = 2

DEAD_PHRASES = [
    "the job you requested was not found",
    "job not found",
    "job posting not found",
    "position not found",
    "this job is no longer available",
    "this job listing is no longer active",
    "no longer accepting applications",
    "position has been filled",
    "job has expired",
    "this position is no longer available",
    "application is not available",
    "this role is no longer",
    "opening has been filled",
    "page not found",
    "404 not found",
    "this posting has been closed",
    "application is closed",
    "position is no longer accepting",
    "this role has been filled",
    "no longer available",
    "job listing has expired",
    "this requisition is closed",
    "we are no longer accepting",
    "the page you're looking for",
    "this job opening has been closed",
    "sorry, we couldn't find anything here",
    "couldn't find anything here",
    "vaga nao encontrada",
    "this position has been closed",
    "position closed",
    "this job posting is no longer available",
]

DEAD_URL_PATTERNS = ["/404", "?error=true", "job-not-found", "posting-not-found"]

_ASHBY_UUID_RE = re.compile(
    r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}", re.I
)
_GH_JOB_RE = re.compile(r"greenhouse\.io/([^/]+)/jobs/(\d+)", re.I)
_LEVER_JOB_RE = re.compile(r"lever\.co/([^/]+)/([A-Za-z0-9-]+)", re.I)

POSITIVE_JOB_MARKERS = [
    '"@type":"jobposting"',
    '"@type": "jobposting"',
    "schema.org/jobposting",
    "apply for this job",
    "apply for this position",
    "job description",
    "employmenttype",
    "dateposted",
    "validthrough",
]

PROVIDER_POSITIVE_MARKERS = {
    "ashby": ["applicationform", "ashbyhq"],
    "greenhouse": ["grnhse_app", "opening-header"],
    "lever": ["posting-categories", "lever-job-container", '"categories"'],
    "workable": ["apply for this job", "workable"],
    "teamtailor": ["teamtailor", "department"],
    "recruitee": ["recruitee", "department", "job description"],
    "weworkremotely": ["we work remotely", "apply for this position"],
    "remotive": ["candidate_required_location", "remotive"],
    "himalayas": ["himalayas", "years of experience"],
    "wellfound": ["wellfound", "apply", "full-time"],
}


# ── URL normalization ─────────────────────────────────────────────────────────

def normalize_url(url: str) -> str:
    """Normaliza URL para comparação consistente.
    - http:// -> https:// para ATS conhecidos
    - Remove trailing slash
    - Strip whitespace
    """
    url = url.strip()
    if url.startswith("http://") and any(
        d in url for d in ("greenhouse.io", "lever.co", "ashbyhq.com",
                           "smartrecruiters.com", "weworkremotely.com",
                           "remotive.com", "himalayas.app")
    ):
        url = "https://" + url[7:]
    return url.rstrip("/")


def _detect_provider(url: str) -> str:
    url = normalize_url(url).lower()
    if "ashbyhq.com" in url:
        return "ashby"
    if "greenhouse.io" in url:
        return "greenhouse"
    if "lever.co" in url:
        return "lever"
    if "workable.com" in url:
        return "workable"
    if "teamtailor.com" in url:
        return "teamtailor"
    if "recruitee.com" in url:
        return "recruitee"
    if "weworkremotely.com" in url:
        return "weworkremotely"
    if "remotive.com" in url:
        return "remotive"
    if "himalayas.app" in url:
        return "himalayas"
    if "wellfound.com" in url:
        return "wellfound"
    return "other"


def is_manually_blocked_url(url: str) -> bool:
    return normalize_url(url) in {normalize_url(u) for u in MANUALLY_BLOCKED_URLS}


# ── Ashby API check ───────────────────────────────────────────────────────────

def _status_ashby(url: str) -> str:
    uuid_m = _ASHBY_UUID_RE.search(url)
    if not uuid_m:
        return "dead"
    comp_m = re.search(r"ashbyhq\.com/([^/]+)", url)
    if not comp_m:
        return "dead"
    company_raw = urllib.parse.unquote(comp_m.group(1))
    company = urllib.parse.quote(company_raw, safe="")
    job_id = uuid_m.group(0)
    api = f"https://api.ashbyhq.com/posting-api/job-board/{company}?ashby_source=job_board&limit=500"
    try:
        req = urllib.request.Request(api, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            jobs = data.get("jobs", [])
            if not jobs:
                return "dead"
            return "open" if any(j.get("id") == job_id for j in jobs) else "dead"
    except urllib.error.HTTPError as e:
        return "dead" if e.code in (404, 410) else "unknown"
    except Exception:
        return "unknown"


# ── Greenhouse API check ──────────────────────────────────────────────────────

def _status_greenhouse_api(url: str) -> str:
    gh_m = _GH_JOB_RE.search(url)
    if not gh_m:
        return "dead"
    company, job_id = gh_m.group(1), gh_m.group(2)
    api = f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs/{job_id}"
    try:
        req = urllib.request.Request(api, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            return "open" if data.get("id") else "dead"
    except urllib.error.HTTPError as e:
        return "dead" if e.code in (404, 410) else "unknown"
    except Exception:
        return "unknown"


def _status_lever_api(url: str) -> str:
    lm = _LEVER_JOB_RE.search(url)
    if not lm:
        return "dead"
    company, job_id = lm.group(1), lm.group(2)
    api = f"https://api.lever.co/v0/postings/{company}/{job_id}?mode=json"
    try:
        req = urllib.request.Request(api, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            return "open" if data.get("id") or data.get("text") else "dead"
    except urllib.error.HTTPError as e:
        return "dead" if e.code in (404, 410) else "unknown"
    except Exception:
        return "unknown"


# ── HTTP body/redirect check ──────────────────────────────────────────────────

def _fetch_http(url: str, max_bytes: int = 200_000) -> dict | None:
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=12) as resp:
            return {
                "status": getattr(resp, "status", 200),
                "final_url": resp.geturl(),
                "body": resp.read(max_bytes).decode("utf-8", errors="ignore"),
            }
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read(max_bytes).decode("utf-8", errors="ignore")
        except Exception:
            pass
        return {
            "status": e.code,
            "final_url": getattr(e, "url", url),
            "body": body,
        }
    except Exception:
        return None


def _body_confirms_open(body_lower: str, provider: str) -> bool:
    if any(marker in body_lower for marker in POSITIVE_JOB_MARKERS):
        return True
    return any(marker in body_lower for marker in PROVIDER_POSITIVE_MARKERS.get(provider, []))


def _status_http(url: str) -> str:
    response = _fetch_http(url)
    if response is None:
        return "unknown"

    status = response["status"]
    final_url = normalize_url(response["final_url"])
    body_lower = response["body"].lower()
    provider = _detect_provider(url)

    if status in (404, 410):
        return "dead"
    if any(pattern in final_url.lower() for pattern in DEAD_URL_PATTERNS):
        return "dead"
    if any(phrase in body_lower for phrase in DEAD_PHRASES):
        return "dead"
    if normalize_url(url) != final_url and not is_specific_job_url(final_url):
        return "dead"
    if _body_confirms_open(body_lower, provider):
        return "open"
    return "unknown"


# ── API pública ────────────────────────────────────────────────────────────────

def get_url_status(url: str) -> str:
    """Retorna o status do link da vaga: open, dead ou unknown.
    O site deve publicar apenas links com status open."""
    normalized = normalize_url(url)
    if is_manually_blocked_url(normalized):
        return "dead"
    provider = _detect_provider(normalized)

    if provider == "ashby":
        status = _status_ashby(normalized)
        return status if status != "unknown" else _status_http(normalized)
    if provider == "greenhouse":
        status = _status_greenhouse_api(normalized)
        return status if status != "unknown" else _status_http(normalized)
    if provider == "lever":
        status = _status_lever_api(normalized)
        return status if status != "unknown" else _status_http(normalized)
    return _status_http(normalized)


def is_dead_url(url: str) -> bool:
    return get_url_status(url) == "dead"


def check_urls_parallel_status(urls: list[str], max_workers: int = 15) -> dict[str, str]:
    """Checa URLs em paralelo. Retorna {url: open|dead|unknown}."""
    results = {}
    if not urls:
        return results
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(get_url_status, u): u for u in urls}
        for future in as_completed(futures):
            u = futures[future]
            try:
                results[u] = future.result()
            except Exception:
                results[u] = "unknown"
    return results


def check_urls_parallel(urls: list[str], max_workers: int = 15) -> dict[str, bool]:
    """Compatibilidade: retorna {url: is_dead}."""
    return {u: status == "dead" for u, status in check_urls_parallel_status(urls, max_workers).items()}


def is_specific_job_url(url: str) -> bool:
    """Retorna True se a URL aponta para uma vaga específica (não página de empresa)."""
    if re.search(r"/jobs/\d+", url):
        return True  # Greenhouse numeric ID
    if re.search(r"/[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}", url, re.I):
        return True  # UUID (Lever, Ashby)
    if re.search(r"/view/[A-Za-z0-9_=-]+", url):
        return True  # Workable ID
    if re.search(r"/remote-jobs/[a-z0-9-]+", url):
        return True  # WWR slug
    if re.search(r"remotive\.com/remote/jobs/[a-z0-9-]+/[a-z0-9-]+-\d+$", url):
        return True  # Remotive category + slug + numeric ID
    if re.search(r"wellfound\.com/(?:jobs|company/[^/]+/jobs)/[a-z0-9-]+", url, re.I):
        return True  # Wellfound job slug
    if re.search(r"/jobs/[a-z0-9-]{10,}$", url):
        return True  # Remotive/Himalayas slug
    if re.search(r"/o/[a-z0-9-]+$", url):
        return True  # Recruitee slug
    if re.search(r"/positions/\d+", url):
        return True  # Careers site numeric
    if re.search(r"/j/[A-Za-z0-9]+", url):
        return True  # Workable apply link
    return False


# ── Cache de links quebrados ──────────────────────────────────────────────────

class BrokenCache:
    """Interface para broken_links.json. Garante atomicidade e consistência.
    Todas as URLs são normalizadas antes de comparação."""

    def __init__(self, path: Path):
        self.path = path
        self._broken: set[str] = set()
        self._ok: set[str] = set()
        self._checked_at: dict[str, str] = {}
        self._validation_policy_version = 0
        self._load()

    def _load(self):
        if not self.path.exists():
            return
        try:
            raw = self.path.read_bytes().rstrip(b"\x00").decode("utf-8")
            data = json.loads(raw)
            self._broken = {normalize_url(u) for u in data.get("broken", [])}
            self._ok = {normalize_url(u) for u in data.get("ok", [])}
            self._checked_at = {
                normalize_url(u): v for u, v in data.get("checked_at", {}).items()
            }
            self._validation_policy_version = (
                data.get("meta", {}).get("validation_policy_version", 0)
            )
        except Exception:
            pass

    def save(self):
        data = {
            "broken": sorted(self._broken),
            "ok": sorted(self._ok - self._broken),
        }
        if self._checked_at:
            data["checked_at"] = dict(sorted(self._checked_at.items()))
        data["meta"] = {"validation_policy_version": VALIDATION_POLICY_VERSION}
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        tmp.replace(self.path)

    @property
    def broken(self) -> set[str]:
        return self._broken

    @property
    def ok(self) -> set[str]:
        return self._ok

    @property
    def is_current_policy(self) -> bool:
        return self._validation_policy_version == VALIDATION_POLICY_VERSION

    def is_broken(self, url: str) -> bool:
        """Verifica se URL está no cache de links quebrados.
        Normaliza a URL antes de comparar."""
        n = normalize_url(url)
        if n in self._broken:
            return True
        decoded = urllib.parse.unquote(n)
        return decoded != n and decoded in self._broken

    def mark_broken(self, url: str):
        n = normalize_url(url)
        self._broken.add(n)
        self._ok.discard(n)
        self._checked_at.pop(n, None)

    def mark_ok(self, url: str, date_str: str):
        n = normalize_url(url)
        self._ok.add(n)
        self._broken.discard(n)
        self._checked_at[n] = date_str

    def mark_unknown(self, url: str):
        """Keep uncertain links publishable, but do not cache them as healthy."""
        n = normalize_url(url)
        self._broken.discard(n)
        self._ok.discard(n)
        self._checked_at.pop(n, None)

    def add_broken_batch(self, urls: set[str]):
        for u in urls:
            self.mark_broken(u)

    def add_ok_batch(self, urls: set[str], date_str: str):
        for u in urls:
            self.mark_ok(u, date_str)

    def prune_stale(self, live_urls: set[str]):
        """Remove entries that no longer appear in any .md file."""
        normalized_live = {normalize_url(u) for u in live_urls}
        self._ok &= normalized_live
        self._checked_at = {
            u: v for u, v in self._checked_at.items() if u in normalized_live
        }
