"""Display-formatting helpers, registered as Jinja2 filters in
app/templating.py. Storage stays ISO/sortable (see docs/ARCHITECTURE.md,
"Dates") — these only convert to the European format shown on screen.
"""
from datetime import datetime
from typing import Optional


def format_datetime_eu(value: Optional[str]) -> str:
    """"YYYY-MM-DD HH:MM:SS" (SQLite's datetime('now')) -> "DD-MM-YYYY HH:MM".
    None/empty -> "Never" (e.g. a user who has never logged in before)."""
    if not value:
        return "Never"
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").strftime("%d-%m-%Y %H:%M")


def format_date_eu(value: Optional[str]) -> str:
    """"YYYY-MM-DD" -> "DD-MM-YYYY". Empty -> ""."""
    if not value:
        return ""
    return datetime.strptime(value, "%Y-%m-%d").strftime("%d-%m-%Y")


_MAAND_NL = [
    "jan", "feb", "mrt", "apr", "mei", "jun",
    "jul", "aug", "sep", "okt", "nov", "dec",
]


def format_month_nl(value: Optional[str]) -> str:
    """"YYYY-MM" -> "aug 2025" (dashboard month-range inputs/chart axis).
    Hardcoded Dutch abbreviations rather than the `locale` module — the
    server may not have a Dutch locale installed, and this avoids that
    dependency entirely. Empty -> ""."""
    if not value:
        return ""
    year, month = value.split("-")
    return f"{_MAAND_NL[int(month) - 1]} {year}"


def format_amount_nl(value: float) -> str:
    """Canonical numeric value -> Dutch-formatted amount string ('.' for
    thousands, ',' for decimals, e.g. 1234.5 -> "1.234,50") — the reverse
    of app/categorization_rules.py::_parse_dutch_amount. Used by the
    dashboard's CSV export (app/routes/dashboard.py::export_csv): a comma
    decimal only reads as numeric in a Dutch-locale spreadsheet, a dot
    would show up as text."""
    sign = "-" if value < 0 else ""
    whole, _, frac = f"{abs(value):.2f}".partition(".")
    groups = []
    while len(whole) > 3:
        groups.insert(0, whole[-3:])
        whole = whole[:-3]
    groups.insert(0, whole)
    return f"{sign}{'.'.join(groups)},{frac}"
