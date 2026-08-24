#!/usr/bin/env python3
"""One-off migration: removes `combine_mode` from
`afschrift_cat_regel_kolommen` (see sql/schema.sql) — categorization
rules no longer support OF ("any of these keywords") within one column,
only EN ("all of these keywords"). "Any of these" is still expressible,
just as separate rules instead — a category already matches as soon as
ANY of its rules matches (OR across a category's rules), so splitting
one OF-column into N single-keyword rules is behaviourally identical.

Two things happen, in order, inside one transaction:

1. Any column-condition currently on `combine_mode = 'OR'` with 2+
   keywords is split: the rule it belongs to is cloned once per keyword
   (same category, subcategory, and all its OTHER column-conditions
   copied unchanged), each clone getting just that one keyword on the
   affected column, and the original rule is deleted. A group with only
   1 keyword needs no split — 'OR' and 'AND' are identical with a single
   keyword, so those simply keep their (now default) meaning.
2. The `combine_mode` column itself is dropped from
   `afschrift_cat_regel_kolommen` (SQLite >= 3.35 `ALTER TABLE ... DROP
   COLUMN`, supported here — the column's CHECK constraint only refers to
   itself, which SQLite allows dropping).

Run once, with the app stopped:
    python scripts/migrate_remove_combine_mode.py [--dry-run]

Safe to re-run: refuses to do anything once `combine_mode` no longer
exists on the table.
"""
import argparse
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.config import DB_PATH  # noqa: E402


def combine_mode_exists(conn: sqlite3.Connection) -> bool:
    cols = conn.execute("PRAGMA table_info(afschrift_cat_regel_kolommen)").fetchall()
    return any(c["name"] == "combine_mode" for c in cols)


def _clone_rule_for_keyword(
    conn: sqlite3.Connection,
    cat_id: int,
    subcat_id,
    user_id: int,
    split_kolom: str,
    split_keyword: str,
    other_columns: list,
) -> int:
    """Creates one new rule: `split_kolom` = [split_keyword] plus every
    (kolom, [keyword, ...]) in `other_columns` copied unchanged. Returns
    the new regel_ID.

    Called before the `combine_mode` column is dropped from
    afschrift_cat_regel_kolommen (still NOT NULL at this point in the
    transaction), so every insert here supplies 'AND' — the value is
    discarded moments later along with the column itself."""
    regel_id = conn.execute(
        "INSERT INTO afschrift_cat_regels (cat_ID, subcat_ID, user_ID) VALUES (?, ?, ?)",
        (cat_id, subcat_id, user_id),
    ).lastrowid

    for kolom, keywords in [(split_kolom, [split_keyword])] + other_columns:
        kolom_id = conn.execute(
            "INSERT INTO afschrift_cat_regel_kolommen (regel_ID, kolom, combine_mode, user_ID) VALUES (?, ?, 'AND', ?)",
            (regel_id, kolom, user_id),
        ).lastrowid
        for keyword in keywords:
            conn.execute(
                "INSERT INTO afschrift_cat_regel_keywords (regel_kolom_ID, keyword, user_ID) VALUES (?, ?, ?)",
                (kolom_id, keyword, user_id),
            )
    return regel_id


def split_multi_keyword_or_groups(conn: sqlite3.Connection) -> int:
    """Splits every combine_mode='OR' column-group with 2+ keywords into
    one single-keyword rule per keyword (see module docstring). Returns
    how many groups were split (0 is the common case — most installs
    have none)."""
    groups = conn.execute(
        """
        SELECT gk.ID AS kolom_id, gk.regel_ID AS regel_id, gk.kolom, COUNT(*) AS n_keywords
        FROM afschrift_cat_regel_kolommen gk
        JOIN afschrift_cat_regel_keywords k ON k.regel_kolom_ID = gk.ID
        WHERE gk.combine_mode = 'OR'
        GROUP BY gk.ID
        HAVING n_keywords > 1
        """
    ).fetchall()

    for group in groups:
        regel = conn.execute(
            "SELECT cat_ID, subcat_ID, user_ID FROM afschrift_cat_regels WHERE ID = ?", (group["regel_id"],)
        ).fetchone()
        keywords = [
            row["keyword"]
            for row in conn.execute(
                "SELECT keyword FROM afschrift_cat_regel_keywords WHERE regel_kolom_ID = ?", (group["kolom_id"],)
            ).fetchall()
        ]
        other_columns = []
        for other_gk in conn.execute(
            "SELECT ID, kolom FROM afschrift_cat_regel_kolommen WHERE regel_ID = ? AND ID != ?",
            (group["regel_id"], group["kolom_id"]),
        ).fetchall():
            other_keywords = [
                row["keyword"]
                for row in conn.execute(
                    "SELECT keyword FROM afschrift_cat_regel_keywords WHERE regel_kolom_ID = ?", (other_gk["ID"],)
                ).fetchall()
            ]
            other_columns.append((other_gk["kolom"], other_keywords))

        for keyword in keywords:
            _clone_rule_for_keyword(
                conn, regel["cat_ID"], regel["subcat_ID"], regel["user_ID"], group["kolom"], keyword, other_columns
            )
        # Cascade-deletes this rule's own kolommen/keywords too (foreign_keys must be ON).
        conn.execute("DELETE FROM afschrift_cat_regels WHERE ID = ?", (group["regel_id"],))
        print(
            f"  Regel {group['regel_id']} (kolom {group['kolom']}, {len(keywords)} keywords, OF) "
            f"-> gesplitst in {len(keywords)} losse regels."
        )

    return len(groups)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not DB_PATH.exists():
        sys.exit(f"No database at {DB_PATH} — nothing to migrate.")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        if not combine_mode_exists(conn):
            sys.exit("combine_mode already removed from afschrift_cat_regel_kolommen — migration already applied, aborting.")

        n_or_single = conn.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT gk.ID FROM afschrift_cat_regel_kolommen gk
                JOIN afschrift_cat_regel_keywords k ON k.regel_kolom_ID = gk.ID
                WHERE gk.combine_mode = 'OR'
                GROUP BY gk.ID
                HAVING COUNT(*) = 1
            )
            """
        ).fetchone()[0]
        n_or_multi = conn.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT gk.ID FROM afschrift_cat_regel_kolommen gk
                JOIN afschrift_cat_regel_keywords k ON k.regel_kolom_ID = gk.ID
                WHERE gk.combine_mode = 'OR'
                GROUP BY gk.ID
                HAVING COUNT(*) > 1
            )
            """
        ).fetchone()[0]

        print(f"{n_or_single} column-group(s) op OF met 1 keyword (wordt gewoon EN, geen wijziging nodig).")
        print(f"{n_or_multi} column-group(s) op OF met 2+ keywords (wordt opgesplitst in losse regels).")
        print("Daarna wordt de combine_mode-kolom zelf verwijderd.")

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
            n_split = split_multi_keyword_or_groups(conn)
            conn.execute("ALTER TABLE afschrift_cat_regel_kolommen DROP COLUMN combine_mode")
            print(f"Splitste {n_split} multi-keyword OF-groep(en) en verwijderde de combine_mode-kolom.")

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
