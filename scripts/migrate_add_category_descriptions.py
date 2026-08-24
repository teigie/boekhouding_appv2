#!/usr/bin/env python3
"""One-off migration: adds a nullable `description` column to
afschrift_categorien and afschrift_subcategorien (see sql/schema.sql) —
a free-form, always-optional text note on what a (sub)category is for,
purely for the user's own reference. Never read by matching/filtering
logic anywhere.

Purely additive — no existing data changes shape, nothing to backfill:
every existing row simply gets NULL ("no description yet"), which is the
correct starting state for all of them. Both columns are nullable, so
this is a plain ADD COLUMN, no table rebuild needed (unlike
scripts/migrate_scope_subcategorien_to_category.py's NOT NULL/UNIQUE
change).

Run once, with the app stopped:
    python scripts/migrate_add_category_descriptions.py [--dry-run]

Safe to re-run: refuses to do anything once afschrift_categorien already
has description.
"""
import argparse
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.config import DB_PATH  # noqa: E402

_ADD_CATEGORY_DESCRIPTION_COLUMN = "ALTER TABLE afschrift_categorien ADD COLUMN description varchar(500)"
_ADD_SUBCATEGORY_DESCRIPTION_COLUMN = "ALTER TABLE afschrift_subcategorien ADD COLUMN description varchar(500)"


def already_migrated(conn: sqlite3.Connection) -> bool:
    cols = {r[1] for r in conn.execute("PRAGMA table_info(afschrift_categorien)")}
    return "description" in cols


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
            sys.exit("afschrift_categorien already has description — migration already applied, aborting.")

        print("Will add a nullable description column to afschrift_categorien and afschrift_subcategorien.")
        print("No existing rows change shape — every new column starts NULL.")

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
            conn.execute(_ADD_CATEGORY_DESCRIPTION_COLUMN)
            conn.execute(_ADD_SUBCATEGORY_DESCRIPTION_COLUMN)
            print("Added description to afschrift_categorien and afschrift_subcategorien.")

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
