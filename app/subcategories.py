"""Shared "resolve or create" logic for the subcategory dropdown, used by
both app/routes/categories.py (a rule's optional subcategory) and
app/routes/review.py (a row's optional subcategory) so this reuse-by-name
-or-create behavior isn't duplicated between the two. Mirrors
app/routes/review.py's own _resolve_category_id, plus the category
linkage — subcategories are scoped to exactly one category (see
sql/schema.sql), so every resolution here happens within a known
:cat_id, never across a user's categories as a whole.
"""
from typing import Optional

from app.config import SQL_DIR
from app.logging_config import get_app_logger

log = get_app_logger()

_FIND_SUBCATEGORY_BY_NAME_SQL = (SQL_DIR / "queries" / "subcategorieen" / "find_by_name.sql").read_text(
    encoding="utf-8"
)
_FIND_SUBCATEGORY_BY_ID_SQL = (
    SQL_DIR / "queries" / "subcategorieen" / "find_by_id_for_category.sql"
).read_text(encoding="utf-8")
_ADD_SUBCATEGORY_SQL = (SQL_DIR / "queries" / "reference_data" / "add_subcategory.sql").read_text(encoding="utf-8")

NEW_SUBCATEGORY_VALUE = "__new__"


def resolve_or_create_subcategory(conn, user_id: int, cat_id: int, subcat_id_raw: str, new_name_raw: str) -> Optional[int]:
    """Turns a submitted (subcat_id, new_subcategory_name) pair into a
    concrete subcategory ID scoped to :cat_id, adding the subcategory
    first if it's genuinely new — reusing an existing (case-insensitive)
    name under the SAME category instead of duplicating it (the same
    name is fine again under a different category, see sql/schema.sql).
    Returns None for "nothing usable to resolve" (empty selection, or an
    empty typed name), for a deliberately blank selection (subcategory is
    always optional, so both cases mean the same thing: no subcategory),
    AND for a submitted numeric ID that turns out to belong to a
    different category than :cat_id (a guessed/stale ID from elsewhere in
    the user's own account) — same "just resolves to nothing" handling as
    an invalid category ID gets elsewhere, rather than erroring. New/reused
    subcategories are scoped to (cat_id, user_id)."""
    if subcat_id_raw == NEW_SUBCATEGORY_VALUE:
        name = new_name_raw.strip()
        if not name:
            return None
        existing = conn.execute(
            _FIND_SUBCATEGORY_BY_NAME_SQL, {"cat_id": cat_id, "user_id": user_id, "name": name}
        ).fetchone()
        if existing:
            return existing["ID"]
        cursor = conn.execute(_ADD_SUBCATEGORY_SQL, {"name": name, "cat_id": cat_id, "user_id": user_id})
        log.info("New subcategory '%s' added inline under category %s for user %s", name, cat_id, user_id)
        return cursor.lastrowid
    if not subcat_id_raw:
        return None
    try:
        subcat_id = int(subcat_id_raw)
    except ValueError:
        return None
    existing = conn.execute(
        _FIND_SUBCATEGORY_BY_ID_SQL, {"id": subcat_id, "cat_id": cat_id, "user_id": user_id}
    ).fetchone()
    return existing["ID"] if existing else None
