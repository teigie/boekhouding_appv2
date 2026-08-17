"""Accounts: link an additional Rekening (bank account) to the current
user. The combined view (GET) lives on the profile page,
app/routes/user.py — this module only owns the POST /accounts write
path, redirecting back to that page on success and re-rendering it
inline with an error on failure."""
import sqlite3

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from app.config import SQL_DIR
from app.db import get_connection
from app.logging_config import get_app_logger
from app.session import require_login
from app.templating import templates
from app.user_page import load_user_page_data, user_page_url

log = get_app_logger()
router = APIRouter()

_ADD_REKENING_SQL = (SQL_DIR / "queries" / "rekeningen" / "add_rekening.sql").read_text(encoding="utf-8")


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
