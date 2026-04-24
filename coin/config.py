import os
from dotenv import load_dotenv

load_dotenv()

# ── Compensation filter ────────────────────────────────────────────────────────
MIN_BASE_SALARY = int(os.getenv("COIN_MIN_BASE", "180000"))

# ── Claude model ───────────────────────────────────────────────────────────────
CLAUDE_MODEL = "claude-sonnet-4-6"
CLAUDE_MODEL_FAST = "claude-haiku-4-5-20251001"  # for cheap classification calls

# ── Scraper behavior ───────────────────────────────────────────────────────────
REQUEST_DELAY_SECONDS = 2.0
REQUEST_TIMEOUT = 15
USER_AGENT = os.getenv(
    "COIN_USER_AGENT",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
)
SCRAPE_CACHE_TTL_HOURS = 24

# ── Target lanes ───────────────────────────────────────────────────────────────
LANES = {
    "tpm-high": {
        "label": "High-Tier TPM",
        "title_keywords": ["technical program manager", "senior tpm", "staff tpm", "principal tpm", "director of tpm"],
        "skill_keywords": ["program management", "cross-functional", "pmp", "agile", "roadmap", "stakeholder"],
        "emphasis": ["cox_true_local_labs", "global_engineering_orchestration"],
        "exclude_titles": ["junior", "associate", "coordinator"],
    },
    "pm-ai": {
        "label": "AI Product Manager",
        "title_keywords": ["product manager", "senior pm", "group pm", "principal pm", "director of product", "ai product"],
        "skill_keywords": ["product strategy", "go-to-market", "saas", "ai", "llm", "roadmap", "kpi"],
        "emphasis": ["titanx_fractional_coo", "cox_true_local_labs"],
        "exclude_titles": ["junior", "associate", "intern"],
    },
    "sales-ent": {
        "label": "Enterprise Technical Sales",
        "title_keywords": ["sales engineer", "solutions engineer", "technical sales", "account executive", "enterprise ae", "se"],
        "skill_keywords": ["arr", "enterprise", "b2b", "saas", "technical sales", "rfp", "demo"],
        "emphasis": ["arr_growth_6m_to_13m", "titanx_fractional_coo", "utah_broadband_acquisition"],
        "exclude_titles": ["sdr", "bdr", "inside sales"],
    },
}

# ── Job boards ─────────────────────────────────────────────────────────────────
BOARDS = {
    "linkedin": {
        "enabled": True,
        "base_url": "https://www.linkedin.com/jobs/search/",
        "requires_auth": False,
    },
    "indeed": {
        "enabled": True,
        "base_url": "https://www.indeed.com/jobs",
        "requires_auth": False,
    },
    "levels_fyi": {
        "enabled": True,
        "base_url": "https://www.levels.fyi/jobs",
        "requires_auth": False,
        "comp_data": True,  # levels.fyi has explicit comp bands
    },
}

# ── Database ───────────────────────────────────────────────────────────────────
DB_PATH = "data/db/pipeline.db"

# ── Fit scoring weights ────────────────────────────────────────────────────────
FIT_SCORE_WEIGHTS = {
    "title_match": 0.30,
    "skill_match": 0.35,
    "comp_band": 0.25,
    "remote_friendly": 0.10,
}
