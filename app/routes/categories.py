"""Categories: add/delete the current user's own spending categories, and
manage their categorization rules (see app/categorization_rules.py and
sql/categorization/match_custom_rules.sql for the rule model). The
combined view (GET) lives on the profile page, app/routes/user.py — this
module only owns the write paths (POST), redirecting back to that page on
success and re-rendering it inline with an error on failure. Categories
and rules are per-user (see docs/ARCHITECTURE.md) — every route here
re-verifies ownership of any ID coming from a URL/form before acting on
it, the same way app/routes/review.py does for Rekening.
"""
import sqlite3

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from app.categorization_rules import (
    COLUMN_NAMES,
    REGEL_KOLOMMEN,
    InvalidKeywordError,
    normalize_keyword,
    split_keywords,
)
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
_FIND_REGEL_FOR_USER_SQL = (SQL_DIR / "queries" / "regels" / "find_for_user.sql").read_text(encoding="utf-8")
_LIST_KOLOMMEN_FOR_REGEL_SQL = (
    SQL_DIR / "queries" / "regels" / "list_kolommen_for_regel.sql"
).read_text(encoding="utf-8")

_ADD_CATEGORY_SQL = (SQL_DIR / "queries" / "reference_data" / "add_category.sql").read_text(encoding="utf-8")
_REMOVE_CATEGORY_SQL = (SQL_DIR / "queries" / "reference_data" / "remove_category.sql").read_text(encoding="utf-8")
_ADD_REGEL_SQL = (SQL_DIR / "queries" / "reference_data" / "add_regel.sql").read_text(encoding="utf-8")
_REMOVE_REGEL_SQL = (SQL_DIR / "queries" / "reference_data" / "remove_regel.sql").read_text(encoding="utf-8")
_ADD_REGEL_KOLOM_SQL = (SQL_DIR / "queries" / "reference_data" / "add_regel_kolom.sql").read_text(encoding="utf-8")
_ADD_REGEL_KEYWORD_SQL = (
    SQL_DIR / "queries" / "reference_data" / "add_regel_keyword.sql"
).read_text(encoding="utf-8")
_REMOVE_REGEL_KOLOMMEN_FOR_REGEL_SQL = (
    SQL_DIR / "queries" / "reference_data" / "remove_regel_kolommen_for_regel.sql"
).read_text(encoding="utf-8")


def _current_columns_map(rows) -> dict:
    """Groups list_kolommen_for_regel.sql's flat rows into
    {kolom: {"mode": "AND"/"OR", "keywords_text": "kw1\\nkw2"}}, ready to
    pre-fill the rule-edit form's textareas/selects. Also used to rebuild
    the same shape from a just-submitted (invalid) form, so a validation
    error re-renders with what the user actually typed, not stale DB
    values — see save_regel below."""
    out: dict = {}
    for row in rows:
        entry = out.setdefault(row["kolom"], {"mode": row["combine_mode"], "keywords": []})
        entry["keywords"].append(row["keyword"])
    return {kolom: {"mode": entry["mode"], "keywords_text": "\n".join(entry["keywords"])} for kolom, entry in out.items()}


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


@router.post("/categories/{cat_id}/regels")
async def add_regel(request: Request, cat_id: int):
    """Create a new rule under a category from the profile page's
    per-category "add rule" form: one optional {column}_keywords /
    {column}_mode field pair per supported column (app.categorization_rules
    .COLUMN_NAMES). Only columns with a non-empty keyword list become an
    actual column-condition — the rest are simply not part of the rule.
    All of it is created in one transaction, so a submitted rule is never
    partially saved."""
    user = require_login(request)
    if isinstance(user, RedirectResponse):
        return user

    form = await request.form()
    conn = get_connection()
    try:
        category = conn.execute(_FIND_CATEGORY_FOR_USER_SQL, {"id": cat_id, "user_id": user["id"]}).fetchone()
        if category is None:
            return RedirectResponse(user_page_url(user["name"]), status_code=303)

        columns = []  # [(kolom, combine_mode, [keyword, ...]), ...]
        error = None
        for kolom in COLUMN_NAMES:
            raw_values = split_keywords(form.get(f"{kolom}_keywords", ""), column=kolom)
            if not raw_values:
                continue
            mode = form.get(f"{kolom}_mode", "OR")
            if mode not in ("AND", "OR"):
                mode = "OR"
            try:
                normalized = [normalize_keyword(kolom, v) for v in raw_values]
            except InvalidKeywordError as exc:
                error = str(exc)
                break
            columns.append((kolom, mode, normalized))

        if error is None and not columns:
            error = "Een regel heeft minstens één voorwaarde nodig — vul minstens één kolom in."

        if error is None:
            try:
                cursor = conn.execute(_ADD_REGEL_SQL, {"cat_id": cat_id, "user_id": user["id"]})
                regel_id = cursor.lastrowid
                for kolom, mode, keywords in columns:
                    kolom_cursor = conn.execute(
                        _ADD_REGEL_KOLOM_SQL,
                        {"regel_id": regel_id, "kolom": kolom, "combine_mode": mode, "user_id": user["id"]},
                    )
                    kolom_id = kolom_cursor.lastrowid
                    for keyword in keywords:
                        conn.execute(
                            _ADD_REGEL_KEYWORD_SQL,
                            {"regel_kolom_id": kolom_id, "keyword": keyword, "user_id": user["id"]},
                        )
                conn.commit()
            except sqlite3.IntegrityError:
                conn.rollback()
                error = "Deze regel bestaat al gedeeltelijk (dubbele waarde binnen een kolom)."

        if error:
            data = load_user_page_data(conn, user["id"])
    finally:
        conn.close()

    if error:
        log.warning("Failed to add rule for category %s, user %s: %s", cat_id, user["id"], error)
        return templates.TemplateResponse(
            request, "user.html", {**data, "user": user, "error": error}, status_code=400
        )
    audit.info("Rule added to category %s by user %s (%d column condition(s))", cat_id, user["id"], len(columns))
    return RedirectResponse(user_page_url(user["name"]), status_code=303)


@router.post("/categories/regels/{regel_id}/delete")
def delete_regel(request: Request, regel_id: int):
    user = require_login(request)
    if isinstance(user, RedirectResponse):
        return user

    conn = get_connection()
    try:
        conn.execute(_REMOVE_REGEL_SQL, {"id": regel_id, "user_id": user["id"]})
        conn.commit()
    finally:
        conn.close()
    audit.info("Rule %s removed by user %s", regel_id, user["id"])
    return RedirectResponse(user_page_url(user["name"]), status_code=303)


@router.get("/categories/regels/{regel_id}/edit")
def edit_regel_page(request: Request, regel_id: int):
    """Full editor for one rule: every supported column is shown (not
    just the ones the rule currently has), pre-filled with its existing
    keywords/mode where set. Reached from the "Aanpassen" button on the
    profile page's rule cards, which otherwise only show a read-only
    summary — all add/remove/change-mode editing happens here."""
    user = require_login(request)
    if isinstance(user, RedirectResponse):
        return user

    conn = get_connection()
    try:
        regel = conn.execute(_FIND_REGEL_FOR_USER_SQL, {"id": regel_id, "user_id": user["id"]}).fetchone()
        if regel is None:
            return RedirectResponse(user_page_url(user["name"]), status_code=303)
        rows = conn.execute(_LIST_KOLOMMEN_FOR_REGEL_SQL, {"regel_id": regel_id, "user_id": user["id"]}).fetchall()
    finally:
        conn.close()

    return templates.TemplateResponse(
        request, "regel_edit.html",
        {"user": user, "regel": regel, "current": _current_columns_map(rows), "regel_kolommen": REGEL_KOLOMMEN},
    )


@router.post("/categories/regels/{regel_id}/edit")
async def save_regel(request: Request, regel_id: int):
    """Saves the rule-edit page as a wholesale replace: every column's
    current keywords are wiped and re-created from whatever was
    submitted, in one transaction (see remove_regel_kolommen_for_regel.sql
    — deleting first is safe since it only commits once the new columns
    have already been validated). Editing the textarea's content is how
    you add or remove individual keywords; clearing a column's textarea
    entirely removes that column-condition from the rule."""
    user = require_login(request)
    if isinstance(user, RedirectResponse):
        return user

    form = await request.form()
    conn = get_connection()
    try:
        regel = conn.execute(_FIND_REGEL_FOR_USER_SQL, {"id": regel_id, "user_id": user["id"]}).fetchone()
        if regel is None:
            return RedirectResponse(user_page_url(user["name"]), status_code=303)

        columns = []  # [(kolom, combine_mode, [keyword, ...]), ...]
        submitted = {}  # kolom -> {"mode", "keywords_text"} as typed, for re-render on error
        error = None
        for kolom in COLUMN_NAMES:
            raw_text = form.get(f"{kolom}_keywords", "")
            mode = form.get(f"{kolom}_mode", "OR")
            if mode not in ("AND", "OR"):
                mode = "OR"
            submitted[kolom] = {"mode": mode, "keywords_text": raw_text}

            raw_values = split_keywords(raw_text, column=kolom)
            if not raw_values:
                continue
            try:
                normalized = [normalize_keyword(kolom, v) for v in raw_values]
            except InvalidKeywordError as exc:
                error = str(exc)
                break
            columns.append((kolom, mode, normalized))

        if error is None and not columns:
            error = "Een regel heeft minstens één voorwaarde nodig — vul minstens één kolom in."

        if error is None:
            try:
                conn.execute(_REMOVE_REGEL_KOLOMMEN_FOR_REGEL_SQL, {"regel_id": regel_id, "user_id": user["id"]})
                for kolom, mode, keywords in columns:
                    kolom_cursor = conn.execute(
                        _ADD_REGEL_KOLOM_SQL,
                        {"regel_id": regel_id, "kolom": kolom, "combine_mode": mode, "user_id": user["id"]},
                    )
                    kolom_id = kolom_cursor.lastrowid
                    for keyword in keywords:
                        conn.execute(
                            _ADD_REGEL_KEYWORD_SQL,
                            {"regel_kolom_id": kolom_id, "keyword": keyword, "user_id": user["id"]},
                        )
                conn.commit()
            except sqlite3.IntegrityError:
                conn.rollback()
                error = "Dubbele waarde binnen een kolom — een keyword mag maar één keer per kolom voorkomen."
    finally:
        conn.close()

    if error:
        log.warning("Failed to save rule %s for user %s: %s", regel_id, user["id"], error)
        return templates.TemplateResponse(
            request, "regel_edit.html",
            {"user": user, "regel": regel, "current": submitted, "regel_kolommen": REGEL_KOLOMMEN, "error": error},
            status_code=400,
        )
    audit.info("Rule %s saved by user %s (%d column condition(s))", regel_id, user["id"], len(columns))
    return RedirectResponse(user_page_url(user["name"]), status_code=303)
