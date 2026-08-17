#!/usr/bin/env python3
"""One-off migration: replaces the old "simple" (afschrift_cat_keywords)
/ "difficult" (afschrift_cat_mededeling_keywords) / "Interne overboeking"
(auto-detected, no table) categorization mechanisms with the new
general, per-user rule system (afschrift_cat_regels /
afschrift_cat_regel_kolommen / afschrift_cat_regel_keywords — see
sql/schema.sql and sql/categorization/match_custom_rules.sql).

Converts existing configured keywords into equivalent rules so current
categorization behavior keeps working immediately, no manual rebuilding:

- Each afschrift_cat_keywords row (Naam keyword) becomes a 1-column rule:
  Naam = keyword, combine_mode 'OR' (irrelevant with a single keyword).
- Each afschrift_cat_mededeling_keywords row becomes a rule with a
  Mededeling column (= keyword), PLUS a Naam column (= naam_keyword) when
  that optional pairing was set — two columns on one rule means AND,
  exactly matching the old paired behavior.
- Each user's category literally named "Interne overboeking" (Name has
  `collate nocase`, so this already matches case-insensitively) that has
  2 or more linked Rekeningen gets ONE new rule: a Tegenrekening column
  with that user's own Rekening IBANs as keywords (OR — any of your own
  accounts counts). This is a static, one-time snapshot, NOT the old
  dynamic "resolves to any Rekening of mine" check — a Rekening linked
  *after* this migration runs won't automatically be covered; add its
  IBAN as another Tegenrekening keyword if you want that too (see
  sql/categorization/README.md).

Then drops the two old tables — this is a genuine schema replacement, not
an additive change, so this rebuilds/removes tables and must run with the
app stopped.

Run once, with the app stopped:
    python scripts/migrate_to_rule_based_categorization.py [--dry-run]

Safe to re-run: refuses to do anything once afschrift_cat_regels already
exists.
"""
import argparse
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.config import DB_PATH  # noqa: E402

_CREATE_REGELS = """
    CREATE TABLE afschrift_cat_regels (
        ID integer primary key autoincrement,
        cat_ID integer not null,
        user_ID integer not null,
        foreign key (cat_ID) references afschrift_categorien(ID) on delete cascade,
        foreign key (user_ID) references Users(ID)
    )
"""

_CREATE_KOLOMMEN = """
    CREATE TABLE afschrift_cat_regel_kolommen (
        ID integer primary key autoincrement,
        regel_ID integer not null,
        kolom varchar(20) not null
            check (kolom in ('Naam', 'Tegenrekening', 'Code', 'Af_bij', 'Bedrag_eur',
                              'Mutatiesoort', 'Mededeling', 'Saldo_na_mutatie', 'Tag')),
        combine_mode varchar(3) not null check (combine_mode in ('AND', 'OR')),
        user_ID integer not null,
        foreign key (regel_ID) references afschrift_cat_regels(ID) on delete cascade,
        foreign key (user_ID) references Users(ID),
        unique (regel_ID, kolom)
    )
"""

_CREATE_KEYWORDS = """
    CREATE TABLE afschrift_cat_regel_keywords (
        ID integer primary key autoincrement,
        regel_kolom_ID integer not null,
        keyword varchar(200) not null,
        user_ID integer not null,
        foreign key (regel_kolom_ID) references afschrift_cat_regel_kolommen(ID) on delete cascade,
        foreign key (user_ID) references Users(ID),
        unique (regel_kolom_ID, keyword)
    )
"""


def already_migrated(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'afschrift_cat_regels'"
    ).fetchone()
    return row is not None


def _add_rule(conn: sqlite3.Connection, cat_id: int, user_id: int, columns: list[tuple[str, str, list[str]]]) -> int:
    """columns: [(kolom, combine_mode, [keyword, ...]), ...]. Returns the
    new regel's ID."""
    regel_id = conn.execute(
        "INSERT INTO afschrift_cat_regels (cat_ID, user_ID) VALUES (?, ?)", (cat_id, user_id)
    ).lastrowid
    for kolom, combine_mode, keywords in columns:
        kolom_id = conn.execute(
            "INSERT INTO afschrift_cat_regel_kolommen (regel_ID, kolom, combine_mode, user_ID) VALUES (?, ?, ?, ?)",
            (regel_id, kolom, combine_mode, user_id),
        ).lastrowid
        for keyword in keywords:
            conn.execute(
                "INSERT INTO afschrift_cat_regel_keywords (regel_kolom_ID, keyword, user_ID) VALUES (?, ?, ?)",
                (kolom_id, keyword, user_id),
            )
    return regel_id


def migrate_naam_keywords(conn: sqlite3.Connection) -> int:
    rows = conn.execute("SELECT keyword, cat_ID, user_ID FROM afschrift_cat_keywords").fetchall()
    for row in rows:
        _add_rule(conn, row["cat_ID"], row["user_ID"], [("Naam", "OR", [row["keyword"]])])
    return len(rows)


def migrate_mededeling_keywords(conn: sqlite3.Connection) -> int:
    rows = conn.execute(
        "SELECT keyword, naam_keyword, cat_ID, user_ID FROM afschrift_cat_mededeling_keywords"
    ).fetchall()
    for row in rows:
        columns = [("Mededeling", "OR", [row["keyword"]])]
        if row["naam_keyword"]:
            columns.append(("Naam", "OR", [row["naam_keyword"]]))
        _add_rule(conn, row["cat_ID"], row["user_ID"], columns)
    return len(rows)


def migrate_internal_transfer(conn: sqlite3.Connection) -> int:
    """Best-effort equivalent of the old dynamic "Tegenrekening resolves
    to one of my own Rekeningen" signal: a static Tegenrekening rule
    listing the user's current IBANs, only created for users who actually
    have a category named exactly "Interne overboeking" AND more than one
    linked Rekening (an internal transfer needs at least two accounts to
    mean anything)."""
    categories = conn.execute(
        "SELECT ID AS cat_id, user_ID FROM afschrift_categorien WHERE Name = 'Interne overboeking'"
    ).fetchall()
    created = 0
    for cat in categories:
        rekeningen = conn.execute(
            "SELECT name FROM Rekening WHERE user_ID = ? ORDER BY name", (cat["user_ID"],)
        ).fetchall()
        if len(rekeningen) < 2:
            continue
        ibans = [r["name"] for r in rekeningen]
        _add_rule(conn, cat["cat_id"], cat["user_ID"], [("Tegenrekening", "OR", ibans)])
        created += 1
    return created


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
            sys.exit("afschrift_cat_regels already exists — migration already applied, aborting.")

        n_naam_kw = conn.execute("SELECT COUNT(*) FROM afschrift_cat_keywords").fetchone()[0]
        n_med_kw = conn.execute("SELECT COUNT(*) FROM afschrift_cat_mededeling_keywords").fetchone()[0]
        n_transfer_candidates = conn.execute(
            "SELECT COUNT(*) FROM afschrift_categorien WHERE Name = 'Interne overboeking'"
        ).fetchone()[0]
        print(f"Will convert {n_naam_kw} Naam keyword(s) and {n_med_kw} Mededeling keyword(s) into rules.")
        print(
            f"Will check {n_transfer_candidates} 'Interne overboeking' categor{'y' if n_transfer_candidates == 1 else 'ies'} "
            "for a static Tegenrekening rule (only created if that user has 2+ linked Rekeningen)."
        )
        print("Will then DROP afschrift_cat_keywords and afschrift_cat_mededeling_keywords.")

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
            conn.execute(_CREATE_REGELS)
            conn.execute(_CREATE_KOLOMMEN)
            conn.execute(_CREATE_KEYWORDS)

            n_naam_rules = migrate_naam_keywords(conn)
            n_med_rules = migrate_mededeling_keywords(conn)
            n_transfer_rules = migrate_internal_transfer(conn)
            print(
                f"Created {n_naam_rules} rule(s) from Naam keywords, {n_med_rules} from Mededeling "
                f"keywords, {n_transfer_rules} static Tegenrekening rule(s) for internal transfers."
            )

            conn.execute("DROP TABLE afschrift_cat_keywords")
            conn.execute("DROP TABLE afschrift_cat_mededeling_keywords")

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
