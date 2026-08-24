"""One-time "voorgestelde categorieën" page shown right after a new user
is created (see app/routes/auth.py::create_user_and_login, which
redirects here instead of straight to "/" once signup succeeds) — offers
the curated Inkomsten/Uitgaven category tree from
app/category_suggestions.py as a single accept/skip choice, so a
brand-new user isn't left staring at a completely empty categories list.

Not itself gated on "this is a fresh signup" — any logged-in user can
revisit this URL (there's no link to it in the nav, but nothing stops a
direct visit) to bulk-add whatever suggested (sub)categories they don't
already have. Accepting again simply skips any category name that
already exists for them (see apply_suggestions below) rather than
erroring out.
"""
import sqlite3

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from app.category_suggestions import CATEGORY_SUGGESTIONS
from app.config import SQL_DIR
from app.db import get_connection
from app.logging_config import get_app_logger, get_audit_logger
from app.session import require_login
from app.templating import templates

log = get_app_logger()
audit = get_audit_logger()

router = APIRouter()

_ADD_CATEGORY_SQL = (SQL_DIR / "queries" / "reference_data" / "add_category.sql").read_text(encoding="utf-8")
_ADD_SUBCATEGORY_SQL = (SQL_DIR / "queries" / "reference_data" / "add_subcategory.sql").read_text(encoding="utf-8")


@router.get("/onboarding/suggesties")
def suggestions_page(request: Request):
    user = require_login(request)
    if isinstance(user, RedirectResponse):
        return user
    return templates.TemplateResponse(
        request, "onboarding_suggesties.html", {"user": user, "suggestions": CATEGORY_SUGGESTIONS}
    )


@router.post("/onboarding/suggesties")
def apply_suggestions(request: Request, action: str = Form(...)):
    user = require_login(request)
    if isinstance(user, RedirectResponse):
        return user

    if action == "accept":
        conn = get_connection()
        added_categories = 0
        added_subcategories = 0
        try:
            for group in CATEGORY_SUGGESTIONS:
                for cat in group["categories"]:
                    try:
                        cursor = conn.execute(
                            _ADD_CATEGORY_SQL,
                            {
                                "name": cat["name"],
                                "description": cat.get("description"),
                                "type": group["type"],
                                "user_id": user["id"],
                            },
                        )
                        cat_id = cursor.lastrowid
                        added_categories += 1
                    except sqlite3.IntegrityError:
                        # Already has a category with this name (e.g. a
                        # returning user re-visiting this page) — skip it
                        # and its subcategories; there's no existing
                        # cat_id to attach them to without a lookup this
                        # simple bulk-add doesn't do.
                        continue
                    for sub_name in cat["subcategorieen"]:
                        try:
                            conn.execute(
                                _ADD_SUBCATEGORY_SQL,
                                {"name": sub_name, "description": None, "cat_id": cat_id, "user_id": user["id"]},
                            )
                            added_subcategories += 1
                        except sqlite3.IntegrityError:
                            continue
            conn.commit()
        finally:
            conn.close()
        audit.info(
            "Onboarding suggestions accepted by user %s (%d categories, %d subcategories added)",
            user["id"], added_categories, added_subcategories,
        )
    else:
        audit.info("Onboarding suggestions skipped by user %s", user["id"])

    return RedirectResponse("/", status_code=303)
