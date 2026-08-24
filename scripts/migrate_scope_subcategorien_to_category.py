#!/usr/bin/env python3
"""One-off migration: scopes `afschrift_subcategorien` to exactly one
parent category (adds a NOT NULL `cat_ID`, changes the uniqueness
constraint from `(user_ID, Name)` to `(cat_ID, Name)`) — subcategories
used to be one shared per-user list, selectable under any category;
changed on request (see CHANGELOG).

SQLite can't ALTER a NOT NULL column onto an existing table, or change an
existing UNIQUE constraint, so this rebuilds `afschrift_subcategorien`
(create the new shape, drop the old table, rename the new one into
place) inside one transaction — same pattern as
scripts/migrate_categories_per_user.py.

Existing subcategory data is simply DISCARDED rather than migrated —
confirmed with the user rather than assumed, since there is no sound
automatic way to guess which single category each existing (until now
category-less) subcategory should move under. Every reference to a
dropped subcategory is cleared first:
  - afschrift_cat_regels.subcat_ID -> NULL (ON DELETE SET NULL would have
    done this too on a real DELETE, but a table rebuild doesn't fire
    triggers/FK actions, so it's done explicitly here).
  - temp_afschrift.Afschrift_subcat_ID / afschrift.Afschrift_subcat_ID ->
    NULL (these two have no ON DELETE action at all normally — an
    in-use subcategory blocks deletion at the app level instead — but
    that guard doesn't apply here since the whole table is being
    rebuilt, not deleted from row by row).
Nothing else about those rows changes; a rule keeps its category
assignment, a ledger row keeps its category — only the (already optional)
subcategory is cleared.

Run once, with the app stopped:
    python scripts/migrate_scope_subcategorien_to_category.py [--dry-run]

Safe to re-run: refuses to do anything once afschrift_subcategorien
already has cat_ID.
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
    cols = {r[1] for r in conn.execute("PRAGMA table_info(afschrift_subcategorien)")}
    return "cat_ID" in cols


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
            sys.exit("afschrift_subcategorien already has cat_ID — migration already applied, aborting.")

        n_subcats = conn.execute("SELECT COUNT(*) FROM afschrift_subcategorien").fetchone()[0]
        n_regel_refs = conn.execute(
            "SELECT COUNT(*) FROM afschrift_cat_regels WHERE subcat_ID IS NOT NULL"
        ).fetchone()[0]
        n_temp_refs = conn.execute(
            "SELECT COUNT(*) FROM temp_afschrift WHERE Afschrift_subcat_ID IS NOT NULL"
        ).fetchone()[0]
        n_afschrift_refs = conn.execute(
            "SELECT COUNT(*) FROM afschrift WHERE Afschrift_subcat_ID IS NOT NULL"
        ).fetchone()[0]

        print(f"{n_subcats} existing subcategorie(ën) will be DISCARDED (not migrated to any category).")
        print(
            f"References that will be cleared to NULL: {n_regel_refs} regel(s), "
            f"{n_temp_refs} temp_afschrift rij(en), {n_afschrift_refs} afschrift rij(en)."
        )
        print("Their category assignment (and everything else) is otherwise untouched.")

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
            conn.execute("UPDATE afschrift_cat_regels SET subcat_ID = NULL WHERE subcat_ID IS NOT NULL")
            conn.execute("UPDATE temp_afschrift SET Afschrift_subcat_ID = NULL WHERE Afschrift_subcat_ID IS NOT NULL")
            conn.execute("UPDATE afschrift SET Afschrift_subcat_ID = NULL WHERE Afschrift_subcat_ID IS NOT NULL")

            conn.execute("DROP TABLE afschrift_subcategorien")
            conn.execute(
                """
                CREATE TABLE afschrift_subcategorien (
                    ID integer primary key autoincrement,
                    Name varchar(30) not null collate nocase,
                    cat_ID integer not null,
                    user_ID integer not null,
                    foreign key (cat_ID) references afschrift_categorien(ID) on delete cascade,
                    foreign key (user_ID) references Users(ID),
                    unique (cat_ID, Name)
                )
                """
            )
            print(f"Dropped and recreated afschrift_subcategorien ({n_subcats} old row(s) discarded).")

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
