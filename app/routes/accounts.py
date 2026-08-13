"""Accounts screen: view the current user's linked Rekeningen, and link an
additional one (a user can have more than one)."""
import sqlite3

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from app.config import SQL_DIR
from app.db import get_connection
from app.logging_config import get_app_logger
from app.session import require_login
from app.templating import templates

log = get_app_logger()
router = APIRouter()

_LIST_REKENINGEN_SQL = (SQL_DIR / "queries" / "rekeningen" / "list_for_user.sql").read_text(encoding="utf-8")
_ADD_REKENING_SQL = (SQL_DIR / "queries" / "rekeningen" / "add_rekening.sql").read_text(encoding="utf-8")


@router.get("/accounts")
def accounts_page(request: Request):
    user = require_login(request)
    if isinstance(user, RedirectResponse):
        return user

    conn = get_connection()
    try:
        rekeningen = conn.execute(_LIST_REKENINGEN_SQL, {"user_id": user["id"]}).fetchall()
    finally:
        conn.close()
    return templates.TemplateResponse(request, "accounts.html", {"rekeningen": rekeningen, "user": user})


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
            rekeningen = conn.execute(_LIST_REKENINGEN_SQL, {"user_id": user["id"]}).fetchall()
    finally:
        conn.close()

    if error:
        log.warning("Failed to add account for user %s: %s", user["id"], error)
        return templates.TemplateResponse(
            request, "accounts.html", {"rekeningen": rekeningen, "error": error, "user": user}, status_code=400
        )
    log.info("Account %s linked to user %s", rekening, user["id"])
    return RedirectResponse("/accounts", status_code=303)
