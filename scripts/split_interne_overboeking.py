#!/usr/bin/env python3
"""One-off, user-directed data reorganization (not a schema migration):
splits one user's "Interne overboeking" category into two —
"Interne overboeking - inkomend" (incoming, Type='Inkomsten') and
"Interne overboeking - uitgaand" (outgoing, Type='Uitgaven') — since an
internal transfer is really two different things depending on direction,
not one. Direction comes from Af_bij ('Bij'/'Af'), the existing
transaction-direction column — Bedrag_eur itself is always stored
unsigned (see sql/schema.sql), so "positive"/"negative" as the user
described it maps directly onto Af_bij = 'Bij'/'Af'.

Concretely, for the target user's "Interne overboeking" category:
  - Every rule under it is cloned into two rules, each with all of the
    original rule's column-conditions PLUS a new Af_bij condition
    ('Bij' for the inkomend clone, 'Af' for the uitgaand clone) — same
    AND-across-columns model as any other rule (see sql/schema.sql).
    Refuses (aborts, changes nothing) if any existing rule already has
    an Af_bij condition of its own, since cloning would then need to
    decide how to merge two Af_bij conditions rather than just add one.
  - Every existing afschrift/temp_afschrift row currently pointing at
    the old category is repointed to whichever new category matches its
    own Af_bij.
  - The old category's own rules are then deleted, and (once nothing
    references it any more) the old category itself is deleted.
  - Refuses if the old category has any subcategories of its own (none
    currently), since deciding where those should move isn't something
    this script can guess.

Run once, with the app stopped:
    python scripts/split_interne_overboeking.py --user-id 3 [--dry-run]

Safe to re-run: refuses to do anything once the named old category no
longer exists for that user (already split).
"""
import argparse
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.config import DB_PATH  # noqa: E402

OLD_CATEGORY_NAME = "Interne overboeking"
INKOMEND_NAME = "Interne overboeking - inkomend"
UITGAAND_NAME = "Interne overboeking - uitgaand"


def find_old_category(conn: sqlite3.Connection, user_id: int):
    return conn.execute(
        "SELECT ID, description FROM afschrift_categorien WHERE user_ID = ? AND Name = ? COLLATE NOCASE",
        (user_id, OLD_CATEGORY_NAME),
    ).fetchone()


def clone_rule(conn: sqlite3.Connection, regel_id: int, new_cat_id: int, af_bij_value: str, user_id: int) -> int:
    old = conn.execute("SELECT subcat_ID FROM afschrift_cat_regels WHERE ID = ?", (regel_id,)).fetchone()
    new_regel_id = conn.execute(
        "INSERT INTO afschrift_cat_regels (cat_ID, subcat_ID, user_ID) VALUES (?, ?, ?)",
        (new_cat_id, old["subcat_ID"], user_id),
    ).lastrowid

    for kolom in conn.execute("SELECT ID, kolom FROM afschrift_cat_regel_kolommen WHERE regel_ID = ?", (regel_id,)):
        new_kolom_id = conn.execute(
            "INSERT INTO afschrift_cat_regel_kolommen (regel_ID, kolom, user_ID) VALUES (?, ?, ?)",
            (new_regel_id, kolom["kolom"], user_id),
        ).lastrowid
        for kw in conn.execute(
            "SELECT keyword FROM afschrift_cat_regel_keywords WHERE regel_kolom_ID = ?", (kolom["ID"],)
        ):
            conn.execute(
                "INSERT INTO afschrift_cat_regel_keywords (regel_kolom_ID, keyword, user_ID) VALUES (?, ?, ?)",
                (new_kolom_id, kw["keyword"], user_id),
            )

    new_af_bij_kolom_id = conn.execute(
        "INSERT INTO afschrift_cat_regel_kolommen (regel_ID, kolom, user_ID) VALUES (?, 'Af_bij', ?)",
        (new_regel_id, user_id),
    ).lastrowid
    conn.execute(
        "INSERT INTO afschrift_cat_regel_keywords (regel_kolom_ID, keyword, user_ID) VALUES (?, ?, ?)",
        (new_af_bij_kolom_id, af_bij_value, user_id),
    )
    return new_regel_id


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-id", type=int, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not DB_PATH.exists():
        sys.exit(f"No database at {DB_PATH} — nothing to migrate.")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        old_category = find_old_category(conn, args.user_id)
        if old_category is None:
            sys.exit(
                f"No '{OLD_CATEGORY_NAME}' category found for user {args.user_id} "
                "— already split, or nothing to split."
            )
        old_cat_id = old_category["ID"]

        subcats = conn.execute(
            "SELECT COUNT(*) FROM afschrift_subcategorien WHERE cat_ID = ?", (old_cat_id,)
        ).fetchone()[0]
        if subcats:
            sys.exit(
                f"'{OLD_CATEGORY_NAME}' (ID {old_cat_id}) has {subcats} subcategorie(ën) of its own — "
                "refusing to guess which new category they should move under. Move/delete them by hand first."
            )

        rules = conn.execute("SELECT ID FROM afschrift_cat_regels WHERE cat_ID = ?", (old_cat_id,)).fetchall()
        for r in rules:
            has_af_bij = conn.execute(
                "SELECT 1 FROM afschrift_cat_regel_kolommen WHERE regel_ID = ? AND kolom = 'Af_bij'", (r["ID"],)
            ).fetchone()
            if has_af_bij:
                sys.exit(
                    f"Regel {r['ID']} under '{OLD_CATEGORY_NAME}' already has its own Af_bij condition — "
                    "refusing to guess how to combine it with the new one. Resolve by hand first."
                )

        n_afschrift = conn.execute(
            "SELECT COUNT(*) FROM afschrift WHERE Afschrift_cat_ID = ?", (old_cat_id,)
        ).fetchone()[0]
        n_temp = conn.execute(
            "SELECT COUNT(*) FROM temp_afschrift WHERE Afschrift_cat_ID = ?", (old_cat_id,)
        ).fetchone()[0]

        print(f"'{OLD_CATEGORY_NAME}' (ID {old_cat_id}, user {args.user_id}): {len(rules)} regel(s) to split,")
        print(f"  {n_afschrift} afschrift rij(en) and {n_temp} temp_afschrift rij(en) to repoint by Af_bij.")
        print(f"New categories: '{INKOMEND_NAME}' (Inkomsten), '{UITGAAND_NAME}' (Uitgaven).")

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
            inkomend_id = conn.execute(
                "INSERT INTO afschrift_categorien (Name, description, Type, user_ID) VALUES (?, ?, 'Inkomsten', ?)",
                (INKOMEND_NAME, old_category["description"], args.user_id),
            ).lastrowid
            uitgaand_id = conn.execute(
                "INSERT INTO afschrift_categorien (Name, description, Type, user_ID) VALUES (?, ?, 'Uitgaven', ?)",
                (UITGAAND_NAME, old_category["description"], args.user_id),
            ).lastrowid
            print(f"Created '{INKOMEND_NAME}' (ID {inkomend_id}), '{UITGAAND_NAME}' (ID {uitgaand_id}).")

            for r in rules:
                new_in = clone_rule(conn, r["ID"], inkomend_id, "Bij", args.user_id)
                new_out = clone_rule(conn, r["ID"], uitgaand_id, "Af", args.user_id)
                print(f"  Regel {r['ID']} -> inkomend regel {new_in}, uitgaand regel {new_out}")

            n_updated_afschrift_in = conn.execute(
                "UPDATE afschrift SET Afschrift_cat_ID = ? WHERE Afschrift_cat_ID = ? AND Af_bij = 'Bij'",
                (inkomend_id, old_cat_id),
            ).rowcount
            n_updated_afschrift_out = conn.execute(
                "UPDATE afschrift SET Afschrift_cat_ID = ? WHERE Afschrift_cat_ID = ? AND Af_bij = 'Af'",
                (uitgaand_id, old_cat_id),
            ).rowcount
            n_updated_temp_in = conn.execute(
                "UPDATE temp_afschrift SET Afschrift_cat_ID = ? WHERE Afschrift_cat_ID = ? AND Af_bij = 'Bij'",
                (inkomend_id, old_cat_id),
            ).rowcount
            n_updated_temp_out = conn.execute(
                "UPDATE temp_afschrift SET Afschrift_cat_ID = ? WHERE Afschrift_cat_ID = ? AND Af_bij = 'Af'",
                (uitgaand_id, old_cat_id),
            ).rowcount
            print(
                f"Repointed afschrift: {n_updated_afschrift_in} -> inkomend, {n_updated_afschrift_out} -> uitgaand; "
                f"temp_afschrift: {n_updated_temp_in} -> inkomend, {n_updated_temp_out} -> uitgaand."
            )

            conn.execute("DELETE FROM afschrift_cat_regels WHERE cat_ID = ?", (old_cat_id,))
            conn.execute("DELETE FROM afschrift_categorien WHERE ID = ?", (old_cat_id,))
            print(f"Deleted old '{OLD_CATEGORY_NAME}' category (ID {old_cat_id}) and its rules.")

            violations = conn.execute("PRAGMA foreign_key_check").fetchall()
            if violations:
                raise RuntimeError(f"foreign_key_check found violations: {[dict(v) for v in violations]}")

            leftover = conn.execute(
                "SELECT COUNT(*) FROM afschrift WHERE Afschrift_cat_ID = ?", (old_cat_id,)
            ).fetchone()[0] + conn.execute(
                "SELECT COUNT(*) FROM temp_afschrift WHERE Afschrift_cat_ID = ?", (old_cat_id,)
            ).fetchone()[0]
            if leftover:
                raise RuntimeError(f"{leftover} row(s) still point at the deleted category — aborting.")

            if args.dry_run:
                conn.rollback()
                print("--dry-run: rolled back, no changes written.")
            else:
                conn.commit()
                print("Split committed successfully.")
        except Exception:
            conn.rollback()
            raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
