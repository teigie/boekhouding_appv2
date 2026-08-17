"""Shared metadata + validation for the per-category rule-based
categorization system (see docs/ARCHITECTURE.md and
sql/categorization/match_custom_rules.sql). Used by both
app/routes/categories.py (validating/normalizing a submitted rule's
conditions before they're stored) and app/user_page.py (labeling columns
on the profile page's "add rule" form) so the one list of supported
columns can't drift out of sync between the two.
"""
import re

# Order matches how columns are presented in the UI (and the order the
# feature was originally requested in).
REGEL_KOLOMMEN = [
    {"name": "Naam", "label": "Naam", "placeholder": "bijv. Baan"},
    {"name": "Tegenrekening", "label": "Tegenrekening", "placeholder": "bijv. NL01ABNA0000000001"},
    {"name": "Code", "label": "Code", "placeholder": "bijv. BA"},
    {"name": "Af_bij", "label": "Af / Bij", "placeholder": "Af of Bij"},
    {"name": "Bedrag_eur", "label": "Bedrag (€)", "placeholder": "bijv. 1.234,56 (één bedrag per regel)"},
    {"name": "Mutatiesoort", "label": "Mutatiesoort", "placeholder": "bijv. Mutatieoverschrijving"},
    {"name": "Mededeling", "label": "Mededeling", "placeholder": "bijv. Salaris"},
    {"name": "Saldo_na_mutatie", "label": "Saldo na mutatie (€)", "placeholder": "bijv. 1.234,56 (één bedrag per regel)"},
    {"name": "Tag", "label": "Tag", "placeholder": ""},
]

COLUMN_NAMES = [k["name"] for k in REGEL_KOLOMMEN]

# Bedrag_eur/Saldo_na_mutatie: matched as an exact NUMBER (see
# match_custom_rules.sql's CAST(... AS REAL) comparison), not as text —
# user input is Dutch-formatted ('.' thousands, ',' decimals) and gets
# parsed into a canonical numeric string before storage.
NUMERIC_COLUMNS = {"Bedrag_eur", "Saldo_na_mutatie"}


class InvalidKeywordError(ValueError):
    """A submitted value doesn't fit its column's expected shape (e.g. an
    unparseable amount, or an Af_bij value that isn't 'Af'/'Bij'). The
    message is Dutch and safe to show directly to the user."""


def split_keywords(raw: str, column: str = None) -> list[str]:
    """Multiple values from a single form field, deduplicated (first
    occurrence wins) with blanks dropped, order preserved — so a user can
    type multiple keywords per column in one textarea instead of
    submitting them one at a time.

    Split on comma AND newline for ordinary columns, but on newline ONLY
    for the numeric columns — a comma there is the Dutch decimal
    separator (see _parse_dutch_amount), not a value separator, so
    splitting on it would tear '1.234,56' into '1.234' and '56'."""
    separator = r"\n+" if column in NUMERIC_COLUMNS else r"[,\n]+"
    parts = re.split(separator, raw)
    seen: set[str] = set()
    out: list[str] = []
    for part in parts:
        value = part.strip()
        if value and value not in seen:
            seen.add(value)
            out.append(value)
    return out


def _parse_dutch_amount(raw: str) -> str:
    """Dutch-formatted amount ('.' thousands, ',' decimals, e.g.
    '1.234,56') into the canonical numeric string stored in the DB and
    read back via CAST(... AS REAL). '.' is ALWAYS treated as a thousands
    separator here, never a decimal point — stripped outright, never
    interpreted."""
    cleaned = raw.strip().replace(".", "").replace(",", ".")
    try:
        return str(float(cleaned))
    except ValueError:
        raise InvalidKeywordError(
            f"'{raw}' is geen geldig bedrag — gebruik ',' voor decimalen en '.' voor "
            "duizendtallen, bijv. '1.234,56'."
        )


def _normalize_af_bij(raw: str) -> str:
    value = raw.strip().casefold()
    if value == "af":
        return "Af"
    if value == "bij":
        return "Bij"
    raise InvalidKeywordError(f"'{raw}' is geen geldige waarde voor Af / Bij — gebruik 'Af' of 'Bij'.")


def normalize_keyword(column: str, raw: str) -> str:
    """Validate + canonicalize one submitted value for the given column,
    ready to store in afschrift_cat_regel_keywords.keyword. Raises
    InvalidKeywordError (Dutch message, safe to show to the user) if the
    value doesn't fit the column."""
    if column in NUMERIC_COLUMNS:
        return _parse_dutch_amount(raw)
    if column == "Af_bij":
        return _normalize_af_bij(raw)
    return raw
