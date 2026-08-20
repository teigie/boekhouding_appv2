"""Shared "resolve or create" logic for the subcategory dropdown, used by
both app/routes/categories.py (a rule's optional subcategory) and
app/routes/review.py (a row's optional subcategory) so this reuse-by-name
-or-create behavior isn't duplicated between the two. Mirrors
app/routes/review.py's own _resolve_category_id, minus the category
linkage — subcategories are one shared per-user list, not scoped to a
category (see sql/schema.sql).
"""
from typing import Optional

from app.config import SQL_DIR
from app.logging_config import get_app_logger

log = get_app_logger()

_FIND_SUBCATEGORY_SQL = (SQL_DIR / "queries" / "subcategorieen" / "find_by_name.sql").read_text(encoding="utf-8")
_ADD_SUBCATEGORY_SQL = (SQL_DIR / "queries" / "reference_data" / "add_subcategory.sql").read_text(encoding="utf-8")

NEW_SUBCATEGORY_VALUE = "__new__"


def resolve_or_create_subcategory(conn, user_id: int, subcat_id_raw: str, new_name_raw: str) -> Optional[int]:
    """Turns a submitted (subcat_id, new_subcategory_name) pair into a
    concrete subcategory ID, adding the subcategory first if it's
    genuinely new — reusing an existing (case-insensitive) name instead of
    duplicating it. Returns None both for "nothing usable to resolve"
    (empty selection, or an empty typed name) AND for a deliberately blank
    selection — subcategory is always optional, so both cases mean the
    same thing: no subcategory. New/reused subcategories are scoped to
    user_id."""
    if subcat_id_raw == NEW_SUBCATEGORY_VALUE:
        name = new_name_raw.strip()
        if not name:
            return None
        existing = conn.execute(_FIND_SUBCATEGORY_SQL, {"user_id": user_id, "name": name}).fetchone()
        if existing:
            return existing["ID"]
        cursor = conn.execute(_ADD_SUBCATEGORY_SQL, {"name": name, "user_id": user_id})
        log.info("New subcategory '%s' added inline for user %s", name, user_id)
        return cursor.lastrowid
    if not subcat_id_raw:
        return None
    try:
        return int(subcat_id_raw)
    except ValueError:
        return None
