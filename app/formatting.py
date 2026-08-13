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
