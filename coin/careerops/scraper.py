"""Live job board scraper.

LinkedIn: uses the public guest jobs endpoint at
  https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search
which returns HTML snippets, no auth required. Paginates in chunks of 25.

Indeed: Cloudflare-protected. We attempt a search; if it fails or returns
no cards, we log and move on — LinkedIn carries the pipeline.

Outputs list[dict] ready to feed into pipeline.upsert_roles().
"""

from __future__ import annotations

import time
import re
from urllib.parse import urlparse
import httpx
from bs4 import BeautifulSoup

from config import (
    BOARDS, LANES, REQUEST_DELAY_SECONDS, REQUEST_TIMEOUT,
    USER_AGENT, DEFAULT_LOCATION,
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

        results.append({
            "url": href,
            "title": title,
            "company": company,
            "location": location,
            "comp_raw": comp_raw,
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


def search_all_lanes(limit_per_lane: int = 15, location: str | None = None) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    for lane in LANES.keys():
        try:
            lane_results = search(lane, limit=limit_per_lane, location=location)
        except Exception as exc:
            print(f"[{lane}] search failed: {exc}")
            continue
        for r in lane_results:
            if r["url"] not in seen:
                seen.add(r["url"])
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
