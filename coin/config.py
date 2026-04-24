import os
from dotenv import load_dotenv

load_dotenv()

# ── Compensation floors ───────────────────────────────────────────────────────
MIN_BASE_SALARY = int(os.getenv("COIN_MIN_BASE", "180000"))
MIN_TOTAL_COMP = int(os.getenv("COIN_MIN_TC", "250000"))

# ── Scraper behavior ──────────────────────────────────────────────────────────
REQUEST_DELAY_SECONDS = 2.0
REQUEST_TIMEOUT = 20
USER_AGENT = os.getenv(
    "COIN_USER_AGENT",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
)
DEFAULT_LOCATION = os.getenv("COIN_LOCATION", "United States")
SCRAPE_CACHE_TTL_HOURS = 24

# ── Target archetypes ─────────────────────────────────────────────────────────
# Each archetype maps Sean's real experience to a role family. The `emphasis`
# list points to story ids in data/resumes/base.py; `north_star` is editable in
# config/profile.yml (Sean's one-line pitch).
LANES = {
    "cox-style-tpm": {
        "label": "High-Tier TPM (Cox/True-Local-Labs lineage)",
        "title_keywords": [
            "technical program manager", "senior tpm", "staff tpm",
            "principal tpm", "director of tpm", "head of program management",
        ],
        "skill_keywords": [
            "program management", "cross-functional", "pmp", "agile",
            "roadmap", "stakeholder", "hardware", "iot", "platform",
        ],
        "emphasis": ["cox_true_local_labs", "global_engineering_orchestration"],
        "exclude_titles": ["junior", "associate", "coordinator", "intern"],
    },
    "titanx-style-pm": {
        "label": "AI / SaaS Product Manager with operator chops",
        "title_keywords": [
            "product manager", "senior pm", "group pm", "principal pm",
            "director of product", "ai product", "head of product",
        ],
        "skill_keywords": [
            "product strategy", "go-to-market", "saas", "ai", "llm",
            "roadmap", "kpi", "product-led growth", "b2b", "platform",
        ],
        "emphasis": ["titanx_fractional_coo", "cox_true_local_labs"],
        "exclude_titles": ["junior", "associate", "intern", "apm"],
    },
    "enterprise-sales-engineer": {
        "label": "Enterprise Technical Sales / Solutions Engineer",
        "title_keywords": [
            "sales engineer", "solutions engineer", "solutions architect",
            "technical sales", "enterprise ae", "field cto", "forward deployed",
        ],
        "skill_keywords": [
            "arr", "enterprise", "b2b", "saas", "technical sales",
            "rfp", "demo", "discovery", "rf", "iot", "wireless",
        ],
        "emphasis": ["arr_growth_6m_to_13m", "titanx_fractional_coo", "utah_broadband_acquisition"],
        "exclude_titles": ["sdr", "bdr", "inside sales", "junior"],
    },
    "revenue-ops-transformation": {
        "label": "Transformation / Revenue Ops Leader",
        "title_keywords": [
            "head of revenue operations", "director of revenue ops",
            "vp operations", "chief of staff", "head of operations",
            "transformation lead", "business operations", "coo", "fractional coo",
        ],
        "skill_keywords": [
            "revenue operations", "forecasting", "operational cadence",
            "cross-functional", "p&l", "m&a", "integration", "gtm",
        ],
        "emphasis": ["utah_broadband_acquisition", "titanx_fractional_coo", "arr_growth_6m_to_13m"],
        "exclude_titles": ["analyst", "junior", "associate"],
    },
    "global-eng-orchestrator": {
        "label": "Global Engineering / Platform TPM",
        "title_keywords": [
            "technical program manager", "platform tpm", "infrastructure tpm",
            "senior tpm", "staff tpm", "principal tpm", "director engineering programs",
        ],
        "skill_keywords": [
            "distributed teams", "global", "platform", "infrastructure",
            "wireless", "aerospace", "defense", "5g", "lte", "rf", "iot",
        ],
        "emphasis": ["global_engineering_orchestration", "cox_true_local_labs"],
        "exclude_titles": ["junior", "associate", "coordinator"],
    },
}

# ── Job boards ────────────────────────────────────────────────────────────────
BOARDS = {
    "linkedin": {
        "enabled": True,
        # Public guest jobs endpoint — returns HTML snippets, no auth required.
        "search_url": "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search",
        "posting_url": "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting",
    },
    "indeed": {
        "enabled": True,
        # Indeed now sits behind Cloudflare; we try, degrade if blocked.
        "base_url": "https://www.indeed.com/jobs",
    },
    "levels_fyi": {
        "enabled": False,  # Phase 2 — compensation cross-reference
        "base_url": "https://www.levels.fyi/jobs",
    },
}

# ── Database ──────────────────────────────────────────────────────────────────
DB_PATH = os.getenv("COIN_DB_PATH", "data/db/pipeline.db")

# ── Fit scoring weights (comp-first per CRO verdict) ─────────────────────────
FIT_SCORE_WEIGHTS = {
    "comp": 0.40,
    "skill_match": 0.30,
    "title_match": 0.20,
    "remote": 0.10,
}

# ── Paths ─────────────────────────────────────────────────────────────────────
PROFILE_YAML_PATH = "config/profile.yml"
GENERATED_RESUMES_DIR = "data/resumes/generated"
