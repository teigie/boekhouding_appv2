"""Per-user profile page: Rekeningen (accounts) and categorieën/keywords
management, combined into one page at /user/{username} — previously two
separate pages (/accounts, /categories). Adding/removing anything is
still handled by accounts.py's and categories.py's POST routes; this
module only owns the combined GET view they redirect back to (or
re-render, as "user.html", on a failed POST).

The {username} in the URL is cosmetic, not authoritative: `Users.Name`
has no uniqueness constraint (this is a personal, not multi-tenant, app —
see app/session.py) and the page always shows the logged-in session's own
data, regardless of what's in the path. If the path doesn't match the
session's own name, redirect to the canonical URL for it instead of
silently serving your own data under a misleading URL.
"""
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from app.db import get_connection
from app.session import require_login
from app.templating import templates
from app.user_page import load_user_page_data, user_page_url

router = APIRouter()


@router.get("/user/{username}")
def user_page(request: Request, username: str):
    user = require_login(request)
    if isinstance(user, RedirectResponse):
        return user

    if username != user["name"]:
        return RedirectResponse(user_page_url(user["name"]), status_code=303)

    conn = get_connection()
    try:
        data = load_user_page_data(conn, user["id"])
    finally:
        conn.close()
    return templates.TemplateResponse(request, "user.html", {**data, "user": user})
