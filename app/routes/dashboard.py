"""Dashboard: the app's landing page — a real financial report over the
permanent afschrift ledger (Fase 5, see docs/ARCHITECTURE.md), filterable
by date range. Rekeningen/categorieën management moved to the per-user
profile page (app/routes/user.py); this page is purely a report.

Defaults to the current calendar month when no range is given (or an
invalid one), and offers a handful of quick-range presets (this/last
month, this year, all time) alongside a free-form start/end date form.
Everything is scoped to the logged-in user's own Rekeningen — never a
cross-user total.
"""
import calendar
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from app.config import SQL_DIR
from app.db import get_connection
from app.session import require_login
from app.templating import templates

router = APIRouter()

_TOTALS_PER_CATEGORY_SQL = (
    SQL_DIR / "queries" / "afschrift" / "totals_per_category_for_user.sql"
).read_text(encoding="utf-8")

# A date outside any real bank statement's range — used as the "Alles"
# (all time) preset's bounds so the same BETWEEN-based query serves it
# without a separate NULL-handling code path.
_EPOCH_START = date(1, 1, 1)
_EPOCH_END = date(9999, 12, 31)


def _month_bounds(d: date) -> tuple[date, date]:
    start = d.replace(day=1)
    last_day = calendar.monthrange(d.year, d.month)[1]
    return start, d.replace(day=last_day)


def _parse_date(value: Optional[str], fallback: date) -> date:
    if not value:
        return fallback
    try:
        return date.fromisoformat(value)
    except ValueError:
        return fallback


def _build_presets(today: date) -> list[dict]:
    this_start, this_end = _month_bounds(today)
    prev_start, prev_end = _month_bounds(this_start - timedelta(days=1))
    year_start, year_end = today.replace(month=1, day=1), today.replace(month=12, day=31)
    return [
        {"label": "Deze maand", "start": this_start.isoformat(), "end": this_end.isoformat()},
        {"label": "Vorige maand", "start": prev_start.isoformat(), "end": prev_end.isoformat()},
        {"label": "Dit jaar", "start": year_start.isoformat(), "end": year_end.isoformat()},
        {"label": "Alles", "start": _EPOCH_START.isoformat(), "end": _EPOCH_END.isoformat()},
    ]


@router.get("/")
def home(request: Request, start: Optional[str] = None, end: Optional[str] = None):
    user = require_login(request)
    if isinstance(user, RedirectResponse):
        return user

    today = date.today()
    default_start, default_end = _month_bounds(today)
    range_start = _parse_date(start, default_start)
    range_end = _parse_date(end, default_end)
    if range_end < range_start:
        range_start, range_end = range_end, range_start

    conn = get_connection()
    try:
        rows = conn.execute(
            _TOTALS_PER_CATEGORY_SQL,
            {"user_id": user["id"], "start": range_start.isoformat(), "end": range_end.isoformat()},
        ).fetchall()
    finally:
        conn.close()

    totaal_inkomsten = sum(r["totaal_bij"] for r in rows)
    totaal_uitgaven = sum(r["totaal_af"] for r in rows)

    return templates.TemplateResponse(
        request, "index.html",
        {
            "categorieen": rows,
            "totaal_inkomsten": totaal_inkomsten,
            "totaal_uitgaven": totaal_uitgaven,
            "verschil": totaal_inkomsten - totaal_uitgaven,
            "start": range_start.isoformat(),
            "end": range_end.isoformat(),
            "presets": _build_presets(today),
        },
    )
