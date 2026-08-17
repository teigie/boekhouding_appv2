"""Manual-review overview (Fase 3, see docs/ARCHITECTURE.md). Lists every
temp_afschrift row (any `processed` status) for the logged-in user's own
accounts, grouped in one table per Rekening, so both what's still pending
and what's already resolved are visible in one place.

Correcting a row's category is the one thing this page can do so far — a
dropdown per row, saved for a whole account's table in one go via a single
button. Saving re-runs the same "is this account fully resolved" check the
future migration step will need, and says so on the page — but it does NOT
migrate anything into `afschrift` yet, that's a separate, later feature.
Correcting the account or picking between ambiguous keyword matches is
also still a later step.
"""
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from app.config import SQL_DIR
from app.db import get_connection
from app.logging_config import get_app_logger, get_audit_logger
from app.session import require_login
from app.templating import templates

log = get_app_logger()
audit = get_audit_logger()

router = APIRouter()

_LIST_ALL_SQL = (SQL_DIR / "queries" / "temp_afschrift" / "list_all_for_user.sql").read_text(encoding="utf-8")
_SET_CATEGORY_SQL = (SQL_DIR / "queries" / "temp_afschrift" / "set_category.sql").read_text(encoding="utf-8")
_LIST_CATEGORIES_SQL = (SQL_DIR / "queries" / "categorieen" / "list_for_user.sql").read_text(encoding="utf-8")
_FIND_CATEGORY_SQL = (SQL_DIR / "queries" / "categorieen" / "find_by_name.sql").read_text(encoding="utf-8")
_ADD_CATEGORY_SQL = (SQL_DIR / "queries" / "reference_data" / "add_category.sql").read_text(encoding="utf-8")
_FIND_REKENING_FOR_USER_SQL = (
    SQL_DIR / "queries" / "rekeningen" / "find_by_id_for_user.sql"
).read_text(encoding="utf-8")

_NEW_CATEGORY_VALUE = "__new__"


def _counts(rows):
    return {
        "resolved": sum(1 for row in rows if row["processed"] == 1),
        "unresolved": sum(1 for row in rows if row["processed"] == 0),
        "ambiguous": sum(1 for row in rows if row["processed"] == 2),
    }


def _grouped_by_rekening(rows):
    """rows is already ORDER BY Rekening-name, ID — group without re-sorting."""
    groups = []
    for row in rows:
        if not groups or groups[-1]["rekening_id"] != row["Rekening_ID"]:
            groups.append({"rekening_id": row["Rekening_ID"], "rekening": row["Rekening"], "rows": []})
        groups[-1]["rows"].append(row)
    for group in groups:
        counts = _counts(group["rows"])
        group["counts"] = counts
        group["all_resolved"] = counts["unresolved"] == 0 and counts["ambiguous"] == 0
    return groups


def _resolve_category_id(conn, user_id: int, cat_id_raw: str, new_name_raw: str):
    """Turn a submitted (cat_id, new_category_name) pair into a concrete
    category ID, adding the category first if it's genuinely new — reusing
    an existing (case-insensitive) name instead of duplicating it. Returns
    None if there's nothing usable to resolve (empty selection, or an
    empty typed name). New/reused categories are scoped to user_id."""
    if cat_id_raw == _NEW_CATEGORY_VALUE:
        name = new_name_raw.strip()
        if not name:
            return None
        existing = conn.execute(_FIND_CATEGORY_SQL, {"user_id": user_id, "name": name}).fetchone()
        if existing:
            return existing["ID"]
        cursor = conn.execute(_ADD_CATEGORY_SQL, {"name": name, "user_id": user_id})
        log.info("New category '%s' added via /review for user %s", name, user_id)
        return cursor.lastrowid
    if not cat_id_raw:
        return None
    try:
        return int(cat_id_raw)
    except ValueError:
        return None


@router.get("/review")
def review_page(request: Request):
    user = require_login(request)
    if isinstance(user, RedirectResponse):
        return user

    conn = get_connection()
    try:
        rows = conn.execute(_LIST_ALL_SQL, {"user_id": user["id"]}).fetchall()
        categories = conn.execute(_LIST_CATEGORIES_SQL, {"user_id": user["id"]}).fetchall()
    finally:
        conn.close()

    return templates.TemplateResponse(
        request,
        "review.html",
        {"groups": _grouped_by_rekening(rows), "counts": _counts(rows), "categories": categories},
    )


@router.post("/review/{rekening_id}/save")
async def save_categories(request: Request, rekening_id: int):
    """Saves every row's category dropdown for one account's table in a
    single submit. Once saved, checks whether the account is now fully
    resolved (every row `processed = 1`) — the same precondition the
    migration step will require — and surfaces that on the page. It does
    NOT migrate anything into `afschrift` itself; that's a later feature."""
    user = require_login(request)
    if isinstance(user, RedirectResponse):
        return user

    conn = get_connection()
    try:
        rekening = conn.execute(_FIND_REKENING_FOR_USER_SQL, {"id": rekening_id, "user_id": user["id"]}).fetchone()
        if rekening is None:
            return RedirectResponse("/review", status_code=303)

        form = await request.form()
        saved = 0
        for key, cat_id_raw in form.items():
            if not key.startswith("cat_id_"):
                continue
            row_id = int(key.removeprefix("cat_id_"))
            new_name_raw = form.get(f"new_category_name_{row_id}", "")
            resolved_cat_id = _resolve_category_id(conn, user["id"], cat_id_raw, new_name_raw)
            if resolved_cat_id is None:
                continue
            cursor = conn.execute(
                _SET_CATEGORY_SQL, {"id": row_id, "cat_id": resolved_cat_id, "user_id": user["id"]}
            )
            if cursor.rowcount:
                saved += 1

        conn.commit()
        audit.info(
            "Review save for Rekening %s (%s): %d row(s) categorized by user %s",
            rekening_id, rekening["name"], saved, user["id"],
        )
    finally:
        conn.close()

    return RedirectResponse(f"/review#rekening-{rekening_id}", status_code=303)
