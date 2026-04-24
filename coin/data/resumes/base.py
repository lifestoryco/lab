"""Sean's canonical professional data model. Single source of truth for all resume outputs."""

PROFILE = {
    "name": "Sean Ivins",
    "credentials": ["PMP", "MBA"],
    "title": "Senior Technical Program Manager",
    "years_experience": 15,
    "email": "sean@lifestory.co",
    "domains": ["wireless infrastructure", "IoT systems", "B2B SaaS", "aerospace/defense", "RF/wireless"],
    "methodologies": ["Agile", "Waterfall", "Requirement Decomposition", "Cross-Functional Orchestration"],

    "skills": [
        "technical program management", "product management", "program execution",
        "cross-functional orchestration", "stakeholder management", "roadmap development",
        "requirement decomposition", "agile", "scrum", "waterfall", "pmp",
        "B2B SaaS", "IoT", "RF", "wireless", "5G", "LTE",
        "revenue growth", "ARR growth", "go-to-market", "enterprise sales",
        "series A", "fractional COO", "P&L ownership", "executive communication",
        "global team management", "vendor management", "technical sales",
        "solutions engineering", "account management", "Python", "SQL",
    ],

    "stories": [
        {
            "id": "cox_true_local_labs",
            "company": "Cox Communications",
            "role": "Technical Program Manager",
            "headline": "Managed complete program execution for True Local Labs",
            "bullets": [
                "Led concept-to-production delivery of True Local Labs, Cox's IoT platform, 12 months ahead of schedule",
                "Drove $1M+ Year 1 revenue within first year of launch",
                "Orchestrated cross-functional teams across engineering, product, and commercial functions",
                "Defined and decomposed requirements across hardware, software, and cloud layers",
            ],
            "metrics": {"revenue": "$1M Year 1", "schedule": "12 months ahead of plan"},
            "tags": ["program management", "IoT", "cross-functional", "product launch", "revenue"],
        },
        {
            "id": "titanx_fractional_coo",
            "company": "TitanX",
            "role": "Fractional COO",
            "headline": "Scaled sales intelligence platform to $27M Series A",
            "bullets": [
                "Served as fractional COO, building operational infrastructure for a B2B SaaS sales intelligence platform",
                "Helped scale the company to $27M Series A in under 2 years",
                "Defined go-to-market strategy, operational cadences, and cross-functional execution model",
                "Built and managed executive reporting and investor-facing metrics",
            ],
            "metrics": {"funding": "$27M Series A", "timeline": "under 2 years"},
            "tags": ["B2B SaaS", "series A", "fractional COO", "go-to-market", "scaling", "product"],
        },
        {
            "id": "utah_broadband_acquisition",
            "company": "Utah Broadband",
            "role": "Senior Leader",
            "headline": "Drove revenue growth culminating in $27M acquisition",
            "bullets": [
                "Led operational and commercial growth initiatives for a regional broadband provider",
                "Drove revenue growth that positioned the company for acquisition",
                "Company acquired by Boston Omaha Corporation for $27M",
            ],
            "metrics": {"acquisition": "$27M by Boston Omaha Corporation"},
            "tags": ["broadband", "wireless", "revenue growth", "acquisition", "telecom"],
        },
        {
            "id": "arr_growth_6m_to_13m",
            "company": "Enterprise Account Manager role",
            "role": "Enterprise Account Manager",
            "headline": "Grew ARR from $6M to $13M",
            "bullets": [
                "Managed and expanded a $6M enterprise book of business to $13M ARR",
                "Sourced and closed new enterprise logos in B2B SaaS verticals",
                "Built executive relationships across technical and business stakeholders",
            ],
            "metrics": {"arr_start": "$6M", "arr_end": "$13M", "growth": "117%"},
            "tags": ["ARR", "enterprise sales", "account management", "B2B SaaS", "revenue"],
        },
        {
            "id": "global_engineering_orchestration",
            "company": "Multiple engagements",
            "role": "Technical Program Manager",
            "headline": "Orchestrated global engineering teams across continents",
            "bullets": [
                "Coordinated engineering execution across distributed teams in North America, Europe, and Asia",
                "Implemented cross-timezone delivery cadences using Agile and hybrid methodologies",
                "Maintained schedule integrity and quality across multi-continent programs",
            ],
            "metrics": {},
            "tags": ["global teams", "distributed engineering", "program management", "agile"],
        },
    ],

    "education": [
        {"degree": "MBA", "institution": ""},
        {"degree": "BS", "field": "Technical / Engineering", "institution": ""},
    ],

    "certifications": ["PMP (Project Management Professional)"],

    "target_comp_min_base": 180000,
    "target_locations": ["Remote", "Salt Lake City", "San Francisco", "New York", "Austin"],
}
