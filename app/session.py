"""Lightweight identity: no passwords anywhere. Logging in means picking
which existing User you are (or creating a new one) on /login — that
choice is stored in a signed session cookie (see app/config.py for what
"signed" buys us here). This is a personal/local app, not a multi-tenant
one with real security boundaries: nothing stops someone from picking a
different name. See docs/ARCHITECTURE.md.
"""
from pathlib import Path
from secrets import token_hex
from typing import Optional

from fastapi import Request
from starlette.responses import RedirectResponse

from app.config import SESSION_SECRET_PATH


def get_or_create_session_secret() -> str:
    """Read the persisted signing secret, generating one on first run."""
    path: Path = SESSION_SECRET_PATH
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    secret = token_hex(32)
    path.write_text(secret, encoding="utf-8")
    return secret


def current_user(request: Request) -> Optional[dict]:
    """{"id": ..., "name": ..., "previous_login": ...} for the logged-in
    user, or None. previous_login is the last_logged_in value Users held
    BEFORE this session's login overwrote it — i.e. "when you logged in
    last time", not "now". None if this is the user's first-ever login."""
    user_id = request.session.get("user_id")
    if user_id is None:
        return None
    return {
        "id": user_id,
        "name": request.session.get("user_name"),
        "previous_login": request.session.get("previous_login"),
    }


def require_login(request: Request):
    """Call at the top of a protected route:

        user = require_login(request)
        if isinstance(user, RedirectResponse):
            return user

    Returns the logged-in user's dict, or a redirect to /login ready to
    be returned as-is if nobody's logged in.
    """
    user = current_user(request)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    return user


def log_in(request: Request, user_id: int, user_name: str, previous_login: Optional[str] = None) -> None:
    request.session["user_id"] = user_id
    request.session["user_name"] = user_name
    request.session["previous_login"] = previous_login


def log_out(request: Request) -> None:
    request.session.clear()
