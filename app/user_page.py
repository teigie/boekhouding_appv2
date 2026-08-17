"""Shared data-loading for the per-user profile page (Rekeningen +
categorieën/keywords together, see app/routes/user.py). Used both by the
page's own GET route and by accounts.py/categories.py's POST error paths,
which re-render that same combined page on failure rather than a
standalone one.
"""
import sqlite3
from urllib.parse import quote

from app.config import SQL_DIR

_LIST_REKENINGEN_SQL = (SQL_DIR / "queries" / "rekeningen" / "list_for_user.sql").read_text(encoding="utf-8")
_LIST_CATEGORIES_SQL = (SQL_DIR / "queries" / "categorieen" / "list_for_user.sql").read_text(encoding="utf-8")
_LIST_SUGGESTIONS_SQL = (SQL_DIR / "queries" / "categorieen" / "list_suggestions.sql").read_text(encoding="utf-8")
_LIST_NAAM_KEYWORDS_SQL = (
    SQL_DIR / "queries" / "reference_data" / "list_naam_keywords_for_user.sql"
).read_text(encoding="utf-8")
_LIST_MEDEDELING_KEYWORDS_SQL = (
    SQL_DIR / "queries" / "reference_data" / "list_mededeling_keywords_for_user.sql"
).read_text(encoding="utf-8")


def user_page_url(username: str) -> str:
    """Canonical URL for a user's profile page. Percent-encodes the name
    so a freely-typed username with spaces or other special characters
    doesn't break the URL — see app/routes/user.py for why the path
    segment itself is cosmetic, not an authorization boundary."""
    return f"/user/{quote(username, safe='')}"


def load_user_page_data(conn: sqlite3.Connection, user_id: int) -> dict:
    """Rekeningen, plus categories with their keywords grouped underneath,
    plus the suggestion chips still worth offering (names the user
    doesn't already have, case-insensitively)."""
    rekeningen = conn.execute(_LIST_REKENINGEN_SQL, {"user_id": user_id}).fetchall()
    categorieen = conn.execute(_LIST_CATEGORIES_SQL, {"user_id": user_id}).fetchall()
    naam_keywords = conn.execute(_LIST_NAAM_KEYWORDS_SQL, {"user_id": user_id}).fetchall()
    mededeling_keywords = conn.execute(_LIST_MEDEDELING_KEYWORDS_SQL, {"user_id": user_id}).fetchall()
    suggesties = conn.execute(_LIST_SUGGESTIONS_SQL).fetchall()

    by_id = {
        c["ID"]: {"ID": c["ID"], "Name": c["Name"], "naam_keywords": [], "mededeling_keywords": []}
        for c in categorieen
    }
    for k in naam_keywords:
        by_id[k["cat_ID"]]["naam_keywords"].append(k)
    for k in mededeling_keywords:
        by_id[k["cat_ID"]]["mededeling_keywords"].append(k)

    owned_names = {c["Name"].casefold() for c in categorieen}
    suggesties = [s for s in suggesties if s["Name"].casefold() not in owned_names]

    return {
        "rekeningen": rekeningen,
        "categorieen": list(by_id.values()),
        "suggesties": suggesties,
    }
