"""Dashboard: landing page once logged in."""
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from app.config import SQL_DIR
from app.db import get_connection
from app.session import require_login
from app.templating import templates

router = APIRouter()

_LIST_REKENINGEN_SQL = (SQL_DIR / "queries" / "rekeningen" / "list_for_user.sql").read_text(encoding="utf-8")
_LIST_CATEGORIES_SQL = (SQL_DIR / "queries" / "categorieen" / "list_categories.sql").read_text(encoding="utf-8")


@router.get("/")
def home(request: Request):
    user = require_login(request)
    if isinstance(user, RedirectResponse):
        return user

    conn = get_connection()
    try:
        rekeningen = conn.execute(_LIST_REKENINGEN_SQL, {"user_id": user["id"]}).fetchall()
        categorieen = conn.execute(_LIST_CATEGORIES_SQL).fetchall()
    finally:
        conn.close()
    return templates.TemplateResponse(
        request, "index.html",
        {"rekeningen": rekeningen, "categorieen": categorieen},
    )
