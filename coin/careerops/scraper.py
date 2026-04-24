"""Job board scraper — LinkedIn, Indeed, Levels.fyi."""

import time
import httpx
from bs4 import BeautifulSoup
from config import BOARDS, LANES, REQUEST_DELAY_SECONDS, REQUEST_TIMEOUT, USER_AGENT


def _get(url: str, params: dict | None = None) -> str:
    headers = {"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"}
    with httpx.Client(timeout=REQUEST_TIMEOUT, follow_redirects=True) as client:
        resp = client.get(url, params=params, headers=headers)
        resp.raise_for_status()
    time.sleep(REQUEST_DELAY_SECONDS)
    return resp.text


def _parse_linkedin(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    results = []
    for card in soup.select("li.jobs-search__results-list > div"):
        try:
            title_el = card.select_one("h3")
            company_el = card.select_one("h4")
            location_el = card.select_one(".job-search-card__location")
            link_el = card.select_one("a.base-card__full-link")
            salary_el = card.select_one(".job-search-card__salary-info")
            results.append({
                "title": title_el.text.strip() if title_el else None,
                "company": company_el.text.strip() if company_el else None,
                "location": location_el.text.strip() if location_el else None,
                "url": link_el["href"].split("?")[0] if link_el else None,
                "comp_raw": salary_el.text.strip() if salary_el else None,
                "source": "linkedin",
            })
        except Exception:
            continue
    return [r for r in results if r.get("url")]


def _parse_indeed(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    results = []
    for card in soup.select("div.job_seen_beacon"):
        try:
            title_el = card.select_one("h2.jobTitle span")
            company_el = card.select_one("span.companyName")
            location_el = card.select_one("div.companyLocation")
            link_el = card.select_one("h2.jobTitle a")
            salary_el = card.select_one("div.metadata.salary-snippet-container")
            job_id = link_el["data-jk"] if link_el and link_el.get("data-jk") else None
            results.append({
                "title": title_el.text.strip() if title_el else None,
                "company": company_el.text.strip() if company_el else None,
                "location": location_el.text.strip() if location_el else None,
                "url": f"https://www.indeed.com/viewjob?jk={job_id}" if job_id else None,
                "comp_raw": salary_el.text.strip() if salary_el else None,
                "source": "indeed",
            })
        except Exception:
            continue
    return [r for r in results if r.get("url")]


def search(lane: str, limit: int = 25) -> list[dict]:
    if lane not in LANES:
        raise ValueError(f"Unknown lane '{lane}'. Choose from: {list(LANES.keys())}")

    cfg = LANES[lane]
    query = " OR ".join(f'"{kw}"' for kw in cfg["title_keywords"][:3])
    results: list[dict] = []

    if BOARDS["linkedin"]["enabled"]:
        try:
            html = _get(
                BOARDS["linkedin"]["base_url"],
                params={"keywords": query, "f_SB2": "6", "sortBy": "R", "count": limit},
            )
            results += _parse_linkedin(html)
        except Exception as exc:
            print(f"[LinkedIn] scrape failed: {exc}")

    if BOARDS["indeed"]["enabled"] and len(results) < limit:
        try:
            html = _get(
                BOARDS["indeed"]["base_url"],
                params={"q": query, "sort": "date", "limit": limit},
            )
            results += _parse_indeed(html)
        except Exception as exc:
            print(f"[Indeed] scrape failed: {exc}")

    for r in results:
        r["lane"] = lane
        r["remote"] = int(
            any(word in (r.get("location") or "").lower() for word in ["remote", "anywhere"])
        )

    return results[:limit]


def fetch_jd(url: str) -> str:
    """Fetch raw job description text from a role URL."""
    html = _get(url)
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)[:8000]
