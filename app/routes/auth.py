"""Login/signup routes. No passwords anywhere — see app/session.py.

Signup creates a User and their first Rekening together, in one
transaction, since a user isn't useful for uploading anything without at
least one linked account.
"""
import sqlite3

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from app.config import SQL_DIR
from app.db import get_connection
from app.logging_config import get_app_logger
from app.session import log_in, log_out
from app.templating import templates

log = get_app_logger()
router = APIRouter()

_LIST_USERS_SQL = (SQL_DIR / "queries" / "users" / "list_users.sql").read_text(encoding="utf-8")
_ADD_USER_SQL = (SQL_DIR / "queries" / "users" / "add_user.sql").read_text(encoding="utf-8")
_FIND_USER_BY_ID_SQL = (SQL_DIR / "queries" / "users" / "find_by_id.sql").read_text(encoding="utf-8")
_TOUCH_LAST_LOGGED_IN_SQL = (SQL_DIR / "queries" / "users" / "touch_last_logged_in.sql").read_text(encoding="utf-8")
_ADD_REKENING_SQL = (SQL_DIR / "queries" / "rekeningen" / "add_rekening.sql").read_text(encoding="utf-8")


@router.get("/login")
def login_page(request: Request):
    conn = get_connection()
    try:
        users = conn.execute(_LIST_USERS_SQL).fetchall()
    finally:
        conn.close()
    return templates.TemplateResponse(request, "login.html", {"users": users})


@router.post("/login")
def login_submit(request: Request, user_id: int = Form(...)):
    conn = get_connection()
    try:
        user = conn.execute(_FIND_USER_BY_ID_SQL, {"user_id": user_id}).fetchone()
        if user is None:
            return templates.TemplateResponse(
                request, "login.html",
                {"users": conn.execute(_LIST_USERS_SQL).fetchall(), "error": "Onbekende gebruiker."},
                status_code=400,
            )
        # Capture the OLD value before overwriting it — that's "when you
        # logged in last time", which is what gets shown on the profile
        # page (/user/{username}). last_logged_in itself always holds the
        # most recent login (see docs/ARCHITECTURE.md).
        previous_login = user["last_logged_in"]
        conn.execute(_TOUCH_LAST_LOGGED_IN_SQL, {"user_id": user_id})
        conn.commit()
    finally:
        conn.close()
    log_in(request, user["ID"], user["Name"], previous_login)
    log.info("User %s (id=%s) logged in", user["Name"], user["ID"])
    return RedirectResponse("/", status_code=303)


@router.post("/login/new")
def create_user_and_login(request: Request, name: str = Form(...), rekening: str = Form(...)):
    name = name.strip()
    rekening = rekening.strip()
    conn = get_connection()
    try:
        if not name or not rekening:
            return templates.TemplateResponse(
                request, "login.html",
                {
                    "users": conn.execute(_LIST_USERS_SQL).fetchall(),
                    "error": "Een naam en een rekeningnummer zijn beide verplicht.",
                },
                status_code=400,
            )
        try:
            cur = conn.execute(_ADD_USER_SQL, {"name": name})
            user_id = cur.lastrowid
            conn.execute(_ADD_REKENING_SQL, {"name": rekening, "user_id": user_id})
            # Record this creation as their first login, so a *future*
            # login has something to show as "previous login".
            conn.execute(_TOUCH_LAST_LOGGED_IN_SQL, {"user_id": user_id})
            conn.commit()
        except sqlite3.IntegrityError:
            conn.rollback()
            return templates.TemplateResponse(
                request, "login.html",
                {
                    "users": conn.execute(_LIST_USERS_SQL).fetchall(),
                    "error": f"Rekening '{rekening}' is al geregistreerd.",
                },
                status_code=400,
            )
    finally:
        conn.close()
    log_in(request, user_id, name, previous_login=None)  # brand new user, no prior login
    log.info("New user %s (id=%s) created with account %s", name, user_id, rekening)
    return RedirectResponse("/", status_code=303)


@router.post("/logout")
def logout(request: Request):
    log_out(request)
    return RedirectResponse("/login", status_code=303)
