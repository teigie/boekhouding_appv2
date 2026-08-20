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


def _group_thousands(digits: str) -> str:
    """"1234" -> "1.234" — shared by both amount formatters below."""
    groups = []
    while len(digits) > 3:
        groups.insert(0, digits[-3:])
        digits = digits[:-3]
    groups.insert(0, digits)
    return ".".join(groups)


def format_amount_nl(value: float) -> str:
    """Canonical numeric value -> Dutch-formatted amount string ('.' for
    thousands, ',' for decimals, e.g. 1234.5 -> "1.234,50") — the reverse
    of app/categorization_rules.py::_parse_dutch_amount. Used by the
    dashboard's CSV export (a comma decimal only reads as numeric in a
    Dutch-locale spreadsheet, a dot would show up as text) and, as the
    `bedrag_nl` Jinja filter (app/templating.py), by every on-screen euro
    amount — dashboard totals, tables, the chart tooltip, /review, the
    profile page's "laatste boeking"."""
    sign = "-" if value < 0 else ""
    whole, _, frac = f"{abs(value):.2f}".partition(".")
    return f"{sign}{_group_thousands(whole)},{frac}"


def format_amount_nl_whole(value: float) -> str:
    """Same thousands-grouping as format_amount_nl, but rounded to a
    whole number with no decimals — used for the dashboard chart's y-axis
    gridline labels (app/templating.py's `bedrag_nl_whole` filter), where
    exact cents would just clutter a compact scale label."""
    sign = "-" if value < 0 else ""
    whole = str(round(abs(value)))
    return f"{sign}{_group_thousands(whole)}"
