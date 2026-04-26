"""SQLite pipeline — application tracking CRUD and Rich dashboard.

State machine adapted from santifer/career-ops (translated to English):
  discovered → scored → resume_generated → applied → responded →
  contact → interviewing → offer | rejected | withdrawn | no_apply | closed
"""

import sqlite3
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from config import DB_PATH, MIN_BASE_SALARY, LANES


def _is_quarantined(lane: str | None) -> bool:
    """A lane is quarantined when it's the explicit 'out_of_band' marker OR
    is not one of the four current archetypes (e.g. a removed legacy lane,
    typo, or stale-import value). Both produce composite=0/grade=F in
    score_breakdown — the DB write paths must keep fit_score in lockstep so
    a re-upsert or update_lane cannot silently resurrect a stale score."""
    return lane == "out_of_band" or lane not in LANES

STATUSES = [
    "discovered",         # just scraped; not yet scored
    "scored",             # fit score computed
    "resume_generated",   # lane-tailored resume written to disk
    "applied",            # Sean submitted the application
    "responded",          # recruiter responded (positive or negative pending)
    "contact",            # phone screen scheduled
    "interviewing",       # loop in progress
    "offer",              # offer extended
    "rejected",           # company passed
    "withdrawn",          # Sean withdrew
    "no_apply",           # Sean decided not to apply
    "closed",             # terminal archive
]

TERMINAL_STATUSES = {"offer", "rejected", "withdrawn", "no_apply", "closed"}


def _conn() -> sqlite3.Connection:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create the roles table on a fresh DB and apply every migration in order.

    Migrations are idempotent and tracked in `schema_migrations`, so calling
    this on an already-up-to-date DB is cheap. Side-effect: any DB created
    after this point ships every table the modes expect (offers, connections,
    outreach, contact_role/target_role_id columns) without a manual setup
    step — fixes the 'no such table: outreach' class of fresh-DB errors.
    """
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS roles (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                url           TEXT UNIQUE NOT NULL,
                title         TEXT,
                company       TEXT,
                location      TEXT,
                remote        INTEGER DEFAULT 0,
                lane          TEXT,
                comp_min      INTEGER,
                comp_max      INTEGER,
                comp_source   TEXT,
                fit_score     REAL,
                status        TEXT DEFAULT 'discovered',
                source        TEXT,
                jd_raw        TEXT,
                jd_parsed     TEXT,
                notes         TEXT,
                discovered_at TEXT,
                updated_at    TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_roles_status ON roles(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_roles_lane   ON roles(lane)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_roles_fit    ON roles(fit_score)")

    # Ordered, idempotent migrations. Late import to avoid a circular pull
    # (scripts.migrations.m###_*.py modules import config which is fine, but
    # keep the cost off the careerops.pipeline import path).
    try:
        from scripts.migrations import run_all
        run_all(DB_PATH)
    except ImportError:
        # Tests may run with scripts/ off sys.path; the modes that need
        # post-roles tables can call run_all() themselves or the migration
        # CLI directly. Don't fail init_db on missing migration runner.
        pass


def upsert_role(role: dict) -> int:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    payload = {
        "url": role.get("url"),
        "title": role.get("title"),
        "company": role.get("company"),
        "location": role.get("location"),
        "remote": int(role.get("remote") or 0),
        "lane": role.get("lane"),
        "comp_min": role.get("comp_min"),
        "comp_max": role.get("comp_max"),
        "comp_source": role.get("comp_source"),
        "fit_score": role.get("fit_score"),
        "source": role.get("source"),
        "jd_raw": role.get("jd_raw"),
        "discovered_at": now,
        "updated_at": now,
    }
    # Build the quarantine predicate from the live LANES set so removed legacy
    # archetype ids (cox-style-tpm, titanx-style-pm, …) sink to 0 alongside
    # the explicit 'out_of_band' marker. Mirrors score_breakdown's `lane not
    # in LANES` rule so the resurrection bug stays closed for both legacy
    # lane names AND any new typo that bypasses the LANES whitelist.
    valid_lanes_sql = ",".join(f"'{l}'" for l in LANES.keys())
    with _conn() as conn:
        cur = conn.execute(f"""
            INSERT INTO roles (url, title, company, location, remote, lane,
                               comp_min, comp_max, comp_source, fit_score,
                               source, jd_raw, discovered_at, updated_at)
            VALUES (:url, :title, :company, :location, :remote, :lane,
                    :comp_min, :comp_max, :comp_source, :fit_score,
                    :source, :jd_raw, :discovered_at, :updated_at)
            ON CONFLICT(url) DO UPDATE SET
                -- NULLIF so an empty-string excluded value doesn't overwrite a
                -- populated stored one (matches network_scrape.upsert_scraped).
                title       = COALESCE(NULLIF(excluded.title,    ''), roles.title),
                company     = COALESCE(NULLIF(excluded.company,  ''), roles.company),
                location    = COALESCE(NULLIF(excluded.location, ''), roles.location),
                remote      = excluded.remote,
                comp_min    = COALESCE(excluded.comp_min, roles.comp_min),
                comp_max    = COALESCE(excluded.comp_max, roles.comp_max),
                comp_source = COALESCE(NULLIF(excluded.comp_source, ''), roles.comp_source),
                -- Quarantine sink: lane outside the current 4 archetypes
                -- (or the explicit 'out_of_band') keeps fit_score at 0 so
                -- re-discovery can't resurrect a stale score.
                fit_score   = CASE
                                WHEN roles.lane = 'out_of_band'
                                  OR roles.lane NOT IN ({valid_lanes_sql})
                                THEN 0
                                ELSE COALESCE(excluded.fit_score, roles.fit_score)
                              END,
                source      = COALESCE(NULLIF(excluded.source, ''), roles.source),
                updated_at  = excluded.updated_at
        """, payload)
        return cur.lastrowid or _role_id_by_url(conn, payload["url"])


def _role_id_by_url(conn: sqlite3.Connection, url: str) -> int:
    row = conn.execute("SELECT id FROM roles WHERE url = ?", (url,)).fetchone()
    return int(row["id"]) if row else 0


def upsert_roles(roles: list[dict]) -> list[int]:
    return [upsert_role(r) for r in roles]


def get_role(role_id: int) -> dict | None:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM roles WHERE id = ?", (role_id,)).fetchone()
        return dict(row) if row else None


def list_roles(status: str | None = None, lane: str | None = None, limit: int = 50) -> list[dict]:
    sql = "SELECT * FROM roles WHERE 1=1"
    args: list = []
    if status:
        sql += " AND status = ?"
        args.append(status)
    if lane:
        sql += " AND lane = ?"
        args.append(lane)
    sql += " ORDER BY fit_score DESC NULLS LAST, updated_at DESC LIMIT ?"
    args.append(limit)
    with _conn() as conn:
        return [dict(r) for r in conn.execute(sql, args).fetchall()]


def update_status(role_id: int, status: str, note: str | None = None) -> None:
    if status not in STATUSES:
        raise ValueError(f"Invalid status '{status}'. Must be one of: {STATUSES}")
    with _conn() as conn:
        if note:
            conn.execute(
                "UPDATE roles SET status = ?, notes = COALESCE(notes,'') || ? || char(10), updated_at = ? WHERE id = ?",
                (status, f"[{datetime.now(timezone.utc).date()} {status}] {note}",
                 datetime.now(timezone.utc).isoformat(timespec="seconds"), role_id),
            )
        else:
            conn.execute(
                "UPDATE roles SET status = ?, updated_at = ? WHERE id = ?",
                (status, datetime.now(timezone.utc).isoformat(timespec="seconds"), role_id),
            )


def update_fit_score(role_id: int, score: float) -> None:
    with _conn() as conn:
        conn.execute(
            "UPDATE roles SET fit_score = ?, status = CASE WHEN status = 'discovered' THEN 'scored' ELSE status END, updated_at = ? WHERE id = ?",
            (score, datetime.now(timezone.utc).isoformat(timespec="seconds"), role_id),
        )


def update_jd_parsed(role_id: int, parsed: dict) -> None:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with _conn() as conn:
        conn.execute(
            "UPDATE roles SET jd_parsed = ?, updated_at = ? WHERE id = ?",
            (json.dumps(parsed), now, role_id),
        )
        if parsed.get("comp_explicit") and parsed.get("comp_min"):
            conn.execute(
                "UPDATE roles SET comp_min = ?, comp_max = ?, comp_source = 'explicit', updated_at = ? WHERE id = ?",
                (parsed["comp_min"], parsed.get("comp_max"), now, role_id),
            )


def update_lane(role_id: int, lane: str) -> None:
    """Reassign a role to a different lane. Used by auto-pipeline after
    score_title picks the best-matching archetype, and by migrations.
    Any lane outside the current 4 archetypes (or the explicit 'out_of_band'
    marker) forces fit_score to 0 — keeps the quarantine sink in lockstep
    with score_breakdown's `lane not in LANES` rule, so a typo or legacy
    lane name (cox-style-tpm, etc.) cannot leave a stale score behind."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with _conn() as conn:
        if _is_quarantined(lane):
            conn.execute(
                "UPDATE roles SET lane = ?, fit_score = 0, updated_at = ? WHERE id = ?",
                (lane, now, role_id),
            )
        else:
            conn.execute(
                "UPDATE roles SET lane = ?, updated_at = ? WHERE id = ?",
                (lane, now, role_id),
            )


def update_role_notes(role_id: int, note: str, append: bool = True) -> None:
    """Add a note to the role's notes field. Default behavior: append with
    timestamp + newline. Pass append=False to overwrite (rarely correct)."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    stamp = datetime.now(timezone.utc).date().isoformat()
    with _conn() as conn:
        if append:
            conn.execute(
                "UPDATE roles SET notes = COALESCE(notes,'') || ? || char(10), updated_at = ? WHERE id = ?",
                (f"[{stamp}] {note}", now, role_id),
            )
        else:
            conn.execute(
                "UPDATE roles SET notes = ?, updated_at = ? WHERE id = ?",
                (note, now, role_id),
            )


def update_jd_raw(role_id: int, jd: str) -> None:
    with _conn() as conn:
        conn.execute(
            "UPDATE roles SET jd_raw = ?, updated_at = ? WHERE id = ?",
            (jd, datetime.now(timezone.utc).isoformat(timespec="seconds"), role_id),
        )


def insert_offer(offer: dict) -> int:
    """Insert a row into offers (created by migration m002).

    Required keys: company, title, base_salary. received_at defaults to today.
    Raises ValueError with a concrete field list if anything required is missing.
    Returns the new offer id.
    """
    required = ("company", "title", "base_salary")
    missing = [k for k in required if not offer.get(k)]
    if missing:
        raise ValueError(f"insert_offer missing required keys: {missing}")
    all_cols = [
        "role_id", "company", "title", "received_at", "expires_at",
        "base_salary", "signing_bonus", "annual_bonus_target_pct",
        "annual_bonus_paid_history", "rsu_total_value", "rsu_vesting_schedule",
        "rsu_vest_years", "rsu_cliff_months", "equity_refresh_expected",
        "benefits_delta", "pto_days", "remote_pct", "state_tax",
        "growth_signal", "notes", "status",
    ]
    payload = dict(offer)
    if not payload.get("received_at"):
        payload["received_at"] = datetime.now(timezone.utc).date().isoformat()
    # Only insert columns the caller actually set so the schema's DEFAULT
    # values (status='active', signing_bonus=0, rsu_vest_years=4, etc.) apply.
    cols = [c for c in all_cols if payload.get(c) is not None]
    # Defence-in-depth: even though `cols` is filtered through the all_cols
    # whitelist above, assert membership before interpolation so a future
    # contributor can't widen the source without re-checking.
    assert set(cols).issubset(all_cols), f"insert_offer column drift: {set(cols) - set(all_cols)}"
    vals = [payload[c] for c in cols]
    placeholders = ",".join("?" * len(cols))
    with _conn() as conn:
        cur = conn.execute(
            f"INSERT INTO offers ({','.join(cols)}) VALUES ({placeholders})",
            vals,
        )
        return cur.lastrowid


def list_offers(status: str | None = "active") -> list[dict]:
    """List offers (default active). Returns dicts (sqlite Row → dict)."""
    with _conn() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM offers WHERE status = ? ORDER BY received_at DESC",
                (status,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM offers ORDER BY received_at DESC"
            ).fetchall()
    return [dict(r) for r in rows]


def insert_market_anchor(
    company: str,
    title: str,
    base_salary: int,
    *,
    rsu_total_value: int = 0,
    annual_bonus_target_pct: float = 0.0,
    state_tax: str = "UT",
    source: str = "Levels.fyi",
    notes: str | None = None,
) -> int:
    """Insert a synthetic 'market_anchor' offer for ofertas comparison.

    When Sean has only one real offer, he can capture a market-comp band
    (typically from Levels.fyi for the same company + role + level) as a
    synthetic offer and use it as the negotiation anchor. The
    `status='market_anchor'` value keeps these out of `list_offers()`'s
    default `'active'` filter so they don't pollute the real-offer set.

    Required: company, title, base_salary (the median or P50 from the
    market source). RSU + bonus default to 0 because Levels.fyi reports
    are usually for established companies where RSU is a moving target;
    Sean can fill them in later if useful.
    """
    if not company or not title or not base_salary:
        raise ValueError("insert_market_anchor requires company, title, base_salary")
    full_notes = f"market_anchor source={source}"
    if notes:
        full_notes += f" | {notes}"
    return insert_offer({
        "company": company,
        "title": title,
        "base_salary": int(base_salary),
        "rsu_total_value": int(rsu_total_value),
        "annual_bonus_target_pct": float(annual_bonus_target_pct),
        "rsu_vesting_schedule": "25/25/25/25",
        "rsu_vest_years": 4,
        "rsu_cliff_months": 12,
        "state_tax": state_tax,
        "growth_signal": f"market_anchor:{source}",
        "notes": full_notes,
        "status": "market_anchor",
    })


def list_market_anchors() -> list[dict]:
    """List synthetic market-anchor offers (Levels.fyi etc.)."""
    return list_offers(status="market_anchor")


# ── Outreach + connections helpers (added by m004) ───────────────────────────

VALID_CONTACT_ROLES = (
    "hiring_manager",
    "team_member",
    "recruiter",
    "exec_sponsor",
    "alumni_intro",
)


def tag_outreach_role(
    outreach_id: int,
    contact_role: str,
    target_role_id: int | None = None,
) -> None:
    """Mark an outreach row's relationship to its target role.

    `contact_role` must be one of VALID_CONTACT_ROLES. Used by network-scan
    to record (when Sean confirms) that a contact is the hiring manager
    for the role we're scanning for; cover-letter mode reads this tag to
    auto-populate `recipient_name`.
    """
    if contact_role not in VALID_CONTACT_ROLES:
        raise ValueError(
            f"contact_role must be one of {VALID_CONTACT_ROLES}; got {contact_role!r}"
        )
    with _conn() as conn:
        if target_role_id is not None:
            conn.execute(
                "UPDATE outreach SET contact_role = ?, target_role_id = ? WHERE id = ?",
                (contact_role, target_role_id, outreach_id),
            )
        else:
            conn.execute(
                "UPDATE outreach SET contact_role = ? WHERE id = ?",
                (contact_role, outreach_id),
            )


def find_hiring_manager_for_role(role_id: int) -> dict | None:
    """Return the connection row tagged as the role's hiring_manager, or None.

    Joins outreach (filtered to contact_role='hiring_manager' for the
    role) with connections. If multiple matches exist (Sean tagged more
    than one), returns the most recently drafted outreach's connection.
    """
    with _conn() as conn:
        # Confirm both tables exist (outreach + the m004 contact_role column)
        # before querying — surfaces a clear error instead of a sqlite syntax one.
        tables = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        if "outreach" not in tables or "connections" not in tables:
            return None
        outreach_cols = {
            r[1] for r in conn.execute("PRAGMA table_info(outreach)").fetchall()
        }
        if "contact_role" not in outreach_cols:
            return None
        row = conn.execute(
            """
            SELECT c.*, o.contact_role AS contact_role_tag
            FROM outreach o
            JOIN connections c ON c.id = o.connection_id
            WHERE (o.role_id = ? OR o.target_role_id = ?)
              AND o.contact_role = 'hiring_manager'
            ORDER BY o.drafted_at DESC
            LIMIT 1
            """,
            (role_id, role_id),
        ).fetchone()
    return dict(row) if row else None


def summary() -> dict:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT status, COUNT(*) AS n FROM roles GROUP BY status"
        ).fetchall()
        comp_row = conn.execute(
            "SELECT SUM(COALESCE(comp_min, 0)) AS floor FROM roles WHERE status NOT IN ('closed','rejected','withdrawn','no_apply')"
        ).fetchone()
        recent_row = conn.execute(
            "SELECT SUM(COALESCE(comp_min, 0)) AS floor FROM roles WHERE discovered_at >= ?",
            ((datetime.now(timezone.utc) - timedelta(days=7)).isoformat(timespec="seconds"),),
        ).fetchone()
    counts = {r["status"]: r["n"] for r in rows}
    return {
        "counts": counts,
        "total": sum(counts.values()),
        "active_comp_floor": int(comp_row["floor"] or 0),
        "week_comp_floor": int(recent_row["floor"] or 0),
    }


def dashboard() -> None:
    """Print a Rich Bloomberg-style dashboard to stdout."""
    from rich.console import Console
    from rich.table import Table
    from rich import box
    from rich.panel import Panel

    console = Console()
    stats = summary()

    header = (
        f"[bold]Coin Pipeline[/bold]   "
        f"Total: {stats['total']}   "
        f"Active comp floor: [green]${stats['active_comp_floor']:,}[/green]   "
        f"Last 7d floor: [cyan]${stats['week_comp_floor']:,}[/cyan]"
    )
    console.print(Panel(header, box=box.HEAVY, border_style="cyan"))

    counts = stats["counts"]
    if counts:
        status_line = "  ".join(
            f"[dim]{s}:[/dim] {counts.get(s, 0)}" for s in STATUSES if counts.get(s)
        )
        console.print(f"  {status_line}\n")

    with _conn() as conn:
        active = conn.execute("""
            SELECT * FROM roles
            WHERE status NOT IN ('offer','rejected','withdrawn','no_apply','closed')
            ORDER BY fit_score DESC NULLS LAST, updated_at DESC
            LIMIT 20
        """).fetchall()

    if not active:
        console.print("[yellow]Pipeline empty — run `/coin` to discover roles.[/yellow]")
        return

    from careerops.score import score_grade

    table = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold cyan")
    table.add_column("ID", style="dim", width=4)
    table.add_column("Status", width=16)
    table.add_column("Lane", width=22)
    table.add_column("Company", width=20)
    table.add_column("Title", width=34)
    table.add_column("Comp", width=14)
    table.add_column("Fit", justify="right", width=5)
    table.add_column("Grade", justify="center", width=5)

    for r in active:
        if r["comp_min"]:
            comp = f"${r['comp_min']//1000}K"
            if r["comp_max"]:
                comp += f"–${r['comp_max']//1000}K"
        else:
            comp = "—"
        fit_val = r["fit_score"]
        fit = f"{fit_val:.0f}" if fit_val is not None else "—"
        grade = score_grade(fit_val) if fit_val is not None else "—"
        fit_color = "green" if fit_val and fit_val >= 70 else ("yellow" if fit_val and fit_val >= 55 else "red")
        grade_color = {"A": "bold green", "B": "green", "C": "yellow", "D": "red", "F": "dim red"}.get(grade, "dim")
        table.add_row(
            str(r["id"]),
            r["status"] or "",
            r["lane"] or "",
            (r["company"] or "")[:20],
            (r["title"] or "")[:34],
            comp,
            f"[{fit_color}]{fit}[/{fit_color}]",
            f"[{grade_color}]{grade}[/{grade_color}]",
        )

    console.print(table)
