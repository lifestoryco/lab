"""SQLite pipeline — application tracking CRUD and Rich dashboard.

State machine adapted from santifer/career-ops (translated to English):
  discovered → scored → resume_generated → applied → responded →
  contact → interviewing → offer | rejected | withdrawn | no_apply | closed
"""

import sqlite3
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from config import DB_PATH, MIN_BASE_SALARY

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
    with _conn() as conn:
        cur = conn.execute("""
            INSERT INTO roles (url, title, company, location, remote, lane,
                               comp_min, comp_max, comp_source, fit_score,
                               source, jd_raw, discovered_at, updated_at)
            VALUES (:url, :title, :company, :location, :remote, :lane,
                    :comp_min, :comp_max, :comp_source, :fit_score,
                    :source, :jd_raw, :discovered_at, :updated_at)
            ON CONFLICT(url) DO UPDATE SET
                title       = COALESCE(excluded.title, roles.title),
                company     = COALESCE(excluded.company, roles.company),
                location    = COALESCE(excluded.location, roles.location),
                remote      = excluded.remote,
                comp_min    = COALESCE(excluded.comp_min, roles.comp_min),
                comp_max    = COALESCE(excluded.comp_max, roles.comp_max),
                comp_source = COALESCE(excluded.comp_source, roles.comp_source),
                fit_score   = COALESCE(excluded.fit_score, roles.fit_score),
                source      = COALESCE(excluded.source, roles.source),
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


def update_jd_raw(role_id: int, jd: str) -> None:
    with _conn() as conn:
        conn.execute(
            "UPDATE roles SET jd_raw = ?, updated_at = ? WHERE id = ?",
            (jd, datetime.now(timezone.utc).isoformat(timespec="seconds"), role_id),
        )


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

    table = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold cyan")
    table.add_column("ID", style="dim", width=4)
    table.add_column("Status", width=16)
    table.add_column("Lane", width=22)
    table.add_column("Company", width=20)
    table.add_column("Title", width=36)
    table.add_column("Comp", width=14)
    table.add_column("Fit", justify="right", width=5)

    for r in active:
        if r["comp_min"]:
            comp = f"${r['comp_min']//1000}K"
            if r["comp_max"]:
                comp += f"–${r['comp_max']//1000}K"
        else:
            comp = "—"
        fit = f"{r['fit_score']:.0f}" if r["fit_score"] is not None else "—"
        fit_color = "green" if r["fit_score"] and r["fit_score"] >= 75 else ("yellow" if r["fit_score"] and r["fit_score"] >= 55 else "red")
        table.add_row(
            str(r["id"]),
            r["status"] or "",
            r["lane"] or "",
            (r["company"] or "")[:20],
            (r["title"] or "")[:36],
            comp,
            f"[{fit_color}]{fit}[/{fit_color}]",
        )

    console.print(table)
