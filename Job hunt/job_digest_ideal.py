#!/usr/bin/env python3
"""
Ideal Job Digest (New England entry-level ChemE / Process / Assoc Scientist)

Sources:
- Adzuna API (broad)
- Greenhouse boards (curated companies)
- Workday CXS (curated companies)

Key goals:
- SPEED + “jobs in front of me”:
    * Use --fast to cut API calls + skip OpenAI ranking
    * Heuristic filter/score only (very fast) unless you explicitly enable OpenAI ranking
- Robust New England location handling:
    * Adzuna often returns "City, County" (no state) -> infer state from the Adzuna `where` loop
    * Adzuna often returns "Massachusetts, US" -> parse full state name and IGNORE "US"
- SQLite dedupe (email only new)
- Email grouped by State -> City; salary shown if present

Run:
  python3 job_digest_ideal.py --config config.json --no-email
  python3 job_digest_ideal.py --config config.json
  python3 job_digest_ideal.py --config config.json --debug
  python3 job_digest_ideal.py --config config.json --fast --no-email
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import email.utils
import hashlib
import html
import json
import os
import re
import sqlite3
import sys
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

try:
    from openai import OpenAI  # pip install openai
except Exception:
    OpenAI = None


# -------------------------
# Model
# -------------------------

@dataclasses.dataclass(frozen=True)
class Job:
    source: str               # adzuna | greenhouse | workday
    source_id: str
    title: str
    company: str
    location_raw: str
    city: Optional[str]
    state: Optional[str]
    url: str
    posted_at: Optional[str]
    salary: Optional[str]
    snippet: str
    score: float = 0.0


# -------------------------
# Helpers
# -------------------------

def utc_now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()

def normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())

def make_job_key(source: str, source_id: str, url: str) -> str:
    base = f"{source}::{source_id}::{url}".encode("utf-8", errors="ignore")
    return hashlib.sha256(base).hexdigest()


# -------------------------
# Location parsing (robust)
# -------------------------

STATE_NAMES_TO_ABBR = {
    "massachusetts": "MA",
    "connecticut": "CT",
    "rhode island": "RI",
    "new hampshire": "NH",
    "vermont": "VT",
    "maine": "ME",
}

# Infer state from Adzuna `where` when location comes back like "Boston, Suffolk County"
WHERE_TO_STATE_ABBR = {
    "Massachusetts": "MA",
    "Connecticut": "CT",
    "Rhode Island": "RI",
    "New Hampshire": "NH",
    "Vermont": "VT",
    "Maine": "ME",
}

CITY_STATE_RE = re.compile(r"^\s*([^,]+)\s*,\s*([A-Z]{2})\b")

def parse_city_state(location: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Returns (city, state_abbr) where possible.

    Handles:
      - "Cambridge, MA"
      - "Cambridge, Massachusetts, US"
      - "Massachusetts, US" -> (None, "MA")
      - Avoids treating "US" as a state
      - Avoids "County" being treated as a city
      - Handles "Remote" / "United States" gracefully
    """
    loc = normalize_ws(location)
    if not loc:
        return None, None

    low = loc.lower()
    if "remote" in low:
        return "Remote", None

    # "City, ST"
    m = CITY_STATE_RE.match(loc)
    if m:
        city = normalize_ws(m.group(1))
        st = m.group(2).upper()
        return city, st

    # Full state name anywhere in string (e.g., "Massachusetts, US")
    for name, abbr in STATE_NAMES_TO_ABBR.items():
        if name in low:
            left = normalize_ws(loc.split(",")[0]) if "," in loc else None
            # If left side IS the state name (no city given), return city=None
            if left and left.lower() == name:
                return None, abbr
            # If left looks like a county, treat as no city
            if left and re.search(r"\bcounty\b", left.lower()):
                return None, abbr
            # Otherwise treat left as city-like token unless it's obviously not a city
            if left and left.lower() not in ("united states", "usa", "remote", "us"):
                return left, abbr
            return None, abbr

    # Fallback: scan 2–3 letter tokens but ignore US/USA/etc.
    tokens = re.findall(r"\b([A-Z]{2,3})\b", loc)
    for tok in tokens:
        st = tok.upper()
        if st in {"US", "USA", "UK", "EU"}:
            continue
        if len(st) == 2:
            city = normalize_ws(loc.split(",")[0]) if "," in loc else None
            if city and re.search(r"\bcounty\b", city.lower()):
                city = None
            return city, st

    return None, None


# -------------------------
# SQLite
# -------------------------

def init_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            job_key TEXT PRIMARY KEY,
            source TEXT,
            source_id TEXT,
            title TEXT,
            company TEXT,
            location_raw TEXT,
            city TEXT,
            state TEXT,
            url TEXT,
            posted_at TEXT,
            salary TEXT,
            snippet TEXT,
            score REAL,
            first_seen_utc TEXT,
            last_seen_utc TEXT,
            last_emailed_utc TEXT
        )
    """)
    conn.commit()
    return conn

def upsert_job(conn: sqlite3.Connection, job: Job) -> Tuple[bool, str]:
    job_key = make_job_key(job.source, job.source_id, job.url)
    now = utc_now_iso()
    exists = conn.execute("SELECT 1 FROM jobs WHERE job_key=?", (job_key,)).fetchone() is not None

    if not exists:
        conn.execute("""
            INSERT INTO jobs VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL
            )
        """, (
            job_key, job.source, job.source_id, job.title, job.company,
            job.location_raw, job.city, job.state, job.url,
            job.posted_at, job.salary, job.snippet, float(job.score),
            now, now
        ))
    else:
        conn.execute("""
            UPDATE jobs
               SET last_seen_utc=?,
                   title=?,
                   company=?,
                   location_raw=?,
                   city=?,
                   state=?,
                   posted_at=?,
                   salary=?,
                   snippet=?,
                   score=?
             WHERE job_key=?
        """, (
            now, job.title, job.company, job.location_raw, job.city, job.state,
            job.posted_at, job.salary, job.snippet, float(job.score), job_key
        ))
    conn.commit()
    return (not exists, job_key)

def get_unemailed(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    cur = conn.execute("""
        SELECT * FROM jobs
         WHERE last_emailed_utc IS NULL
         ORDER BY score DESC, first_seen_utc DESC
    """)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]

def mark_emailed(conn: sqlite3.Connection, keys: List[str]) -> None:
    if not keys:
        return
    now = utc_now_iso()
    conn.executemany("UPDATE jobs SET last_emailed_utc=? WHERE job_key=?", [(now, k) for k in keys])
    conn.commit()


# -------------------------
# Filtering
# -------------------------

_WORD_RE_CACHE: Dict[str, re.Pattern] = {}

def _word_pat(word: str) -> re.Pattern:
    # whole-word match with case-insensitive flag
    key = word.lower()
    if key not in _WORD_RE_CACHE:
        _WORD_RE_CACHE[key] = re.compile(rf"\b{re.escape(word)}\b", re.IGNORECASE)
    return _WORD_RE_CACHE[key]

def contains_any(text: str, words: Iterable[str]) -> bool:
    """
    Safer than plain substring:
    - For very short keywords (<=2 chars), require whole-word match to avoid "it" nuking "validation".
    - For others, use substring match.
    """
    t = (text or "")
    tl = t.lower()
    for w in words:
        if not w:
            continue
        w = w.strip()
        if not w:
            continue
        if len(w) <= 2:
            if _word_pat(w).search(t):
                return True
        else:
            if w.lower() in tl:
                return True
    return False

def heuristic_match(job: Job, cfg: Dict[str, Any]) -> bool:
    f = cfg["filters"]
    title = (job.title or "").lower()
    body = (job.snippet or "").lower()

    if contains_any(title, f.get("exclude_title_keywords", [])):
        return False

    include_hit = contains_any(title, f.get("include_title_keywords", []))
    entry_hit = contains_any(title + " " + body, f.get("entry_level_hints", []))

    relevant = contains_any(title + " " + body, [
        "engineer", "engineering", "process", "chemical",
        "manufacturing", "gmp", "msat", "validation",
        "quality", "bioprocess", "downstream", "upstream",
        "scientist", "research associate"
    ])

    return (include_hit or entry_hit) and relevant

def heuristic_score(job: Job, cfg: Dict[str, Any]) -> float:
    f = cfg["filters"]
    t = (job.title or "").lower()
    s = (job.snippet or "").lower()
    score = 0.0

    for kw in f.get("include_title_keywords", []):
        if kw.lower() in t:
            score += 3.0

    for kw in f.get("entry_level_hints", []):
        # short tokens are dangerous; still allow but whole-word matching happens inside contains_any
        if contains_any(t + " " + s, [kw]):
            score += 1.5

    for kw in cfg.get("filters", {}).get("prefer_industry_keywords", []):
        if kw.lower() in t or kw.lower() in s:
            score += 0.4

    return score


# -------------------------
# Adzuna
# -------------------------

def fetch_adzuna(cfg: Dict[str, Any], allowed_states: set[str], debug: bool, fast: bool) -> List[Job]:
    a = cfg["adzuna"]
    country = a.get("country", "us")
    app_id = a["app_id"]
    app_key = a["app_key"]

    results_per_page = int(a.get("results_per_page", 50))

    # Fast mode: reduce pages + reduce queries if user provided lots
    max_pages = int(a.get("max_pages", 2))
    queries = list(a.get("queries", []))
    where_list = list(a.get("where", []))

    if fast:
        max_pages = 1
        # Keep only a few broad queries for speed
        if len(queries) > 3:
            queries = ["process engineer", "manufacturing engineer", "associate scientist"]

    out: List[Job] = []

    for query in queries:
        for where in where_list:
            inferred_state = WHERE_TO_STATE_ABBR.get(where)
            for page in range(1, max_pages + 1):
                url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"
                params = {
                    "app_id": app_id,
                    "app_key": app_key,
                    "what": query,
                    "where": where,
                    "results_per_page": results_per_page,
                    "sort_by": "date",
                    "content-type": "application/json",
                }

                r = requests.get(url, params=params, timeout=20)
                r.raise_for_status()
                data = r.json()

                for j in data.get("results", []):
                    title = normalize_ws(j.get("title", ""))
                    company = normalize_ws((j.get("company") or {}).get("display_name", "") or "Unknown")
                    loc = normalize_ws((j.get("location") or {}).get("display_name", "") or "")
                    desc = normalize_ws(j.get("description", "") or "")
                    snippet = (desc[:350] + "…") if len(desc) > 350 else desc

                    city, st = parse_city_state(loc)

                    # Adzuna "City, County" (no state) -> infer from looped `where`
                    if not st and inferred_state:
                        st = inferred_state
                        if not city and "," in loc:
                            cand = normalize_ws(loc.split(",")[0])
                            city = None if re.search(r"\bcounty\b", cand.lower()) else cand

                    keep_loc = bool(st) and st.upper() in allowed_states

                    if debug:
                        print(f"ADZUNA LOC: '{loc}' -> city={city}, st={st}, keep_loc={keep_loc}")

                    if not keep_loc:
                        continue

                    salary_min = j.get("salary_min")
                    salary_max = j.get("salary_max")
                    salary = None
                    try:
                        if salary_min or salary_max:
                            if salary_min and salary_max:
                                salary = f"${int(salary_min):,} – ${int(salary_max):,}"
                            elif salary_min:
                                salary = f"${int(salary_min):,}+"
                            else:
                                salary = f"Up to ${int(salary_max):,}"
                    except Exception:
                        salary = None

                    job = Job(
                        source="adzuna",
                        source_id=str(j.get("id") or hashlib.md5((title + company + loc).encode()).hexdigest()),
                        title=title,
                        company=company,
                        location_raw=loc,
                        city=city,
                        state=st,
                        url=j.get("redirect_url") or j.get("adref") or "",
                        posted_at=j.get("created") or j.get("created_at"),
                        salary=salary,
                        snippet=snippet,
                        score=0.0,
                    )

                    if not job.url:
                        continue

                    if not heuristic_match(job, cfg):
                        if debug:
                            print(f"  DROP (heuristic): {title} | {company}")
                        continue

                    out.append(dataclasses.replace(job, score=heuristic_score(job, cfg)))

    return out


# -------------------------
# Greenhouse
# -------------------------

def fetch_greenhouse(company_name: str, token: str, cfg: Dict[str, Any], allowed_states: set[str], debug: bool) -> List[Job]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    data = r.json()

    out: List[Job] = []
    for j in data.get("jobs", []):
        title = normalize_ws(j.get("title", ""))
        loc = normalize_ws((j.get("location") or {}).get("name", "") or "")
        city, st = parse_city_state(loc)

        if not (st and st.upper() in allowed_states):
            continue

        content = j.get("content") or ""
        snippet = normalize_ws(re.sub(r"<[^>]+>", " ", content))[:350]

        job = Job(
            source="greenhouse",
            source_id=str(j.get("id", "")),
            title=title,
            company=company_name,
            location_raw=loc,
            city=city,
            state=st,
            url=j.get("absolute_url") or "",
            posted_at=j.get("updated_at"),
            salary=None,
            snippet=snippet,
            score=0.0,
        )

        if not job.url:
            continue
        if not heuristic_match(job, cfg):
            if debug:
                print(f"GH DROP (heuristic): {title} | {company_name}")
            continue

        out.append(dataclasses.replace(job, score=heuristic_score(job, cfg)))

    return out


# -------------------------
# Workday
# -------------------------

def fetch_workday(company_name: str, host: str, tenant: str, site: str, locale: str,
                 cfg: Dict[str, Any], allowed_states: set[str], debug: bool, fast: bool) -> List[Job]:
    base = f"https://{host}"
    api = f"{base}/wday/cxs/{tenant}/{site}/jobs"

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Origin": base,
        "Referer": f"{base}/{locale}/{site}",
        "User-Agent": "Mozilla/5.0",
    }

    out: List[Job] = []
    limit = 20
    offset = 0

    max_pages = int(cfg.get("workday_max_pages", 3))
    if fast:
        max_pages = 1

    page = 0

    while True:
        payload = {"appliedFacets": {}, "limit": limit, "offset": offset, "searchText": ""}

        r = requests.post(api, headers=headers, json=payload, timeout=20)
        r.raise_for_status()
        data = r.json()

        postings = data.get("jobPostings") or []
        if not postings:
            break

        for p in postings:
            title = normalize_ws(p.get("title", ""))
            loc = normalize_ws(p.get("locationsText", "") or p.get("location", "") or "")
            city, st = parse_city_state(loc)

            if not (st and st.upper() in allowed_states):
                continue

            bullet = p.get("bulletFields") or []
            snippet = normalize_ws(" | ".join([str(x) for x in bullet if x]))[:350] if bullet else ""

            external_path = p.get("externalPath") or ""
            job_url = f"{base}/{locale}/{site}{external_path}" if external_path else f"{base}/{locale}/{site}"

            job = Job(
                source="workday",
                source_id=str(external_path or p.get("id") or hashlib.md5((company_name + title + loc).encode()).hexdigest()),
                title=title,
                company=company_name,
                location_raw=loc,
                city=city,
                state=st,
                url=job_url,
                posted_at=p.get("postedOn"),
                salary=None,
                snippet=snippet,
                score=0.0,
            )

            if not heuristic_match(job, cfg):
                if debug:
                    print(f"WD DROP (heuristic): {title} | {company_name}")
                continue

            out.append(dataclasses.replace(job, score=heuristic_score(job, cfg)))

        offset += limit
        page += 1
        if page >= max_pages:
            break

        total = data.get("total") or data.get("totalCount")
        if isinstance(total, int) and offset >= total:
            break

    return out


# -------------------------
# OpenAI ranking (optional)
# -------------------------

def openai_rank(jobs: List[Job], cfg: Dict[str, Any], debug: bool, fast: bool) -> List[Job]:
    """
    Batch ranks jobs with OpenAI if enabled AND key is available.

    Fast mode skips OpenAI entirely.
    If OPENAI_API_KEY isn't present in env, silently skip.
    """
    if not jobs:
        return jobs

    if fast:
        return jobs

    if not cfg.get("openai", {}).get("enabled", True):
        return jobs

    if os.getenv("OPENAI_API_KEY") in (None, ""):
        # speed-first: just skip silently
        return jobs

    if OpenAI is None:
        return jobs

    model = cfg["openai"]["model"]
    batch_size = int(cfg["openai"].get("batch_size", 10))
    persona = cfg["openai"].get("persona", "You are an expert recruiter.")
    scoring_prompt = cfg["openai"]["scoring_prompt"]

    client = OpenAI()
    ranked: List[Job] = []

    for i in range(0, len(jobs), batch_size):
        chunk = jobs[i:i + batch_size]
        payload = [{
            "id": j.source_id,
            "title": j.title,
            "company": j.company,
            "location": j.location_raw,
            "salary": j.salary,
            "snippet": j.snippet[:500],
            "url": j.url,
        } for j in chunk]

        try:
            resp = client.responses.create(
                model=model,
                input=[
                    {"role": "system", "content": persona},
                    {"role": "user", "content": scoring_prompt + "\n\nJOBS:\n" + json.dumps(payload)}
                ],
                text={"format": {"type": "json_object"}},
            )
            data = json.loads(resp.output_text)
        except Exception as e:
            if debug:
                print(f"[WARN] OpenAI batch failed: {e}", file=sys.stderr)
            # keep heuristic scores
            ranked.extend(chunk)
            continue

        score_map = {
            item.get("id"): (float(item.get("score", 0.0)), str(item.get("reason", "")))
            for item in (data.get("ranked") or [])
        }

        for j in chunk:
            sc, reason = score_map.get(j.source_id, (j.score, ""))
            extra = f"\nOpenAI: {reason}" if reason else ""
            ranked.append(dataclasses.replace(j, score=sc, snippet=j.snippet + extra))

        if debug:
            print(f"OpenAI ranked batch {i//batch_size + 1} / {(len(jobs)+batch_size-1)//batch_size}")

    ranked.sort(key=lambda x: x.score, reverse=True)
    return ranked


# -------------------------
# Email
# -------------------------

def render_email(rows: List[Dict[str, Any]], subject_prefix: str) -> Tuple[str, str]:
    today = dt.datetime.now().strftime("%Y-%m-%d")
    subject = f"{subject_prefix} {today} — {len(rows)} new"

    grouped: Dict[str, Dict[str, List[Dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for r in rows:
        st = (r.get("state") or "??").upper()
        city = r.get("city") or "Unknown"
        grouped[st][city].append(r)

    for st in grouped:
        for city in grouped[st]:
            grouped[st][city].sort(key=lambda x: float(x.get("score", 0.0)), reverse=True)

    def esc(x: Any) -> str:
        return html.escape(str(x)) if x is not None else ""

    parts: List[str] = []
    parts.append(f"<h2>New job matches — {esc(today)}</h2>")
    parts.append("<p>Sources: Adzuna (broad) + curated Greenhouse/Workday. Salary shown when available.</p>")

    for st in sorted(grouped.keys()):
        parts.append(f"<h3>{esc(st)}</h3>")
        for city in sorted(grouped[st].keys()):
            parts.append(f"<h4>{esc(city)}, {esc(st)}</h4><ul>")
            for r in grouped[st][city]:
                title = esc(r.get("title", ""))
                company = esc(r.get("company", ""))
                url = r.get("url", "") or ""
                salary = esc(r.get("salary") or "Not listed")
                source = esc(r.get("source", ""))
                score = esc(round(float(r.get("score", 0.0)), 1))
                snippet = esc((r.get("snippet") or "")[:700])
                loc_raw = esc(r.get("location_raw") or "")

                # For href, don't html.escape the entire URL (can turn & into &amp;). Just quote it.
                safe_href = url.replace("'", "%27")

                parts.append(
                    "<li style='margin-bottom:12px'>"
                    f"<b>{title}</b> — {company} <i>({source})</i><br/>"
                    f"{loc_raw}<br/>"
                    f"Salary: <b>{salary}</b> | Score: <b>{score}</b><br/>"
                    f"<a href='{safe_href}'>Open posting</a><br/>"
                    f"<span style='color:#444'>{snippet}</span>"
                    "</li>"
                )
            parts.append("</ul>")

    return subject, "\n".join(parts)

def send_email_smtp(email_cfg: Dict[str, Any], subject: str, html_body: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["From"] = email_cfg["from_email"]

    # allow one or multiple recipients
    recipients = email_cfg["to_email"]
    if isinstance(recipients, str):
        recipients = [recipients]

    msg["To"] = ", ".join(recipients)
    msg["Date"] = email.utils.formatdate(localtime=True)
    msg["Subject"] = subject

    msg.attach(MIMEText("HTML email. If you see this, your client didn't render HTML.", "plain"))
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(email_cfg["smtp_host"], int(email_cfg["smtp_port"]), timeout=30) as s:
        s.ehlo()
        s.starttls()
        s.ehlo()
        s.login(email_cfg["from_email"], email_cfg["smtp_password"])

        # send to all recipients
        s.sendmail(email_cfg["from_email"], recipients, msg.as_string())


# -------------------------
# Main
# -------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--db", default="jobs.sqlite")
    ap.add_argument("--no-email", action="store_true")
    ap.add_argument("--debug", action="store_true")
    ap.add_argument("--fast", action="store_true", help="Speed-first: fewer API calls + skip OpenAI ranking")
    args = ap.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    allowed_states = {s.upper() for s in cfg["filters"]["states"]}

    conn = init_db(args.db)

    jobs: List[Job] = []

    # Adzuna
    try:
        jobs.extend(fetch_adzuna(cfg, allowed_states, args.debug, args.fast))
    except Exception as e:
        print(f"[WARN] Adzuna fetch failed: {e}", file=sys.stderr)

    # Greenhouse
    for g in cfg.get("sources", {}).get("greenhouse", []):
        try:
            jobs.extend(fetch_greenhouse(g["company_name"], g["board_token"], cfg, allowed_states, args.debug))
        except Exception as e:
            print(f"[WARN] Greenhouse failed for {g.get('company_name')}: {e}", file=sys.stderr)

    # Workday
    for w in cfg.get("sources", {}).get("workday", []):
        try:
            jobs.extend(fetch_workday(
                w["company_name"], w["host"], w["tenant"], w["site"], w.get("locale", "en-US"),
                cfg, allowed_states, args.debug, args.fast
            ))
        except Exception as e:
            print(f"[WARN] Workday failed for {w.get('company_name')}: {e}", file=sys.stderr)

    # OpenAI ranking (optional)
    jobs = openai_rank(jobs, cfg, args.debug, args.fast)

    # Upsert
    for j in jobs:
        upsert_job(conn, j)

    rows = get_unemailed(conn)
    max_items = int(cfg["filters"].get("max_items_email", 40))
    rows = rows[:max_items]

    if args.no_email:
        print(f"Collected {len(jobs)} matches; {len(rows)} unemailed in DB. (Email disabled)")
        for j in jobs[:12]:
            print(f"- [{j.source}] {j.title} | {j.company} | {j.location_raw} | city={j.city} | state={j.state} | score={round(j.score,1)}")
        return 0

    if not rows:
        print("No new jobs.")
        return 0

    subject, body = render_email(rows, cfg["email"]["subject_prefix"])
    send_email_smtp(cfg["email"], subject, body)
    mark_emailed(conn, [r["job_key"] for r in rows])
    print(f"Emailed {len(rows)} jobs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())