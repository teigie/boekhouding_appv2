"""Categories: add/delete the current user's own spending categories, and
manage their "simple" (Naam) and "difficult" (Mededeling) keywords. The
combined view (GET) lives on the profile page, app/routes/user.py — this
module only owns the write paths (POST), redirecting back to that page on
success and re-rendering it inline with an error on failure. Categories
and keywords are per-user (see docs/ARCHITECTURE.md) — every route here
re-verifies ownership of any ID coming from a URL/form before acting on
it, the same way app/routes/review.py does for Rekening.
"""
import sqlite3

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from app.config import SQL_DIR
from app.db import get_connection
from app.logging_config import get_app_logger, get_audit_logger
from app.session import require_login
from app.templating import templates
from app.user_page import load_user_page_data, user_page_url

log = get_app_logger()
audit = get_audit_logger()

router = APIRouter()

_FIND_CATEGORY_BY_NAME_SQL = (SQL_DIR / "queries" / "categorieen" / "find_by_name.sql").read_text(encoding="utf-8")
_FIND_CATEGORY_FOR_USER_SQL = (
    SQL_DIR / "queries" / "categorieen" / "find_by_id_for_user.sql"
).read_text(encoding="utf-8")
_COUNT_USAGE_SQL = (SQL_DIR / "queries" / "categorieen" / "count_usage_for_user.sql").read_text(encoding="utf-8")

_ADD_CATEGORY_SQL = (SQL_DIR / "queries" / "reference_data" / "add_category.sql").read_text(encoding="utf-8")
_REMOVE_CATEGORY_SQL = (SQL_DIR / "queries" / "reference_data" / "remove_category.sql").read_text(encoding="utf-8")
_ADD_NAAM_KEYWORD_SQL = (SQL_DIR / "queries" / "reference_data" / "add_naam_keyword.sql").read_text(encoding="utf-8")
_ADD_MEDEDELING_KEYWORD_SQL = (
    SQL_DIR / "queries" / "reference_data" / "add_mededeling_keyword.sql"
).read_text(encoding="utf-8")
_REMOVE_NAAM_KEYWORD_SQL = (
    SQL_DIR / "queries" / "reference_data" / "remove_naam_keyword.sql"
).read_text(encoding="utf-8")
_REMOVE_MEDEDELING_KEYWORD_SQL = (
    SQL_DIR / "queries" / "reference_data" / "remove_mededeling_keyword.sql"
).read_text(encoding="utf-8")


@router.post("/categories")
def add_category(request: Request, name: str = Form(...)):
    user = require_login(request)
    if isinstance(user, RedirectResponse):
        return user

    name = name.strip()
    conn = get_connection()
    try:
        error = None
        if not name:
            error = "Een categorienaam is verplicht."
        else:
            existing = conn.execute(_FIND_CATEGORY_BY_NAME_SQL, {"user_id": user["id"], "name": name}).fetchone()
            if existing:
                error = f"Categorie '{name}' bestaat al."
            else:
                try:
                    conn.execute(_ADD_CATEGORY_SQL, {"name": name, "user_id": user["id"]})
                    conn.commit()
                except sqlite3.IntegrityError:
                    conn.rollback()
                    error = f"Categorie '{name}' bestaat al."

        if error:
            data = load_user_page_data(conn, user["id"])
    finally:
        conn.close()

    if error:
        log.warning("Failed to add category for user %s: %s", user["id"], error)
        return templates.TemplateResponse(
            request, "user.html", {**data, "user": user, "error": error}, status_code=400
        )
    audit.info("Category '%s' added by user %s", name, user["id"])
    return RedirectResponse(user_page_url(user["name"]), status_code=303)


@router.post("/categories/{cat_id}/delete")
def delete_category(request: Request, cat_id: int):
    user = require_login(request)
    if isinstance(user, RedirectResponse):
        return user

    conn = get_connection()
    try:
        category = conn.execute(_FIND_CATEGORY_FOR_USER_SQL, {"id": cat_id, "user_id": user["id"]}).fetchone()
        if category is None:
            return RedirectResponse(user_page_url(user["name"]), status_code=303)

        usage = conn.execute(_COUNT_USAGE_SQL, {"cat_id": cat_id, "user_id": user["id"]}).fetchone()
        error = None
        if usage["usage_count"] > 0:
            error = (
                f"Categorie '{category['Name']}' is nog in gebruik bij {usage['usage_count']} "
                "rij(en) en kan niet verwijderd worden."
            )
        else:
            try:
                conn.execute(_REMOVE_CATEGORY_SQL, {"cat_id": cat_id, "user_id": user["id"]})
                conn.commit()
            except sqlite3.IntegrityError:
                conn.rollback()
                error = f"Categorie '{category['Name']}' is nog in gebruik en kan niet verwijderd worden."

        if error:
            data = load_user_page_data(conn, user["id"])
    finally:
        conn.close()

    if error:
        log.warning("Failed to delete category %s for user %s: %s", cat_id, user["id"], error)
        return templates.TemplateResponse(
            request, "user.html", {**data, "user": user, "error": error}, status_code=400
        )
    audit.info("Category '%s' (%s) deleted by user %s", category["Name"], cat_id, user["id"])
    return RedirectResponse(user_page_url(user["name"]), status_code=303)


def _add_keyword(request: Request, cat_id: int, keyword: str, kind: str, naam_keyword: str = ""):
    """Shared body for the naam/mededeling add-keyword routes below —
    kind is "naam" or "mededeling", picking which table/query to use.

    naam_keyword only applies to kind == "mededeling": an OPTIONAL paired
    condition (see sql/schema.sql's comment on
    afschrift_cat_mededeling_keywords) — a blank value means "no pairing",
    stored as NULL, matching today's Mededeling-only behavior."""
    user = require_login(request)
    if isinstance(user, RedirectResponse):
        return user

    add_sql = _ADD_NAAM_KEYWORD_SQL if kind == "naam" else _ADD_MEDEDELING_KEYWORD_SQL
    keyword = keyword.strip()
    naam_keyword = naam_keyword.strip() or None

    conn = get_connection()
    try:
        category = conn.execute(_FIND_CATEGORY_FOR_USER_SQL, {"id": cat_id, "user_id": user["id"]}).fetchone()
        if category is None:
            return RedirectResponse(user_page_url(user["name"]), status_code=303)

        error = None
        if not keyword:
            error = "Een keyword is verplicht."
        else:
            params = {"keyword": keyword, "cat_id": cat_id, "user_id": user["id"]}
            if kind == "mededeling":
                params["naam_keyword"] = naam_keyword
            try:
                conn.execute(add_sql, params)
                conn.commit()
            except sqlite3.IntegrityError:
                conn.rollback()
                error = f"Keyword '{keyword}' bestaat al."

        if error:
            data = load_user_page_data(conn, user["id"])
    finally:
        conn.close()

    if error:
        log.warning("Failed to add %s keyword for user %s: %s", kind, user["id"], error)
        return templates.TemplateResponse(
            request, "user.html", {**data, "user": user, "error": error}, status_code=400
        )
    audit.info(
        "%s keyword '%s' (naam_keyword=%r) added to category %s by user %s",
        kind, keyword, naam_keyword, cat_id, user["id"],
    )
    return RedirectResponse(user_page_url(user["name"]), status_code=303)


@router.post("/categories/{cat_id}/keywords/naam")
def add_naam_keyword(request: Request, cat_id: int, keyword: str = Form(...)):
    return _add_keyword(request, cat_id, keyword, "naam")


@router.post("/categories/{cat_id}/keywords/mededeling")
def add_mededeling_keyword(request: Request, cat_id: int, keyword: str = Form(...), naam_keyword: str = Form("")):
    return _add_keyword(request, cat_id, keyword, "mededeling", naam_keyword)


def _remove_keyword(request: Request, keyword_id: int, kind: str):
    user = require_login(request)
    if isinstance(user, RedirectResponse):
        return user

    remove_sql = _REMOVE_NAAM_KEYWORD_SQL if kind == "naam" else _REMOVE_MEDEDELING_KEYWORD_SQL
    conn = get_connection()
    try:
        conn.execute(remove_sql, {"id": keyword_id, "user_id": user["id"]})
        conn.commit()
    finally:
        conn.close()
    audit.info("%s keyword %s removed by user %s", kind, keyword_id, user["id"])
    return RedirectResponse(user_page_url(user["name"]), status_code=303)


@router.post("/categories/keywords/naam/{keyword_id}/delete")
def remove_naam_keyword(request: Request, keyword_id: int):
    return _remove_keyword(request, keyword_id, "naam")


@router.post("/categories/keywords/mededeling/{keyword_id}/delete")
def remove_mededeling_keyword(request: Request, keyword_id: int):
    return _remove_keyword(request, keyword_id, "mededeling")
