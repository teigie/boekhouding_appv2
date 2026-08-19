"""Manual-review overview (Fase 3, see docs/ARCHITECTURE.md), plus the
Fase 4 migration trigger. Lists every temp_afschrift row (any `processed`
status) for the logged-in user's own accounts, grouped in one table per
Rekening, so both what's still pending and what's already resolved are
visible in one place. A status filter (onopgelost/opgelost/ambigu) only
affects which rows are *displayed* per group — counts, the "fully
resolved" check, and migration eligibility always use the account's full,
unfiltered row set, never the filtered display subset.

Correcting a row's category is the main thing this page can do — a
dropdown per row, saved for a whole account's table in one go via a single
button. This is also how an ambiguous row (processed = 2) gets resolved —
same dropdown, same save button as an unresolved row; picking a category
is itself the resolution, there's no separate "choose between these
matches" step. Saving re-runs the "is this account fully resolved" check
the migration step needs, and shows a "Migreren naar afschrift"-button
under a fully resolved table. That button posts to
/review/{rekening_id}/migrate, which re-checks the same condition against
the database (never trusts the already-rendered page state) via
app/migration.py before moving anything. Moving a row to a different
account, or editing an already-linked account's IBAN, isn't possible —
see app/routes/accounts.py::delete_account for the alternative (delete
the account and re-link the correct one).

Also hosts the "Categorisatie opnieuw proberen" button (moved here from
/upload — this is where its outcome actually matters) — see
app/categorization.py::recategorize_pending.
"""
from typing import List, Optional

from fastapi import APIRouter, Query, Request
from fastapi.responses import RedirectResponse

from app.categorization import recategorize_pending
from app.config import SQL_DIR
from app.db import get_connection
from app.logging_config import get_app_logger, get_audit_logger
from app.migration import NotFullyResolvedError, migrate_account
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
# processed values as strings, since that's how they travel through
# checkbox form values/query params.
_ALL_STATUSES = {"0", "1", "2"}


def _counts(rows):
    return {
        "resolved": sum(1 for row in rows if row["processed"] == 1),
        "unresolved": sum(1 for row in rows if row["processed"] == 0),
        "ambiguous": sum(1 for row in rows if row["processed"] == 2),
    }


def _grouped_by_rekening(rows, selected_statuses=_ALL_STATUSES):
    """rows is already ORDER BY Rekening-name, ID — group without re-sorting.
    counts/all_resolved always reflect the account's FULL row set — the
    status filter only narrows display_rows, so it can never make an
    account look "fully resolved" (or hide that it isn't) just because the
    unresolved/ambiguous rows are filtered out of view."""
    groups = []
    for row in rows:
        if not groups or groups[-1]["rekening_id"] != row["Rekening_ID"]:
            groups.append({"rekening_id": row["Rekening_ID"], "rekening": row["Rekening"], "rows": []})
        groups[-1]["rows"].append(row)
    for group in groups:
        counts = _counts(group["rows"])
        group["counts"] = counts
        group["all_resolved"] = counts["unresolved"] == 0 and counts["ambiguous"] == 0
        group["display_rows"] = [row for row in group["rows"] if str(row["processed"]) in selected_statuses]
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
def review_page(
    request: Request,
    status: List[str] = Query(default_factory=list),
    filtered: Optional[str] = None,
):
    user = require_login(request)
    if isinstance(user, RedirectResponse):
        return user

    # Same "hidden filtered=1 marker" pattern as the dashboard: distinguishes
    # a deliberate all-unchecked submit from a fresh page load, which
    # defaults to showing every status.
    selected_statuses = set(status) if filtered is not None else set(_ALL_STATUSES)

    conn = get_connection()
    try:
        rows = conn.execute(_LIST_ALL_SQL, {"user_id": user["id"]}).fetchall()
        categories = conn.execute(_LIST_CATEGORIES_SQL, {"user_id": user["id"]}).fetchall()
    finally:
        conn.close()

    return templates.TemplateResponse(
        request,
        "review.html",
        {
            "groups": _grouped_by_rekening(rows, selected_statuses),
            "counts": _counts(rows),
            "categories": categories,
            "selected_statuses": selected_statuses,
        },
    )


@router.post("/review/recategorize")
def review_recategorize(request: Request):
    """Re-run automatic categorization against ALL of this user's current
    temp_afschrift rows, without a re-upload — see
    app/categorization.py::recategorize_pending. Re-renders the page
    unfiltered (showing every status) so any rows that just changed are
    visible regardless of whatever filter was active before."""
    user = require_login(request)
    if isinstance(user, RedirectResponse):
        return user

    recategorization = recategorize_pending(user["id"])

    conn = get_connection()
    try:
        rows = conn.execute(_LIST_ALL_SQL, {"user_id": user["id"]}).fetchall()
        categories = conn.execute(_LIST_CATEGORIES_SQL, {"user_id": user["id"]}).fetchall()
    finally:
        conn.close()

    return templates.TemplateResponse(
        request,
        "review.html",
        {
            "groups": _grouped_by_rekening(rows),
            "counts": _counts(rows),
            "categories": categories,
            "selected_statuses": set(_ALL_STATUSES),
            "recategorization": recategorization,
            "recategorize_ran": True,
        },
    )


@router.post("/review/{rekening_id}/save")
async def save_categories(request: Request, rekening_id: int):
    """Saves every row's category dropdown for one account's table in a
    single submit. Once saved, checks whether the account is now fully
    resolved (every row `processed = 1`) — the precondition
    migrate_to_afschrift below requires — and surfaces that on the page.
    It does NOT migrate anything into `afschrift` itself; that's the
    separate migrate_to_afschrift route below."""
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


@router.post("/review/{rekening_id}/migrate")
def migrate_to_afschrift(request: Request, rekening_id: int):
    """Fase 4: migrates one account's fully-resolved temp_afschrift
    backlog into the permanent afschrift ledger (app/migration.py).
    Re-checks ownership and the "fully resolved" precondition against the
    database itself — never trusts that the page shown to the user is
    still accurate — and refuses with a 400 + Dutch error, re-rendering
    the review page, if either fails."""
    user = require_login(request)
    if isinstance(user, RedirectResponse):
        return user

    conn = get_connection()
    try:
        rekening = conn.execute(_FIND_REKENING_FOR_USER_SQL, {"id": rekening_id, "user_id": user["id"]}).fetchone()
    finally:
        conn.close()
    if rekening is None:
        return RedirectResponse("/review", status_code=303)

    try:
        result = migrate_account(rekening_id, user["id"])
    except NotFullyResolvedError:
        conn = get_connection()
        try:
            rows = conn.execute(_LIST_ALL_SQL, {"user_id": user["id"]}).fetchall()
            categories = conn.execute(_LIST_CATEGORIES_SQL, {"user_id": user["id"]}).fetchall()
        finally:
            conn.close()
        error = (
            f"Rekening '{rekening['name']}' heeft nog onopgeloste of ambigue rijen "
            "— migratie is geblokkeerd."
        )
        log.warning("Migration refused for Rekening %s (user %s): not fully resolved", rekening_id, user["id"])
        return templates.TemplateResponse(
            request,
            "review.html",
            {
                "groups": _grouped_by_rekening(rows),
                "counts": _counts(rows),
                "categories": categories,
                "selected_statuses": set(_ALL_STATUSES),
                "error": error,
            },
            status_code=400,
        )

    if result is None:
        log.info("Migration no-op for Rekening %s (user %s): nothing pending", rekening_id, user["id"])

    return RedirectResponse("/review", status_code=303)
