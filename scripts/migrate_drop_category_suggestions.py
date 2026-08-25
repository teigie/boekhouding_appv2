#!/usr/bin/env python3
"""One-off migration: drops `afschrift_categorie_suggesties` (see
sql/schema.sql) on an EXISTING data/boekhouding.db.

That table was a flat, global, name-only list of one-click suggestion
chips on /categories — never joined into categorization matching, never
inserted into any user's afschrift_categorien automatically. It's
replaced by app/category_suggestions.py's CATEGORY_SUGGESTIONS (already
the source for the onboarding page's suggestion tree): the /categories
chips now derive from that same fixed list instead of duplicating it in
the database, and get a correct Inkomsten/Uitgaven Type in the bargain
(the old table had none).

Run once, with the app stopped:
    python scripts/migrate_drop_category_suggestions.py [--dry-run]

Safe to re-run: refuses to do anything once the table no longer exists.
"""
import argparse
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.config import DB_PATH  # noqa: E402


def table_exists(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'afschrift_categorie_suggesties'"
    ).fetchone()
    return row is not None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not DB_PATH.exists():
        sys.exit(f"No database at {DB_PATH} — nothing to migrate.")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        if not table_exists(conn):
            sys.exit("afschrift_categorie_suggesties already dropped — migration already applied, aborting.")

        n_rows = conn.execute("SELECT COUNT(*) FROM afschrift_categorie_suggesties").fetchone()[0]
        print(f"{n_rows} row(s) in afschrift_categorie_suggesties will be dropped along with the table.")

        if not args.dry_run:
            backup_path = DB_PATH.with_name(f"{DB_PATH.stem}.bak-{datetime.now():%Y%m%d%H%M%S}{DB_PATH.suffix}")
            conn.close()
            shutil.copy2(DB_PATH, backup_path)
            print(f"Backup written to {backup_path}")
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row

        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("BEGIN")
        try:
            conn.execute("DROP TABLE afschrift_categorie_suggesties")

            violations = conn.execute("PRAGMA foreign_key_check").fetchall()
            if violations:
                raise RuntimeError(f"foreign_key_check found violations: {[dict(v) for v in violations]}")

            if args.dry_run:
                conn.rollback()
                print("--dry-run: rolled back, no changes written.")
            else:
                conn.commit()
                print("Migration committed successfully.")
        except Exception:
            conn.rollback()
            raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
