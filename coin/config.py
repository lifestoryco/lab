import os
from dotenv import load_dotenv

load_dotenv()

# ── Compensation floors ───────────────────────────────────────────────────────
# Sean is at $99K; targeting a 60-100% jump to a real product company or SE seat.
# $160K base / $200K TC is the realistic floor — anything below isn't worth a tailor pass.
MIN_BASE_SALARY = int(os.getenv("COIN_MIN_BASE", "160000"))
MIN_TOTAL_COMP = int(os.getenv("COIN_MIN_TC", "200000"))

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
    "mid-market-tpm": {
        "label": "Mid-Market TPM (Series B–D, IoT/hardware/wireless/B2B SaaS)",
        "title_keywords": [
            "technical program manager", "senior technical program manager",
            "director of program management", "director, technical program management",
            "head of program management", "senior tpm", "lead tpm", "program manager",
        ],
        "skill_keywords": [
            "program management", "cross-functional", "pmp", "agile",
            "roadmap", "stakeholder", "hardware", "iot", "wireless",
            "b2b saas", "client-facing", "delivery",
        ],
        "emphasis": ["cox_true_local_labs", "global_engineering_orchestration", "arr_growth_6m_to_13m"],
        "exclude_titles": [
            "junior", "associate", "coordinator", "intern",
            "staff technical program manager",  # FAANG-tier — Sean is filtered out
            "principal technical program manager",
        ],
    },
    "enterprise-sales-engineer": {
        "label": "Enterprise SE / Solutions Architect (IoT, wireless, industrial SaaS)",
        "title_keywords": [
            "sales engineer", "solutions engineer", "solutions architect",
            "senior sales engineer", "principal solutions engineer",
            "technical sales", "field cto", "forward deployed engineer",
            "pre-sales engineer", "presales solutions",
        ],
        "skill_keywords": [
            "arr", "enterprise", "b2b", "saas", "technical sales",
            "rfp", "demo", "discovery", "rf", "iot", "wireless",
            "presales", "post-sales", "customer success", "implementation",
        ],
        "emphasis": ["arr_growth_6m_to_13m", "utah_broadband_acquisition", "titanx_fractional_coo"],
        "exclude_titles": ["sdr", "bdr", "inside sales", "junior", "intern"],
    },
    "iot-solutions-architect": {
        "label": "IoT / Wireless Solutions Architect (technical pre-sales + delivery)",
        "title_keywords": [
            "solutions architect", "iot architect", "wireless architect",
            "principal architect", "senior solutions architect",
            "technical architect", "platform architect", "field architect",
        ],
        "skill_keywords": [
            "iot", "wireless", "rf", "wi-fi", "ble", "z-wave", "lora",
            "cellular", "5g", "lte", "embedded", "edge", "aws iot",
            "azure iot", "industrial iot", "firmware", "hardware integration",
        ],
        "emphasis": ["global_engineering_orchestration", "utah_broadband_acquisition", "cox_true_local_labs"],
        "exclude_titles": ["junior", "intern", "associate"],
    },
    "revenue-ops-operator": {
        "label": "RevOps / BizOps Operator (Series B–D, Utah-friendly)",
        "title_keywords": [
            "head of revenue operations", "director of revenue operations",
            "director of operations", "vp operations", "chief of staff",
            "head of operations", "business operations lead",
            "director, business operations", "head of bizops",
        ],
        "skill_keywords": [
            "revenue operations", "forecasting", "operational cadence",
            "cross-functional", "p&l", "gtm", "salesforce", "hubspot",
            "process design", "scaling operations",
        ],
        "emphasis": ["utah_broadband_acquisition", "titanx_fractional_coo", "arr_growth_6m_to_13m"],
        "exclude_titles": ["analyst", "junior", "associate", "coordinator"],
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

# ── Company tier list (for company_tier scoring dimension) ───────────────────
# IMPORTANT: tier scoring is INVERTED for Sean's reality.
# FAANG roles screen Sean out at recruiter step #1 (no CS degree, no big-tech tour).
# Sean's sweet spot is Series B–D mid-market product cos and Utah tech.
# Tier 1 (best): in-league mid-market product cos and Utah tech ecosystem
# Tier 2: recognized brands where Sean is a stretch but not auto-rejected
# Tier 3 (default): unknown small co — fine, just less leverage
# Tier 4 (penalized): FAANG/big-tech where pedigree filter kills the application
COMPANY_TIERS = {
    "tier1": {
        "score": 100.0,
        "label": "In-league mid-market / Utah tech",
        "companies": [
            # Utah tech ecosystem (Sean lives here, easy onsite/hybrid)
            "qualtrics", "pluralsight", "domo", "lucid", "weave", "pattern",
            "bamboohr", "podium", "ancestry", "mx", "health catalyst", "recursion",
            "owlet", "vivint", "smartrent", "veritone", "divvy", "bill.com",
            "press ganey", "instructure", "canopy", "entrata", "younique",
            "route", "filevine", "neighbor", "homie", "alianza", "cotopaxi",
            # Mid-market IoT / wireless / industrial that match his domain
            "particle", "samsara", "verkada", "memfault", "blues wireless",
            "soracom", "swift navigation", "augury", "tulip", "fictiv",
            "fortive", "rockwell", "honeywell", "emerson", "schneider electric",
            # Series B-D B2B SaaS in his sweet spot
            "gong", "outreach", "salesloft", "drift", "lattice", "deel",
            "rippling", "vanta", "secureframe", "drata", "ironclad",
        ],
    },
    "tier2": {
        "score": 75.0,
        "label": "Recognized brand / Sean is a stretch",
        "companies": [
            "hubspot", "zendesk", "workday", "servicenow", "okta",
            "crowdstrike", "zscaler", "datadog", "cloudflare", "elastic",
            "asana", "coupa", "docusign", "splunk", "hashicorp",
            "twilio", "segment", "amplitude", "intercom", "linear", "notion",
            "brex", "ramp", "retool",
        ],
    },
    "tier4_pedigree_filter": {
        "score": 25.0,
        "label": "FAANG / big-tech (pedigree filter — Sean screened out)",
        "companies": [
            "netflix", "google", "meta", "apple", "amazon", "microsoft",
            "stripe", "openai", "anthropic", "deepmind", "nvidia", "tesla",
            "linkedin", "salesforce", "uber", "airbnb", "palantir", "snowflake",
            "databricks", "figma", "vercel", "github", "shopify",
            "square", "block", "roku",
        ],
    },
}
COMPANY_TIER_DEFAULT_SCORE = 65.0  # unknown / small co — neutral, no penalty

# ── Fit scoring weights — 8 dimensions, sum = 1.0 ────────────────────────────
# Comp stays the dominant signal (CRO verdict). Company tier is new — FAANG
# pays 2× and it's correlated with role quality. Effort matters because a
# 20-field Taleo portal has a real opportunity cost.
FIT_SCORE_WEIGHTS = {
    "comp":               0.28,  # still dominant, but FAANG-tier comp now correlates with pedigree-filter loss
    "company_tier":       0.20,  # bumped — in-league vs out-of-league is the #1 hidden signal
    "skill_match":        0.22,
    "title_match":        0.12,
    "remote":             0.06,
    "application_effort": 0.02,  # dropped from 0.04 to make room for freshness
    "seniority_fit":      0.05,
    "culture_fit":        0.01,  # dropped from 0.03 to make room for freshness
    "freshness":          0.04,  # new (m005): stale postings rarely convert
}

# ── Score → letter grade thresholds ──────────────────────────────────────────
SCORE_GRADE_THRESHOLDS = [
    (85, "A"),  # apply immediately after tailoring
    (70, "B"),  # tailor + review together
    (55, "C"),  # only if Sean explicitly asks
    (40, "D"),  # skip
]
# Below lowest threshold → "F"

# ── Paths ─────────────────────────────────────────────────────────────────────
PROFILE_YAML_PATH = "config/profile.yml"
GENERATED_RESUMES_DIR = "data/resumes/generated"
RESUME_TEMPLATE_PATH = "data/resume_template.html"
RECRUITER_TEMPLATE_PATH = "data/resume_template_recruiter.html"
COVER_TEMPLATE_PATH = "data/cover_letter_template.html"
TEMPLATE_DIR = "data"  # base for Jinja2 FileSystemLoader; also the Weasyprint base_url scope

# Network-scan + onboarding paths
LINKEDIN_CONNECTIONS_CSV = "data/network/linkedin_connections.csv"
NETWORK_DATA_DIR = "data/network"
ONBOARDING_DIR = "data/onboarding"
ONBOARDING_MARKER = "data/onboarding/.completed"
ONBOARDING_RAW_RESUME = "data/onboarding/raw_resume.txt"

# ── Offer-math economic constants (consumed by careerops/offer_math.py) ──────
# Annual base-bump assumption for 3-yr TC projections — industry mid-tenure norm.
ANNUAL_BASE_BUMP = 1.04
# Default vesting schedule when an offer row leaves rsu_vesting_schedule blank.
DEFAULT_VEST_SCHEDULE = "25/25/25/25"
# Top-marginal / flat-equivalent state income tax (approximation, NOT advice).
# Sean confirms with a CPA on real numbers — surfaced as such in modes/ofertas.md.
STATE_TAX_RATES = {
    "CA": 0.093,
    "NY": 0.0685,
    "OR": 0.099,
    "MN": 0.0985,
    "NJ": 0.0897,
    "MA": 0.05,
    "CO": 0.0444,
    "UT": 0.0465,
    "ID": 0.058,
    "AZ": 0.025,
    "WA": 0.0,
    "TX": 0.0,
    "FL": 0.0,
    "NV": 0.0,
    "TN": 0.0,
    "WY": 0.0,
    "SD": 0.0,
    "AK": 0.0,
    "NH": 0.0,
}


# ── Disqualifiers ──────────────────────────────────────────────────────────────
# Mirrors `careerops/disqualifiers.py` — keep in lockstep when editing.
# Hand-editable rule list; the regex logic lives in disqualifiers.py.

DISQUALIFIER_PATTERNS: list[tuple[str, str]] = [
    (r"\b(secret|top.secret|ts/sci|public trust)\s+clearance", "clearance_required"),
    (r"\b(ITAR|22\s*CFR\s*120|22\s*CFR\s*121|export\s+controlled)\b", "itar_restricted"),
    (r"(BS|Bachelor'?s?|MS|Master'?s?|B\.S\.|M\.S\.)\s+(degree\s+)?(in|of)\s+(Computer Science|CS|Software Engineering|Electrical Engineering|Mechanical Engineering|Materials Science|Chemical Engineering)\s+(is\s+)?required", "degree_required"),
]

DOMAIN_PENALTY_RULES: list[tuple[str, str, int]] = [
    (r"\b(Microsoft\s+stack|Azure|\.NET|C#|Power\s+Platform|Power\s+BI|Dynamics\s+365|D365)", "msft_stack_mismatch", -20),
    (r"\b(cybersecurity|infosec|SIEM|SOC|threat\s+intel|penetration|red\s+team|blue\s+team|zero\s+trust)\b", "narrow_security_domain", -20),
]
