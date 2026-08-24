#!/usr/bin/env python3
"""One-off migration: adds a NOT NULL `Type` column to afschrift_categorien
(see sql/schema.sql) — every category is either an 'Inkomsten' (income) or
'Uitgaven' (expense) super-category, unrelated to the dashboard's own
Inkomsten/Uitgaven totals (those are computed per-transaction from
Af_bij, not from this). Not stored on afschrift_subcategorien at all — a
subcategory always inherits its parent category's Type via cat_ID.

NOT NULL with a DEFAULT of 'Uitgaven' (the more common case) — SQLite can
add a NOT NULL column via a plain ADD COLUMN as long as a non-NULL
DEFAULT is given, no table rebuild needed (unlike
scripts/migrate_scope_subcategorien_to_category.py's NOT NULL + new
UNIQUE change). Every EXISTING category starts as 'Uitgaven'; there's no
sound way to guess which ones are actually 'Inkomsten' automatically, so
those need correcting by hand afterward via
POST /categories/{cat_id}/type (no UI wired up to that yet, see
CHANGELOG) — this script prints every category so you know what to
check.

Run once, with the app stopped:
    python scripts/migrate_add_category_type.py [--dry-run]

Safe to re-run: refuses to do anything once afschrift_categorien already
has Type.
"""
import argparse
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.config import DB_PATH  # noqa: E402

_ADD_TYPE_COLUMN = (
    "ALTER TABLE afschrift_categorien "
    "ADD COLUMN Type varchar(10) not null default 'Uitgaven' "
    "check (Type in ('Inkomsten', 'Uitgaven'))"
)


def already_migrated(conn: sqlite3.Connection) -> bool:
    cols = {r[1] for r in conn.execute("PRAGMA table_info(afschrift_categorien)")}
    return "Type" in cols


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not DB_PATH.exists():
        sys.exit(f"No database at {DB_PATH} — nothing to migrate.")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        if already_migrated(conn):
            sys.exit("afschrift_categorien already has Type — migration already applied, aborting.")

        categories = conn.execute(
            "SELECT c.ID, c.Name, u.Name AS user_name FROM afschrift_categorien c "
            "JOIN Users u ON u.ID = c.user_ID ORDER BY u.Name, c.Name"
        ).fetchall()
        print("Will add Type (NOT NULL, default 'Uitgaven') to afschrift_categorien.")
        print(f"All {len(categories)} existing categorie(ën) start as 'Uitgaven' — review and correct by hand:")
        for c in categories:
            print(f"  [{c['ID']:>3}] {c['user_name']}: {c['Name']}")

        if not args.dry_run:
            backup_path = DB_PATH.with_name(f"{DB_PATH.stem}.bak-{datetime.now():%Y%m%d%H%M%S}{DB_PATH.suffix}")
            conn.close()
            shutil.copy2(DB_PATH, backup_path)
            print(f"Backup written to {backup_path}")
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row

        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("BEGIN")
        try:
            conn.execute(_ADD_TYPE_COLUMN)
            print("Added Type to afschrift_categorien.")

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
            conn.execute("PRAGMA foreign_keys = ON")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
