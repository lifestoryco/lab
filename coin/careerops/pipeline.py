"""SQLite pipeline — application tracking CRUD."""

import sqlite3
import json
from datetime import datetime
from config import DB_PATH

STATUSES = [
    "discovered",
    "resume_generated",
    "applied",
    "screening",
    "interviewing",
    "offer",
    "closed",
]


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS roles (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                url         TEXT UNIQUE NOT NULL,
                title       TEXT,
                company     TEXT,
                location    TEXT,
                remote      INTEGER DEFAULT 0,
                lane        TEXT,
                comp_min    INTEGER,
                comp_max    INTEGER,
                comp_source TEXT,
                fit_score   REAL,
                status      TEXT DEFAULT 'discovered',
                jd_raw      TEXT,
                jd_parsed   TEXT,
                notes       TEXT,
                discovered_at TEXT,
                updated_at  TEXT
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_roles_status ON roles(status)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_roles_lane ON roles(lane)
        """)


def upsert_role(role: dict) -> int:
    now = datetime.utcnow().isoformat()
    with _conn() as conn:
        cur = conn.execute("""
            INSERT INTO roles (url, title, company, location, remote, lane,
                               comp_min, comp_max, comp_source, fit_score,
                               jd_raw, discovered_at, updated_at)
            VALUES (:url, :title, :company, :location, :remote, :lane,
                    :comp_min, :comp_max, :comp_source, :fit_score,
                    :jd_raw, :discovered_at, :updated_at)
            ON CONFLICT(url) DO UPDATE SET
                title       = excluded.title,
                company     = excluded.company,
                comp_min    = excluded.comp_min,
                comp_max    = excluded.comp_max,
                comp_source = excluded.comp_source,
                fit_score   = excluded.fit_score,
                updated_at  = excluded.updated_at
        """, {**role, "discovered_at": now, "updated_at": now})
        return cur.lastrowid


def upsert_roles(roles: list[dict]) -> list[int]:
    return [upsert_role(r) for r in roles]


def get_role(role_id: int) -> dict | None:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM roles WHERE id = ?", (role_id,)).fetchone()
        return dict(row) if row else None


def update_status(role_id: int, status: str) -> None:
    if status not in STATUSES:
        raise ValueError(f"Invalid status '{status}'. Must be one of: {STATUSES}")
    with _conn() as conn:
        conn.execute(
            "UPDATE roles SET status = ?, updated_at = ? WHERE id = ?",
            (status, datetime.utcnow().isoformat(), role_id),
        )


def update_jd_parsed(role_id: int, parsed: dict) -> None:
    with _conn() as conn:
        conn.execute(
            "UPDATE roles SET jd_parsed = ?, updated_at = ? WHERE id = ?",
            (json.dumps(parsed), datetime.utcnow().isoformat(), role_id),
        )


def summary() -> str:
    with _conn() as conn:
        rows = conn.execute("""
            SELECT status, COUNT(*) as n FROM roles GROUP BY status
        """).fetchall()
        if not rows:
            return "Pipeline empty — run /coin-search to discover roles"
        parts = [f"{r['status']}: {r['n']}" for r in rows]
        return " | ".join(parts)


def dashboard() -> str:
    from rich.console import Console
    from rich.table import Table
    from rich import box

    with _conn() as conn:
        active = conn.execute("""
            SELECT * FROM roles
            WHERE status NOT IN ('closed', 'offer')
            ORDER BY fit_score DESC NULLS LAST
        """).fetchall()
        offers = conn.execute("""
            SELECT * FROM roles WHERE status IN ('offer', 'closed')
            ORDER BY updated_at DESC LIMIT 10
        """).fetchall()

    console = Console()
    table = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold cyan")
    table.add_column("ID", style="dim", width=4)
    table.add_column("Status", width=18)
    table.add_column("Company", width=20)
    table.add_column("Title", width=30)
    table.add_column("Comp", width=20)
    table.add_column("Fit", width=6)

    for r in active:
        comp = f"${r['comp_min']//1000}K–${r['comp_max']//1000}K" if r["comp_min"] else "unverified"
        fit = f"{r['fit_score']:.0f}" if r["fit_score"] else "—"
        table.add_row(str(r["id"]), r["status"] or "", r["company"] or "", r["title"] or "", comp, fit)

    console.print(table)
    return ""
