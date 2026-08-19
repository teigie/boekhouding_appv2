"""Accounts: link an additional Rekening (bank account) to the current
user, or remove one again. The combined view (GET) lives on the profile
page, app/routes/user.py — this module only owns the POST /accounts
write paths, redirecting back to that page on success and re-rendering it
inline with an error on failure."""
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

_ADD_REKENING_SQL = (SQL_DIR / "queries" / "rekeningen" / "add_rekening.sql").read_text(encoding="utf-8")
_FIND_REKENING_FOR_USER_SQL = (
    SQL_DIR / "queries" / "rekeningen" / "find_by_id_for_user.sql"
).read_text(encoding="utf-8")
_DELETE_TEMP_AFSCHRIFT_FOR_REKENING_SQL = (
    SQL_DIR / "queries" / "temp_afschrift" / "delete_for_rekening.sql"
).read_text(encoding="utf-8")
_DELETE_AFSCHRIFT_FOR_REKENING_SQL = (
    SQL_DIR / "queries" / "afschrift" / "delete_for_rekening.sql"
).read_text(encoding="utf-8")
_DELETE_REKENING_SQL = (SQL_DIR / "queries" / "rekeningen" / "delete_rekening.sql").read_text(encoding="utf-8")


@router.post("/accounts")
def add_account(request: Request, rekening: str = Form(...)):
    user = require_login(request)
    if isinstance(user, RedirectResponse):
        return user

    rekening = rekening.strip()
    conn = get_connection()
    try:
        error = None
        if not rekening:
            error = "Een rekeningnummer is verplicht."
        else:
            try:
                conn.execute(_ADD_REKENING_SQL, {"name": rekening, "user_id": user["id"]})
                conn.commit()
            except sqlite3.IntegrityError:
                conn.rollback()
                error = f"Rekening '{rekening}' is al geregistreerd."

        if error:
            data = load_user_page_data(conn, user["id"])
    finally:
        conn.close()

    if error:
        log.warning("Failed to add account for user %s: %s", user["id"], error)
        return templates.TemplateResponse(
            request, "user.html", {**data, "user": user, "error": error}, status_code=400
        )
    log.info("Account %s linked to user %s", rekening, user["id"])
    return RedirectResponse(user_page_url(user["name"]), status_code=303)


@router.post("/accounts/{rekening_id}/delete")
def delete_account(request: Request, rekening_id: int):
    """Removes an account and everything tied to it — its entire
    temp_afschrift backlog *and* its already-migrated afschrift history —
    in one transaction. Unlike categories.py::delete_category, this
    doesn't block on existing usage and ask the user to clear it first:
    there's no way to "unlink" a bank statement row from its account, so
    the only options are keep both or delete both. The confirmation
    warning shown before this is ever submitted (user.html's data-count
    attribute + app/static/js/user.js) is the only thing standing between
    a click and permanently losing that history — there is no undo.

    Rekening/temp_afschrift/afschrift have no ON DELETE CASCADE between
    them (a Rekening_ID is meant to survive as long as the ledger does,
    see docs/ARCHITECTURE.md), so all three deletes are explicit here and
    ordered child-before-parent to satisfy the foreign keys."""
    user = require_login(request)
    if isinstance(user, RedirectResponse):
        return user

    conn = get_connection()
    try:
        rekening = conn.execute(_FIND_REKENING_FOR_USER_SQL, {"id": rekening_id, "user_id": user["id"]}).fetchone()
        if rekening is None:
            return RedirectResponse(user_page_url(user["name"]), status_code=303)

        params = {"rekening_id": rekening_id, "user_id": user["id"]}
        error = None
        try:
            temp_deleted = conn.execute(_DELETE_TEMP_AFSCHRIFT_FOR_REKENING_SQL, params).rowcount
            afschrift_deleted = conn.execute(_DELETE_AFSCHRIFT_FOR_REKENING_SQL, params).rowcount
            conn.execute(_DELETE_REKENING_SQL, {"id": rekening_id, "user_id": user["id"]})
            conn.commit()
        except sqlite3.IntegrityError:
            conn.rollback()
            error = f"Rekening '{rekening['name']}' kon niet verwijderd worden."

        if error:
            data = load_user_page_data(conn, user["id"])
    finally:
        conn.close()

    if error:
        log.warning("Failed to delete Rekening %s for user %s: %s", rekening_id, user["id"], error)
        return templates.TemplateResponse(
            request, "user.html", {**data, "user": user, "error": error}, status_code=400
        )
    audit.info(
        "Rekening '%s' (%s) deleted by user %s — %d temp_afschrift row(s) and %d afschrift row(s) removed with it",
        rekening["name"], rekening_id, user["id"], temp_deleted, afschrift_deleted,
    )
    return RedirectResponse(user_page_url(user["name"]), status_code=303)
