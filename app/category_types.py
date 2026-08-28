"""Shared constants/helpers for a category's Inkomsten/Uitgaven
super-classification (see sql/schema.sql's afschrift_categorien.Type) —
used by both app/routes/categories.py (setting it explicitly, and
requiring it on the "Nieuwe categorie" form) and app/routes/review.py
(the "+ nieuwe categorie…" inline-create flow, which still has no Type
field of its own and so falls back to DEFAULT_CATEGORY_TYPE). Mirrors
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
    None here means: both category creation (app/routes/categories.py)
    and explicitly setting an existing category's Type reject a None
    here as an error rather than silently defaulting it — that could
    file a category under (or silently overwrite it into) the wrong
    supercategory. Only /review's inline quick-add still falls back to
    DEFAULT_CATEGORY_TYPE, since it has no Type field to collect a
    choice from at all."""
    stripped = raw.strip()
    return stripped if stripped in CATEGORY_TYPES else None
