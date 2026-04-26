#!/usr/bin/env python
"""Import a LinkedIn connections CSV into pipeline.db.

Source: LinkedIn → "Get a copy of your data" → Connections → Connections.csv
Default location: data/network/linkedin_connections.csv

Idempotent: ON CONFLICT(linkedin_url) updates the existing row. Re-running
on the same export is safe.

Schema is created on first run (also creates `outreach`, used by network-scan
for tracking which contacts have been drafted-for / sent-to / replied).

Usage:
  python scripts/import_linkedin_connections.py
  python scripts/import_linkedin_connections.py --csv path/to/Connections.csv
  python scripts/import_linkedin_connections.py --dry-run
"""

from __future__ import annotations

import argparse
import csv
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import DB_PATH, LINKEDIN_CONNECTIONS_CSV
from careerops.paths import validate_under

DEFAULT_CSV = LINKEDIN_CONNECTIONS_CSV

DDL_CONNECTIONS = """
CREATE TABLE IF NOT EXISTS connections (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name      TEXT,
    last_name       TEXT,
    full_name       TEXT,
    linkedin_url    TEXT UNIQUE,
    email           TEXT,
    company         TEXT,
    company_normalized TEXT,
    position        TEXT,
    connected_on    DATE,
    seniority       TEXT,
    last_seen       DATE,
    notes           TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_connections_company ON connections(company_normalized);
CREATE INDEX IF NOT EXISTS idx_connections_seniority ON connections(seniority);
"""

DDL_OUTREACH = """
CREATE TABLE IF NOT EXISTS outreach (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    role_id         INTEGER REFERENCES roles(id),
    connection_id   INTEGER REFERENCES connections(id),
    drafted_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sent_at         TIMESTAMP NULL,
    replied_at      TIMESTAMP NULL,
    warmth_score    REAL,
    draft_message   TEXT,
    notes           TEXT
);
CREATE INDEX IF NOT EXISTS idx_outreach_role ON outreach(role_id);
"""


_LEADERSHIP = re.compile(
    r"\b(vp|vice president|director|head of|chief|cxo|c-suite|founder|"
    r"co-?founder|partner|managing director)\b",
    re.IGNORECASE,
)
_SENIOR_IC = re.compile(
    r"\b(senior|sr\.?|principal|staff|lead\b|architect)",
    re.IGNORECASE,
)


def classify_seniority(position: str | None) -> str:
    if not position:
        return "peer"
    if _LEADERSHIP.search(position):
        return "leadership"
    if _SENIOR_IC.search(position):
        return "senior_ic"
    return "peer"


_CO_SUFFIXES = re.compile(
    r",?\s*(inc\.?|llc\.?|ltd\.?|corp\.?|co\.?|company|gmbh|s\.?a\.?|plc)\.?$",
    re.IGNORECASE,
)


def normalize_company(name: str | None) -> str:
    if not name:
        return ""
    s = name.strip().lower()
    s = _CO_SUFFIXES.sub("", s)
    s = re.sub(r"[&,]+", " ", s)
    s = re.sub(r"[^\w\s\-]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def parse_connected_on(raw: str | None) -> str | None:
    if not raw:
        return None
    raw = raw.strip()
    for fmt in ("%d %b %Y", "%d %B %Y", "%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(DDL_CONNECTIONS)
    conn.executescript(DDL_OUTREACH)


def import_csv(db_path: str | Path, csv_path: str | Path, dry_run: bool = False) -> dict:
    """Import the CSV. Returns summary dict (totals + by-seniority breakdown)."""
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        ensure_schema(conn)
        rows_processed = 0
        rows_inserted = 0
        rows_updated = 0
        seniority_counts = {"leadership": 0, "senior_ic": 0, "peer": 0}
        company_counts: dict[str, int] = {}

        with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
            # LinkedIn export prepends a "Notes:" preamble in some versions.
            # Skip until we find the header row.
            reader = csv.reader(f)
            header: list[str] | None = None
            for line in reader:
                if line and line[0].strip() == "First Name":
                    header = [h.strip() for h in line]
                    break
            if not header:
                raise ValueError(
                    f"{csv_path} has no recognizable LinkedIn header. "
                    f"Expected first cell 'First Name'."
                )

            dict_reader = csv.DictReader(f, fieldnames=header)
            for row in dict_reader:
                first = (row.get("First Name") or "").strip()
                last = (row.get("Last Name") or "").strip()
                url = (row.get("URL") or "").strip()
                if not url:
                    continue  # URL is the dedupe key; skip if missing
                full = (first + " " + last).strip()
                email = (row.get("Email Address") or "").strip() or None
                company = (row.get("Company") or "").strip()
                company_norm = normalize_company(company)
                position = (row.get("Position") or "").strip()
                connected_iso = parse_connected_on(row.get("Connected On"))
                seniority = classify_seniority(position)

                seniority_counts[seniority] = seniority_counts.get(seniority, 0) + 1
                if company_norm:
                    company_counts[company_norm] = company_counts.get(company_norm, 0) + 1
                rows_processed += 1

                if dry_run:
                    continue

                # Pre-check existence: SQLite UPSERT (ON CONFLICT DO UPDATE)
                # always returns rowcount=1 and a non-zero lastrowid, so the
                # only reliable insert/update split is a SELECT before the
                # write. linkedin_url is UNIQUE, so this is one indexed lookup.
                existed = conn.execute(
                    "SELECT 1 FROM connections WHERE linkedin_url = ?", (url,)
                ).fetchone()

                conn.execute(
                    """
                    INSERT INTO connections
                        (first_name, last_name, full_name, linkedin_url, email,
                         company, company_normalized, position, connected_on, seniority)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(linkedin_url) DO UPDATE SET
                        first_name        = excluded.first_name,
                        last_name         = excluded.last_name,
                        full_name         = excluded.full_name,
                        email             = COALESCE(excluded.email, connections.email),
                        company           = excluded.company,
                        company_normalized = excluded.company_normalized,
                        position          = excluded.position,
                        connected_on      = excluded.connected_on,
                        seniority         = excluded.seniority
                    """,
                    (first, last, full, url, email, company, company_norm,
                     position, connected_iso, seniority),
                )
                if existed:
                    rows_updated += 1
                else:
                    rows_inserted += 1
        if not dry_run:
            conn.commit()

        top_companies = sorted(
            company_counts.items(), key=lambda kv: kv[1], reverse=True
        )[:10]

        return {
            "rows_processed": rows_processed,
            "rows_inserted": rows_inserted,
            "rows_updated": rows_updated,
            "seniority_counts": seniority_counts,
            "top_companies": top_companies,
            "dry_run": dry_run,
        }
    finally:
        conn.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=DEFAULT_CSV)
    # config.DB_PATH is absolute (config._absolute_db_path()) — pass through.
    ap.add_argument("--db", default=DB_PATH)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.is_absolute():
        csv_path = ROOT / csv_path
    # Refuse arbitrary paths — keeps a stray --csv /etc/passwd from being parsed.
    csv_path = validate_under(csv_path, ROOT / "data", "--csv")

    if not csv_path.exists():
        print(
            f"❌ CSV not found at {csv_path}\n\n"
            f"How to export your LinkedIn connections:\n"
            f"  1. linkedin.com/mypreferences/d/download-my-data\n"
            f"  2. Pick 'Connections' under 'Want something in particular?'\n"
            f"  3. Click Request archive — comes via email in ~10 min\n"
            f"  4. Unzip; copy Connections.csv to {DEFAULT_CSV}\n",
            file=sys.stderr,
        )
        return 1

    # DB lives in the user-data dir (persistent across worktrees) by default,
    # or under data/db/ if a legacy relative COIN_DB_PATH is configured.
    db_path = Path(args.db).resolve()
    allowed_roots = [
        (ROOT / "data" / "db").resolve(),  # legacy in-tree
        Path(DB_PATH).parent.resolve(),    # configured user-data dir
    ]
    if not any(
        db_path == root or db_path.parent == root or str(db_path).startswith(str(root) + "/")
        for root in allowed_roots
    ):
        ap.error(f"--db must be under one of: {[str(r) for r in allowed_roots]}")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    summary = import_csv(db_path, csv_path, dry_run=args.dry_run)

    print(f"{'[DRY RUN] ' if summary['dry_run'] else ''}Connections import:")
    print(f"  Rows processed: {summary['rows_processed']}")
    if not summary["dry_run"]:
        print(f"  Inserted/updated: {summary['rows_inserted'] + summary['rows_updated']}")
    print(f"\n  By seniority:")
    for k, v in summary["seniority_counts"].items():
        print(f"    {k:<12} {v}")
    print(f"\n  Top 10 companies by connection count:")
    for co, n in summary["top_companies"]:
        print(f"    {n:>4}  {co}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
