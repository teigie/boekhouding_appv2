"""Shared constants/helpers for a category's Inkomsten/Uitgaven
super-classification (see sql/schema.sql's afschrift_categorien.Type) —
used by both app/routes/categories.py (setting it explicitly, or
creating a category with a bare-bones form that doesn't collect one yet)
and app/routes/review.py (the "+ nieuwe categorie…" inline-create flow,
which has no Type field to collect one from either). Mirrors
app/subcategories.py's role as the shared home for subcategory logic
used across those same two route modules.
"""
from typing import Optional

CATEGORY_TYPES = ("Inkomsten", "Uitgaven")
DEFAULT_CATEGORY_TYPE = "Uitgaven"  # mirrors sql/schema.sql's own column DEFAULT


def clean_category_type(raw: str) -> Optional[str]:
    """Parses a submitted Type value, returning None for anything that
    isn't exactly one of CATEGORY_TYPES (including empty/whitespace) —
    the column is NOT NULL, so callers must decide for themselves what a
    None here means: category creation falls back to
    DEFAULT_CATEGORY_TYPE (there's no UI to collect this at creation
    time yet), while explicitly setting an existing category's Type
    treats it as a rejected request instead — silently defaulting there
    could overwrite an already-correct classification with the wrong
    one."""
    stripped = raw.strip()
    return stripped if stripped in CATEGORY_TYPES else None
