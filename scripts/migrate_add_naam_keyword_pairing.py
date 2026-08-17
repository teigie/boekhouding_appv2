#!/usr/bin/env python3
"""One-off migration: adds the nullable naam_keyword column to
afschrift_cat_mededeling_keywords on an EXISTING data/boekhouding.db (see
sql/schema.sql's comment on that table for what it's for).

Unlike scripts/migrate_categories_per_user.py, this one's a plain
`ALTER TABLE ... ADD COLUMN` — no table rebuild needed, since the new
column is nullable and doesn't add/change any constraint. Existing rows
get NULL, which means "no pairing", i.e. unchanged Mededeling-only
matching behavior.

Run once, with the app stopped:
    python scripts/migrate_add_naam_keyword_pairing.py [--dry-run]

Safe to re-run: refuses to do anything if the column already exists.
"""
import argparse
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.config import DB_PATH  # noqa: E402


def already_migrated(conn: sqlite3.Connection) -> bool:
    cols = {r[1] for r in conn.execute("PRAGMA table_info(afschrift_cat_mededeling_keywords)")}
    return "naam_keyword" in cols


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not DB_PATH.exists():
        sys.exit(f"No database at {DB_PATH} — nothing to migrate.")

    conn = sqlite3.connect(DB_PATH)
    try:
        if already_migrated(conn):
            sys.exit("afschrift_cat_mededeling_keywords already has naam_keyword — migration already applied, aborting.")

        n_rows = conn.execute("SELECT COUNT(*) FROM afschrift_cat_mededeling_keywords").fetchone()[0]
        print(f"Will add nullable naam_keyword column ({n_rows} existing row(s) get NULL — unchanged behavior).")

        if args.dry_run:
            print("--dry-run: no changes written.")
            return

        backup_path = DB_PATH.with_name(f"{DB_PATH.stem}.bak-{datetime.now():%Y%m%d%H%M%S}{DB_PATH.suffix}")
        conn.close()
        shutil.copy2(DB_PATH, backup_path)
        print(f"Backup written to {backup_path}")
        conn = sqlite3.connect(DB_PATH)

        conn.execute("ALTER TABLE afschrift_cat_mededeling_keywords ADD COLUMN naam_keyword varchar(30)")
        conn.commit()
        print("Migration committed successfully.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
