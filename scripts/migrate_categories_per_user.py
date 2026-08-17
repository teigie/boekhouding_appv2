#!/usr/bin/env python3
"""One-off migration: adds user_ID to afschrift_categorien,
afschrift_cat_keywords, afschrift_cat_mededeling_keywords on an EXISTING
data/boekhouding.db, backfilling all current rows to a single target
user, and adds + seeds the new afschrift_categorie_suggesties table.

SQLite can't ALTER a NOT NULL column onto an existing table, or add a new
composite UNIQUE constraint at all, so this rebuilds the three affected
tables (create the new shape, copy+backfill data preserving IDs, drop the
old table, rename the new one into place) inside one transaction.

Run once, with the app stopped:
    python scripts/migrate_categories_per_user.py [--user-id N] [--dry-run]

Safe to re-run: refuses to do anything if the migration already applied.
"""
import argparse
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.config import DB_PATH  # noqa: E402

SUGGESTION_NAMES = [
    "Auto", "OV", "Abonnementen", "Wonen", "Inboedel", "Levensmiddelen",
    "Zorgkosten", "Hobbies", "Kleding", "Huisdieren", "Interne overboeking",
    "Vakantie", "Uitjes/uit eten", "Overig",
]


def pick_target_user(conn: sqlite3.Connection, forced_user_id):
    users = conn.execute("SELECT ID, Name FROM Users ORDER BY ID").fetchall()
    if not users:
        sys.exit("No Users found — nothing to backfill. Run the app once to create a user first.")
    if forced_user_id is not None:
        if forced_user_id not in {u["ID"] for u in users}:
            sys.exit(f"--user-id {forced_user_id} does not exist. Known users: {[dict(u) for u in users]}")
        return forced_user_id
    if len(users) == 1:
        return users[0]["ID"]
    sys.exit(
        "More than one User exists — refusing to guess who owns the existing "
        f"global categories/keywords. Users found: {[dict(u) for u in users]}. "
        "Re-run with --user-id <ID> to pick one explicitly."
    )


def already_migrated(conn: sqlite3.Connection) -> bool:
    cols = {r[1] for r in conn.execute("PRAGMA table_info(afschrift_categorien)")}
    return "user_ID" in cols


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-id", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not DB_PATH.exists():
        sys.exit(f"No database at {DB_PATH} — nothing to migrate.")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        if already_migrated(conn):
            sys.exit("afschrift_categorien already has user_ID — migration already applied, aborting.")

        target_user_id = pick_target_user(conn, args.user_id)
        user_name = conn.execute("SELECT Name FROM Users WHERE ID = ?", (target_user_id,)).fetchone()["Name"]

        n_cats = conn.execute("SELECT COUNT(*) FROM afschrift_categorien").fetchone()[0]
        n_naam_kw = conn.execute("SELECT COUNT(*) FROM afschrift_cat_keywords").fetchone()[0]
        n_med_kw = conn.execute("SELECT COUNT(*) FROM afschrift_cat_mededeling_keywords").fetchone()[0]
        print(f"Target user: {user_name} (ID={target_user_id})")
        print(f"Will backfill {n_cats} categories, {n_naam_kw} naam keywords, {n_med_kw} mededeling keywords.")

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
            # --- afschrift_categorien -------------------------------------
            conn.execute("""
                CREATE TABLE afschrift_categorien_new (
                    ID integer primary key autoincrement,
                    Name varchar(30) not null collate nocase,
                    user_ID integer not null,
                    foreign key (user_ID) references Users(ID),
                    unique (user_ID, Name)
                )
            """)
            conn.execute("""
                INSERT INTO afschrift_categorien_new (ID, Name, user_ID)
                SELECT ID, Name, ? FROM afschrift_categorien
            """, (target_user_id,))
            conn.execute("DROP TABLE afschrift_categorien")
            conn.execute("ALTER TABLE afschrift_categorien_new RENAME TO afschrift_categorien")

            # --- afschrift_cat_keywords ------------------------------------
            conn.execute("""
                CREATE TABLE afschrift_cat_keywords_new (
                    ID integer primary key autoincrement,
                    keyword varchar(30) not null,
                    cat_ID integer not null,
                    user_ID integer not null,
                    foreign key (cat_ID) references afschrift_categorien(ID) on delete cascade,
                    foreign key (user_ID) references Users(ID),
                    unique (user_ID, keyword)
                )
            """)
            conn.execute("""
                INSERT INTO afschrift_cat_keywords_new (ID, keyword, cat_ID, user_ID)
                SELECT ID, keyword, cat_ID, ? FROM afschrift_cat_keywords
            """, (target_user_id,))
            conn.execute("DROP TABLE afschrift_cat_keywords")
            conn.execute("ALTER TABLE afschrift_cat_keywords_new RENAME TO afschrift_cat_keywords")

            # --- afschrift_cat_mededeling_keywords --------------------------
            conn.execute("""
                CREATE TABLE afschrift_cat_mededeling_keywords_new (
                    ID integer primary key autoincrement,
                    keyword varchar(200) not null,
                    cat_ID integer not null,
                    user_ID integer not null,
                    foreign key (cat_ID) references afschrift_categorien(ID) on delete cascade,
                    foreign key (user_ID) references Users(ID),
                    unique (user_ID, keyword)
                )
            """)
            conn.execute("""
                INSERT INTO afschrift_cat_mededeling_keywords_new (ID, keyword, cat_ID, user_ID)
                SELECT ID, keyword, cat_ID, ? FROM afschrift_cat_mededeling_keywords
            """, (target_user_id,))
            conn.execute("DROP TABLE afschrift_cat_mededeling_keywords")
            conn.execute(
                "ALTER TABLE afschrift_cat_mededeling_keywords_new RENAME TO afschrift_cat_mededeling_keywords"
            )

            # --- new suggestions table (doesn't exist yet on old DBs) ------
            conn.execute("""
                CREATE TABLE IF NOT EXISTS afschrift_categorie_suggesties (
                    ID integer primary key autoincrement,
                    Name varchar(30) not null unique
                )
            """)
            conn.executemany(
                "INSERT OR IGNORE INTO afschrift_categorie_suggesties (Name) VALUES (?)",
                [(n,) for n in SUGGESTION_NAMES],
            )

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
