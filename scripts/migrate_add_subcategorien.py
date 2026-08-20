#!/usr/bin/env python3
"""One-off migration: adds subcategories (see sql/schema.sql) to an
existing data/boekhouding.db.

Purely additive — no existing data changes shape, nothing to backfill:

- New table `afschrift_subcategorien`: one shared per-user list (NOT
  scoped to a single category — the same subcategory is usable under any
  of a user's categories).
- New nullable `afschrift_cat_regels.subcat_ID` column (a rule can
  optionally also assign a subcategory).
- New nullable `Afschrift_subcat_ID` column on both `temp_afschrift` and
  `afschrift` (a row's subcategory, always optional).

Every existing row simply gets NULL for these new columns — "no
subcategory yet" is the correct starting state for all of them.

Run once, with the app stopped:
    python scripts/migrate_add_subcategorien.py [--dry-run]

Safe to re-run: refuses to do anything once afschrift_subcategorien
already exists.
"""
import argparse
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.config import DB_PATH  # noqa: E402

_CREATE_SUBCATEGORIEEN = """
    CREATE TABLE afschrift_subcategorien (
        ID integer primary key autoincrement,
        Name varchar(30) not null collate nocase,
        user_ID integer not null,
        foreign key (user_ID) references Users(ID),
        unique (user_ID, Name)
    )
"""

_ADD_REGEL_SUBCAT_COLUMN = (
    "ALTER TABLE afschrift_cat_regels "
    "ADD COLUMN subcat_ID integer references afschrift_subcategorien(ID) on delete set null"
)
_ADD_TEMP_AFSCHRIFT_SUBCAT_COLUMN = (
    "ALTER TABLE temp_afschrift ADD COLUMN Afschrift_subcat_ID integer references afschrift_subcategorien(ID)"
)
_ADD_AFSCHRIFT_SUBCAT_COLUMN = (
    "ALTER TABLE afschrift ADD COLUMN Afschrift_subcat_ID integer references afschrift_subcategorien(ID)"
)


def already_migrated(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'afschrift_subcategorien'"
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
        if already_migrated(conn):
            sys.exit("afschrift_subcategorien already exists — migration already applied, aborting.")

        print("Will create afschrift_subcategorien, and add nullable subcategory columns to")
        print("afschrift_cat_regels (subcat_ID), temp_afschrift and afschrift (Afschrift_subcat_ID).")
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
            conn.execute(_CREATE_SUBCATEGORIEEN)
            conn.execute(_ADD_REGEL_SUBCAT_COLUMN)
            conn.execute(_ADD_TEMP_AFSCHRIFT_SUBCAT_COLUMN)
            conn.execute(_ADD_AFSCHRIFT_SUBCAT_COLUMN)
            print("Created afschrift_subcategorien and added the 3 new columns.")

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
