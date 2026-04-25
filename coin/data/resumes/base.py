"""Sean's canonical professional data model. Single source of truth for all resume outputs.

Mirrors the structure of the Ford v1.0 resume (data/inputs/resumes/Sean Ivins - Ford Resume - v1.0.docx).
Tailored resume JSON in data/resumes/generated/ overrides `executive_summary` and supplies
`top_bullets` (rendered as a "Selected Achievements" lead-in); the rest comes from here.
"""

PROFILE = {
    # ── Identity ──────────────────────────────────────────────────────────────
    "name": "Sean Ivins",
    "credentials": ["PMP", "MBA"],
    "title": "Senior Technical Program Manager",
    "city": "Salt Lake City, UT",
    "phone": "801.803.3084",
    "email": "sivins@caengineering.com",
    "linkedin": "linkedin.com/in/seanivins",
    "years_experience": 15,
    "domains": ["wireless infrastructure", "IoT systems", "B2B SaaS", "RF", "industrial"],

    # ── Default executive summary (overridden per-application by JSON) ────────
    "default_summary": (
        "Technical Program Manager with 15+ years orchestrating complex technology "
        "initiatives from concept to delivery across wireless infrastructure, IoT systems, "
        "and B2B SaaS platforms. Proven ability to synchronize distributed engineering "
        "teams across continents and deliver on aggressive timelines by eliminating the "
        "blockers that prevent alignment between technical execution and business stakeholders. "
        "MBA + PMP credentialed with expertise in Agile and Waterfall methodologies, "
        "requirement decomposition, and cross-functional program coordination."
    ),

    # ── Professional Experience (chronological, newest first) ─────────────────
    "positions": [
        {
            "id": "ca_engineering",
            "company": "CA Engineering",
            "title": "Technical Program Manager",
            "location": "Draper, UT",
            "start": "Jan 2025",
            "end": "Present",
            "summary": (
                "Client-facing technical program lead coordinating wireless and IoT product "
                "development for enterprise clients in aerospace, industrial automation, and "
                "safety-critical applications."
            ),
            "bullets": [
                "Orchestrate global engineering teams across multiple time zones for enterprise clients including aerospace OEM in-flight wireless systems, enterprise conferencing solutions for international organizations, and Fortune 500 energy company industrial sensor deployments — daily standups synchronizing hardware, firmware, and RF teams while maintaining project velocity",
                "Serve as primary liaison between client business stakeholders and distributed engineering teams, translating high-level business requirements into detailed PRDs and technical specifications while managing scope, timeline, and value communication throughout the product development lifecycle",
                "Manage technical discovery and project scoping for IoT and wireless projects spanning home automation safety systems, industrial vibration monitoring, and enterprise RF communications — coordinating cross-functional resources and establishing clear deliverables that align client objectives with engineering execution",
                "Lead revenue operations initiatives reporting to the CRO, including SOW preparation, project forecasting, CRM system development, and internal program sync meetings to align client commitments with engineering capacity and business objectives",
            ],
        },
        {
            "id": "hydrant",
            "company": "Hydrant (Software Engineering Firm)",
            "title": "Technical Program Manager | Co-Owner",
            "location": "Salt Lake City, UT",
            "start": "Jul 2019",
            "end": "Dec 2024",
            "summary": (
                "Co-owned and scaled technical delivery operations from startup to successful exit, "
                "leading B2B SaaS product development from concept to launch for venture-backed "
                "startups and enterprise clients."
            ),
            "bullets": [
                "Managed complete program execution for Cox Communications' True Local Labs, conducting daily global standups coordinating data enrichment teams across multiple continents to transform initial concept into production platform that exceeded $1M Year 1 revenue 12 months ahead of schedule",
                "Served as fractional COO for TitanX, operationalizing sales intelligence platform architecture that scaled from concept to $27M Series A funding in under 2 years through systematic process documentation and cross-functional team coordination",
                "Led mission-critical CMS migration for Safeguard Global spanning 187 countries and 1,000+ pages with 7 localizations, delivering project six weeks ahead of schedule with zero major technical incidents through daily standups and direct C-suite communication",
            ],
        },
        {
            "id": "utah_broadband",
            "company": "Utah Broadband",
            "title": "Enterprise Account Manager",
            "location": "Draper, UT",
            "start": "Apr 2013",
            "end": "Jul 2019",
            "summary": (
                "Drove revenue growth for wireless ISP during hypergrowth phase that culminated "
                "in $27M acquisition by Boston Omaha Corporation (NASDAQ: BOMN) in 2020. "
                "Coordinated technical operations between sales, engineering, and field installation teams."
            ),
            "bullets": [
                "Managed enterprise client relationships including high-capacity circuit deployments for major technology companies — conducted on-site technical assessments to assess signal strength and equipment placement, coordinated with building management and engineering teams to ensure installation requirements were met, and served as primary liaison throughout the deployment lifecycle",
                "Coordinated 15+ network expansion deployments serving as liaison between sales, RF engineering, and field installation teams to align tower site selection, capacity planning, and municipal permitting with revenue targets — supporting company growth from $6M to $13M ARR",
            ],
        },
        {
            "id": "linx",
            "company": "LINX Communications",
            "title": "IT Project Manager",
            "location": "Orem, UT",
            "start": "Jan 2011",
            "end": "Apr 2013",
            "summary": (
                "Managed national VoIP deployment supporting 100+ internal stakeholders across "
                "sales, operations, and field installation teams."
            ),
            "bullets": [
                "Implemented company-wide training procedures and SOP documentation for VoIP provisioning, SIP configuration, and PBX troubleshooting — improving first-call resolution by 40%+ and establishing the foundation for scaling enterprise telecom services to thousands of clients nationwide",
            ],
        },
    ],

    # ── Technical Skills (3-column layout matching Ford resume) ───────────────
    "skills_grid": {
        "Program Management": [
            "Agile / Waterfall Methodologies",
            "Requirement Decomposition",
            "Cross-Functional Orchestration",
            "Scope & Budget Management",
            "Technical Documentation (PRDs, SOWs)",
            "Vendor & Stakeholder Management",
            "Risk Mitigation & Change Control",
        ],
        "Technical Domain Experience": [
            "RF / Wireless (Wi-Fi, BLE, Z-Wave)",
            "IoT Product Development",
            "Manufacturing Test Development",
            "B2B SaaS Platform Development",
            "Industrial Sensor Systems",
            "Aerospace & Defense Systems",
            "Critical Infrastructure Monitoring",
        ],
        "Tools & Platforms": [
            "JIRA, MS Project, Asana, ClickUp",
            "MS Teams, Google Workspace",
            "Confluence, Trello",
            "Google Analytics, Data Studio",
            "Slack, WhatsApp, Zoom",
            "GitHub, Bitbucket",
            "HubSpot, Salesforce CRM, Odoo",
        ],
    },

    # ── Skills (flat list for keyword matching in score.py) ──────────────────
    "skills": [
        "technical program management", "program execution", "cross-functional orchestration",
        "stakeholder management", "roadmap development", "requirement decomposition",
        "agile", "scrum", "waterfall", "pmp", "B2B SaaS", "IoT", "RF", "wireless",
        "Wi-Fi", "BLE", "Z-Wave", "5G", "LTE", "embedded", "firmware",
        "revenue growth", "ARR growth", "go-to-market", "enterprise sales",
        "solutions engineering", "sales engineering", "technical sales", "presales",
        "consultative discovery", "demos", "RFP", "SOW", "PRD",
        "series A", "fractional COO", "P&L ownership", "executive communication",
        "global team management", "vendor management", "account management",
        "Salesforce", "HubSpot", "Odoo", "JIRA", "Confluence",
        "aerospace", "defense", "industrial automation", "manufacturing test",
    ],

    # ── Education & Certifications ────────────────────────────────────────────
    "education": [
        {
            "degree": "Master of Business Administration (MBA)",
            "field": "IT Project Management",
            "institution": "Western Governors University",
            "graduated": "Feb 2019",
        },
        {
            "degree": "Bachelor of Arts (BA)",
            "field": "History",
            "institution": "University of Utah",
            "graduated": "May 2013",
        },
    ],

    "certifications": [
        {
            "name": "Project Management Professional (PMP)®",
            "issuer": "Project Management Institute",
            "id": "PMI ID: 2857003",
            "valid": "Dec 2021 – Aug 2026",
        },
    ],

    # ── Story refs (used by score.py / tailoring prompts) ─────────────────────
    # Maps story id → position id so tailoring can pull the right context.
    "stories": [
        {"id": "cox_true_local_labs", "position_id": "hydrant"},
        {"id": "titanx_fractional_coo", "position_id": "hydrant"},
        {"id": "safeguard_global_cms", "position_id": "hydrant"},
        {"id": "utah_broadband_acquisition", "position_id": "utah_broadband"},
        {"id": "arr_growth_6m_to_13m", "position_id": "utah_broadband"},
        {"id": "global_engineering_orchestration", "position_id": "ca_engineering"},
    ],

    # ── Targeting (config.py is the canonical source for comp; profile.yml
    # is canonical for target_locations. These two keys remain only for
    # backward-compat with the brief PDF template's header.) ─────────────────
    "target_comp_min_base": 160000,
}


def get_target_locations() -> list[str]:
    """Single source of truth for target locations: config/profile.yml.
    base.py used to duplicate this — removed 2026-04-25 to prevent drift."""
    import yaml
    from pathlib import Path
    yml_path = Path(__file__).resolve().parent.parent.parent / "config" / "profile.yml"
    if not yml_path.exists():
        return ["Remote", "Salt Lake City"]
    data = yaml.safe_load(yml_path.read_text()) or {}
    return data.get("identity", {}).get("target_locations", ["Remote", "Salt Lake City"])
