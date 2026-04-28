"""Live job board scraper.

LinkedIn: uses the public guest jobs endpoint at
  https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search
which returns HTML snippets, no auth required. Paginates in chunks of 25.

Indeed: Cloudflare-protected. We attempt a search; if it fails or returns
no cards, we log and move on — LinkedIn carries the pipeline.

Outputs list[dict] ready to feed into pipeline.upsert_roles().
"""

from __future__ import annotations

import datetime
import time
import re
from urllib.parse import urlparse
import httpx
from bs4 import BeautifulSoup

# Matches "Posted N <unit>s ago" / "N <unit> ago". Used as a fallback when
# LinkedIn's <time> element lacks a machine-readable datetime attribute.
RELATIVE_AGE_RE = re.compile(
    r"(\d+)\s+(minute|hour|day|week|month|year)s?\s+ago",
    re.IGNORECASE,
)
_RELATIVE_AGE_DAYS = {
    "minute": 0, "hour": 0, "day": 1, "week": 7, "month": 30, "year": 365,
}


def _extract_posted_at(card) -> str | None:
    """Pull a posting date (ISO YYYY-MM-DD) off a LinkedIn card, or None.

    Tries selectors in order of reliability; prefers the machine-readable
    datetime attribute over parsed human strings.
    """
    selectors = (
        "time.job-search-card__listdate",
        "time.job-search-card__listdate--new",
        "time[datetime]",
        ".job-search-card__listdate",
    )
    el = None
    for sel in selectors:
        el = card.select_one(sel)
        if el is not None:
            break
    if el is None:
        return None

    dt_attr = el.get("datetime") if hasattr(el, "get") else None
    if dt_attr:
        try:
            return datetime.date.fromisoformat(dt_attr).isoformat()
        except (ValueError, TypeError):
            pass

    text = el.get_text(strip=True) if hasattr(el, "get_text") else ""
    m = RELATIVE_AGE_RE.search(text or "")
    if not m:
        return None
    n = int(m.group(1))
    unit = m.group(2).lower()
    delta_days = n * _RELATIVE_AGE_DAYS.get(unit, 0)
    posted = datetime.date.today() - datetime.timedelta(days=delta_days)
    return posted.isoformat()

from config import (
    BOARDS, LANES, REQUEST_DELAY_SECONDS, REQUEST_TIMEOUT,
    USER_AGENT, DEFAULT_LOCATION, TARGET_COMPANIES, LANE_BOARD_SCORE_FLOOR,
)
from careerops.compensation import parse_comp_string


_COMMON_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
}


def _get(url: str, params: dict | None = None) -> httpx.Response:
    with httpx.Client(
        timeout=REQUEST_TIMEOUT,
        follow_redirects=True,
        http2=True,
        headers=_COMMON_HEADERS,
    ) as client:
        resp = client.get(url, params=params)
    time.sleep(REQUEST_DELAY_SECONDS)
    return resp


# ─── LinkedIn guest API ───────────────────────────────────────────────────────

def _search_linkedin(keywords: str, limit: int, location: str) -> list[dict]:
    """Hit the guest seeMoreJobPostings endpoint and parse HTML job cards."""
    url = BOARDS["linkedin"]["search_url"]
    results: list[dict] = []
    page_size = 25

    for start in range(0, max(limit, page_size), page_size):
        params = {
            "keywords": keywords,
            "location": location,
            "start": start,
            "sortBy": "DD",  # date desc
        }
        try:
            resp = _get(url, params=params)
            if resp.status_code != 200:
                print(f"[linkedin] status={resp.status_code} at start={start}")
                break
            html = resp.text
        except Exception as exc:
            print(f"[linkedin] request failed at start={start}: {exc}")
            break

        page_results = _parse_linkedin_cards(html)
        if not page_results:
            break
        results.extend(page_results)
        if len(results) >= limit:
            break

    return results[:limit]


def _parse_linkedin_cards(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    # Guest API returns a plain list of <li> wrappers, each containing a card div.
    cards = soup.select("li") or soup.select("div.base-card")
    results = []
    for card in cards:
        link_el = card.select_one("a.base-card__full-link, a.job-card-list__title, a[href*='/jobs/view/']")
        title_el = card.select_one(
            "h3.base-search-card__title, h3.base-card__title, .job-card-list__title"
        )
        company_el = card.select_one(
            "h4.base-search-card__subtitle, .job-card-container__company-name, a.hidden-nested-link"
        )
        location_el = card.select_one(".job-search-card__location, .job-card-container__metadata-item")
        salary_el = card.select_one(".job-search-card__salary-info")

        if not link_el or not title_el:
            continue

        href = (link_el.get("href") or "").split("?")[0]
        if not href or "/jobs/view/" not in href:
            continue

        title = title_el.get_text(strip=True)
        company = company_el.get_text(strip=True) if company_el else None
        location = location_el.get_text(strip=True) if location_el else None
        comp_raw = salary_el.get_text(strip=True) if salary_el else None

        posted_at = _extract_posted_at(card)

        results.append({
            "url": href,
            "title": title,
            "company": company,
            "location": location,
            "comp_raw": comp_raw,
            "posted_at": posted_at,
            "source": "linkedin",
        })
    return results


# ─── Indeed (best-effort) ─────────────────────────────────────────────────────

def _search_indeed(keywords: str, limit: int, location: str) -> list[dict]:
    params = {"q": keywords, "l": location, "sort": "date", "limit": min(limit, 50)}
    try:
        resp = _get(BOARDS["indeed"]["base_url"], params=params)
    except Exception as exc:
        print(f"[indeed] request failed (likely Cloudflare): {exc}")
        return []

    if resp.status_code in (403, 429, 503) or "Cloudflare" in resp.text[:2000]:
        print(f"[indeed] blocked by anti-bot (status={resp.status_code}) — skipping")
        return []
    if resp.status_code != 200:
        print(f"[indeed] status={resp.status_code} — skipping")
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    results = []
    for card in soup.select("div.job_seen_beacon, div[data-testid='slider_item']"):
        try:
            title_el = card.select_one("h2.jobTitle span, h2 a span")
            company_el = card.select_one("span.companyName, [data-testid='company-name']")
            location_el = card.select_one("div.companyLocation, [data-testid='text-location']")
            link_el = card.select_one("h2.jobTitle a, a[data-jk]")
            salary_el = card.select_one("div.metadata.salary-snippet-container, [data-testid='attribute_snippet_testid']")

            jk = None
            if link_el:
                jk = link_el.get("data-jk") or _extract_jk_from_href(link_el.get("href", ""))

            if not jk:
                continue

            results.append({
                "url": f"https://www.indeed.com/viewjob?jk={jk}",
                "title": title_el.get_text(strip=True) if title_el else None,
                "company": company_el.get_text(strip=True) if company_el else None,
                "location": location_el.get_text(strip=True) if location_el else None,
                "comp_raw": salary_el.get_text(strip=True) if salary_el else None,
                "source": "indeed",
            })
        except Exception:
            continue
    return results[:limit]


def _extract_jk_from_href(href: str) -> str | None:
    m = re.search(r"jk=([A-Za-z0-9]+)", href or "")
    return m.group(1) if m else None


# ─── Public API ────────────────────────────────────────────────────────────────

def search(lane: str, limit: int = 25, location: str | None = None) -> list[dict]:
    """Search all enabled boards for a single lane.

    Returns role dicts with keys: url, title, company, location, remote,
    lane, comp_raw, comp_min, comp_max, comp_source, source.
    Comp bands are parsed from comp_raw via compensation.parse_comp_string.
    """
    if lane not in LANES:
        raise ValueError(f"Unknown lane '{lane}'. Choose from: {list(LANES.keys())}")
    cfg = LANES[lane]
    # Use the top-3 title keywords OR'd together — broad net
    keywords = " OR ".join(f'"{kw}"' for kw in cfg["title_keywords"][:3])
    loc = location or DEFAULT_LOCATION

    results: list[dict] = []
    seen_urls: set[str] = set()

    if BOARDS["linkedin"]["enabled"]:
        try:
            for r in _search_linkedin(keywords, limit, loc):
                if r["url"] not in seen_urls:
                    seen_urls.add(r["url"])
                    results.append(r)
        except Exception as exc:
            print(f"[linkedin] scrape failed: {exc}")

    if BOARDS["indeed"]["enabled"] and len(results) < limit:
        try:
            for r in _search_indeed(keywords, limit - len(results), loc):
                if r["url"] not in seen_urls:
                    seen_urls.add(r["url"])
                    results.append(r)
        except Exception as exc:
            print(f"[indeed] scrape failed: {exc}")

    # Enrich: parse comp band, flag remote, tag lane
    for r in results:
        comp_min, comp_max = parse_comp_string(r.get("comp_raw"))
        r["comp_min"] = comp_min
        r["comp_max"] = comp_max
        r["comp_source"] = "explicit" if comp_min else "unverified"
        r["lane"] = lane
        r["remote"] = int(
            any(w in (r.get("location") or "").lower() for w in ("remote", "anywhere", "distributed"))
        )

    return results[:limit]


def _canonical_url(url: str | None) -> str:
    """Strip query/fragment/trailing-slash so the same role on LinkedIn vs.
    a board doesn't surface twice in dedup. Best-effort — unknown shapes
    fall through unchanged."""
    if not url:
        return ""
    try:
        p = urlparse(url)
    except Exception:
        return url
    path = (p.path or "").rstrip("/")
    return f"{p.scheme}://{p.netloc}{path}".lower()


def search_boards(
    lane: str,
    location: str | None = None,
    boards: list[str] | None = None,
    companies: list[str] | None = None,
) -> list[dict]:
    """Iterate TARGET_COMPANIES, fetch from each enabled board, filter by lane.

    Args:
      lane: archetype id (must be in LANES).
      location: substring match against role.location; None = no location filter.
      boards: subset of {"greenhouse","lever","ashby"}; default = all three.
      companies: subset of TARGET_COMPANIES keys; default = all.

    Returns role dicts with keys matching the LinkedIn scraper's shape (url,
    title, company, location, remote, lane, comp_min, comp_max, comp_source,
    source, posted_at, jd_raw, comp_currency).
    """
    # Local imports to avoid hard dependency loops at module import time.
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from careerops.boards import ALL_BOARDS
    from careerops.score import score_title

    if lane not in LANES:
        raise ValueError(f"Unknown lane '{lane}'. Choose from: {list(LANES.keys())}")

    enabled = set(boards) if boards else {"greenhouse", "lever", "ashby"}
    target_companies = (
        {k: v for k, v in TARGET_COMPANIES.items() if k in companies}
        if companies
        else dict(TARGET_COMPANIES)
    )

    # Instantiate one board scraper per enabled name (per-instance rate limit).
    board_instances: dict[str, "object"] = {}
    for cls in ALL_BOARDS:
        if cls.name in enabled:
            board_instances[cls.name] = cls()

    tasks: list[tuple[str, "object", str]] = []
    for company, slugs in target_companies.items():
        for board_name, slug in slugs.items():
            if slug and board_name in board_instances:
                tasks.append((company, board_instances[board_name], slug))

    results: list[dict] = []

    def _matches_location(loc_str: str | None, target: str) -> bool:
        if not target:
            return True
        if not loc_str:
            return False
        target_l = target.lower()
        loc_l = loc_str.lower()
        # crude substring match — "Utah" matches "Lehi, UT" via the "ut" fallback
        if target_l in loc_l:
            return True
        # tokenize the target on commas; require any token to match
        for tok in [t.strip() for t in target_l.split(",") if t.strip()]:
            if tok in loc_l:
                return True
        return False

    if not tasks:
        return results

    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = {
            ex.submit(board.fetch_listings, slug, lane): (company, board.name)
            for company, board, slug in tasks
        }
        for fut in as_completed(futures):
            company, board_name = futures[fut]
            try:
                roles = fut.result() or []
            except Exception as e:
                print(f"[boards] {company}/{board_name} failed: {e}")
                continue
            for r in roles:
                r["company"] = company  # canonical name from registry
                r["lane"] = lane
                title_score = score_title(r.get("title"), lane)
                if title_score < LANE_BOARD_SCORE_FLOOR:
                    continue
                if location and not _matches_location(r.get("location"), location):
                    # remote roles always pass — Sean is remote-friendly
                    if not r.get("remote"):
                        continue
                results.append(r)
    return results


def search_all_lanes(
    limit_per_lane: int = 15,
    location: str | None = None,
    boards: list[str] | None = None,
    companies: list[str] | None = None,
) -> list[dict]:
    """Discover across all 4 lanes from LinkedIn + (optionally) public boards.

    `boards` semantics:
      - None or contains "linkedin" → LinkedIn pass runs (existing behavior)
      - Contains any of {"greenhouse","lever","ashby"} → those boards run too
      - To skip LinkedIn entirely, pass boards=["greenhouse","lever","ashby"]
        (i.e. omit "linkedin")

    Dedup is canonical-URL based across both sources.
    """
    enabled = set(boards) if boards else {"linkedin", "greenhouse", "lever", "ashby"}
    out: list[dict] = []
    seen: set[str] = set()

    for lane in LANES.keys():
        # LinkedIn / Indeed pass (existing search() handles both)
        if "linkedin" in enabled:
            try:
                lane_results = search(lane, limit=limit_per_lane, location=location)
            except Exception as exc:
                print(f"[{lane}] linkedin search failed: {exc}")
                lane_results = []
            for r in lane_results:
                key = _canonical_url(r.get("url"))
                if key and key not in seen:
                    seen.add(key)
                    out.append(r)

        # Public boards pass
        board_subset = [b for b in ("greenhouse", "lever", "ashby") if b in enabled]
        if board_subset:
            try:
                board_results = search_boards(
                    lane,
                    location=location,
                    boards=board_subset,
                    companies=companies,
                )
            except Exception as exc:
                print(f"[{lane}] boards search failed: {exc}")
                board_results = []
            for r in board_results:
                key = _canonical_url(r.get("url"))
                if key and key not in seen:
                    seen.add(key)
                    out.append(r)

    return out


def fetch_jd(url: str) -> str:
    """Fetch the full JD text from a role URL. Works for LinkedIn guest job pages.

    For LinkedIn URLs like https://www.linkedin.com/jobs/view/<id>/, we hit the
    posting endpoint at jobs-guest/jobs/api/jobPosting/<id> which returns a
    cleaner HTML response.
    """
    try:
        lk_id = _linkedin_job_id(url)
        if lk_id:
            posting = BOARDS["linkedin"]["posting_url"]
            resp = _get(f"{posting}/{lk_id}")
            if resp.status_code == 200:
                return _extract_text(resp.text)

        resp = _get(url)
        return _extract_text(resp.text)
    except Exception as exc:
        print(f"[fetch_jd] failed for {url}: {exc}")
        return ""


def _linkedin_job_id(url: str) -> str | None:
    host = urlparse(url).netloc
    if "linkedin.com" not in host:
        return None
    m = re.search(r"/jobs/view/(?:[^/]+-)?(\d+)", url)
    if m:
        return m.group(1)
    m = re.search(r"currentJobId=(\d+)", url)
    return m.group(1) if m else None


def _extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "nav", "header", "footer", "svg"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    # Compress whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text[:12000]
