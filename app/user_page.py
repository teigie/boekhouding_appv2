"""Shared data-loading for the per-user profile page (Rekeningen +
categorieën/categorization rules together, see app/routes/user.py). Used
both by the page's own GET route and by accounts.py/categories.py's POST
error paths, which re-render that same combined page on failure rather
than a standalone one.
"""
import sqlite3
from urllib.parse import quote

from app.categorization_rules import REGEL_KOLOMMEN
from app.config import SQL_DIR

_LIST_REKENINGEN_SQL = (SQL_DIR / "queries" / "rekeningen" / "list_for_user.sql").read_text(encoding="utf-8")
_COUNT_REKENING_DATA_SQL = (
    SQL_DIR / "queries" / "rekeningen" / "count_data_for_user.sql"
).read_text(encoding="utf-8")
_LATEST_ENTRY_SQL = (
    SQL_DIR / "queries" / "rekeningen" / "latest_entry_for_user.sql"
).read_text(encoding="utf-8")
_LIST_CATEGORIES_SQL = (SQL_DIR / "queries" / "categorieen" / "list_for_user.sql").read_text(encoding="utf-8")
_LIST_SUGGESTIONS_SQL = (SQL_DIR / "queries" / "categorieen" / "list_suggestions.sql").read_text(encoding="utf-8")
_LIST_REGELS_SQL = (SQL_DIR / "queries" / "regels" / "list_for_user.sql").read_text(encoding="utf-8")
_LIST_SUBCATEGORIES_FOR_CATEGORY_SQL = (
    SQL_DIR / "queries" / "subcategorieen" / "list_for_category.sql"
).read_text(encoding="utf-8")


def user_page_url(username: str) -> str:
    """Canonical URL for a user's profile page. Percent-encodes the name
    so a freely-typed username with spaces or other special characters
    doesn't break the URL — see app/routes/user.py for why the path
    segment itself is cosmetic, not an authorization boundary."""
    return f"/user/{quote(username, safe='')}"


def _group_regels_by_category(rows) -> dict:
    """The flat (regel, kolom, keyword) rows from list_for_user.sql,
    nested into cat_ID -> [ {"ID": regel_ID, "subcat_ID", "subcat_name",
    "kolommen": [{"ID", "kolom", "keywords": [{"ID",
    "keyword"}, ...]}, ...]} , ...]. Dict insertion order (Python 3.7+)
    keeps the original regel_ID/kolom_ID/keyword_ID ordering from the
    query intact."""
    regels_by_cat: dict = {}
    for row in rows:
        regels = regels_by_cat.setdefault(row["cat_ID"], {})
        regel = regels.setdefault(
            row["regel_ID"],
            {"ID": row["regel_ID"], "subcat_ID": row["subcat_ID"], "subcat_name": row["subcat_name"], "kolommen": {}},
        )
        kolom = regel["kolommen"].setdefault(
            row["kolom_ID"],
            {"ID": row["kolom_ID"], "kolom": row["kolom"], "keywords": []},
        )
        kolom["keywords"].append({"ID": row["keyword_ID"], "keyword": row["keyword"]})

    return {
        cat_id: [
            {"ID": r["ID"], "subcat_ID": r["subcat_ID"], "subcat_name": r["subcat_name"], "kolommen": list(r["kolommen"].values())}
            for r in regels.values()
        ]
        for cat_id, regels in regels_by_cat.items()
    }


def load_user_page_data(conn: sqlite3.Connection, user_id: int) -> dict:
    """Rekeningen — each annotated with data_count, how many
    temp_afschrift + afschrift rows currently belong to it, shown in the
    "Rekening verwijderen" confirmation warning (app/static/js/user.js),
    and latest_entry, the single most recent statement across both
    temp_afschrift and afschrift (sql/queries/rekeningen/
    latest_entry_for_user.sql — None if the account has no rows at all
    yet) — plus categories with their categorization rules nested
    underneath, plus the suggestion chips still worth offering (names the
    user doesn't already have, case-insensitively)."""
    rekeningen = conn.execute(_LIST_REKENINGEN_SQL, {"user_id": user_id}).fetchall()
    rekeningen_out = [
        {
            "ID": r["ID"],
            "name": r["name"],
            "creation_date": r["creation_date"],
            "data_count": conn.execute(
                _COUNT_REKENING_DATA_SQL, {"rekening_id": r["ID"], "user_id": user_id}
            ).fetchone()["row_count"],
            "latest_entry": conn.execute(
                _LATEST_ENTRY_SQL, {"rekening_id": r["ID"], "user_id": user_id}
            ).fetchone(),
        }
        for r in rekeningen
    ]
    categorieen = conn.execute(_LIST_CATEGORIES_SQL, {"user_id": user_id}).fetchall()
    suggesties = conn.execute(_LIST_SUGGESTIONS_SQL).fetchall()
    regel_rows = conn.execute(_LIST_REGELS_SQL, {"user_id": user_id}).fetchall()
    regels_by_cat = _group_regels_by_category(regel_rows)

    categorieen_out = [
        {
            "ID": c["ID"],
            "Name": c["Name"],
            "regels": regels_by_cat.get(c["ID"], []),
            "subcategorieen": conn.execute(
                _LIST_SUBCATEGORIES_FOR_CATEGORY_SQL, {"cat_id": c["ID"], "user_id": user_id}
            ).fetchall(),
        }
        for c in categorieen
    ]

    owned_names = {c["Name"].casefold() for c in categorieen}
    suggesties = [s for s in suggesties if s["Name"].casefold() not in owned_names]

    return {
        "rekeningen": rekeningen_out,
        "categorieen": categorieen_out,
        "suggesties": suggesties,
        "regel_kolommen": REGEL_KOLOMMEN,
    }
