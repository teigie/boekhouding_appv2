"""Dashboard: the app's landing page — a real financial report over the
permanent afschrift ledger (Fase 5, see docs/ARCHITECTURE.md), filterable
by a whole-calendar-month range (not arbitrary dates — see
app/dashboard_chart.py), which Rekeningen/categorieën count towards
Inkomsten/Uitgaven/Verschil, and a linegraph of those totals (and/or
individual categories) across the selected months.

Everything on this page is scoped to the logged-in user's own data —
never a cross-user total — and reads only the permanent ledger
(afschrift), never temp_afschrift (pending/unresolved rows haven't been
migrated yet, see sql/migration/README.md).

Rekening/categorie filtering happens in Python, not SQL, on purpose —
see app/dashboard_chart.py's module docstring and
sql/queries/afschrift/monthly_totals_for_user.sql.

Each row of the "Per categorie" table can be expanded (index.html +
app/static/js/dashboard.js) to show the individual afschrift rows its
totals were summed from — a separate, unaggregated query
(sql/queries/afschrift/list_for_user.sql) over the same date range, run
through the exact same Rekening/categorie selection filtering as the
totals themselves, so what's shown underneath always matches what's
added up above it.

"Exporteren naar CSV" (below the "Per categorie" table) downloads the
same selection as a standalone CSV — every afschrift column for exactly
the Rekeningen/categorieën/period currently chosen, with foreign keys
(Rekening, Mutatiesoort, categorie) resolved to their names rather than
left as IDs, since the file is meant to be read outside the app. ';'
field delimiter with Dutch-formatted (comma-decimal) amounts — the
standard Dutch/Excel-NL CSV pairing (app/formatting.py::format_amount_nl).
See export_csv below and sql/queries/afschrift/export_for_user.sql.
"""
import csv
import io
import json
from datetime import date
from typing import List, Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Query, Request
from fastapi.responses import RedirectResponse, Response

from app.config import SQL_DIR
from app.dashboard_chart import (
    AGGREGATE_STYLES,
    add_months,
    build_chart,
    build_series,
    category_style,
    month_end,
    month_range,
    parse_month,
)
from app.db import get_connection
from app.formatting import format_amount_nl
from app.session import require_login
from app.templating import templates

router = APIRouter()

_MONTHLY_TOTALS_SQL = (SQL_DIR / "queries" / "afschrift" / "monthly_totals_for_user.sql").read_text(encoding="utf-8")
_LIST_AFSCHRIFT_SQL = (SQL_DIR / "queries" / "afschrift" / "list_for_user.sql").read_text(encoding="utf-8")
_EXPORT_AFSCHRIFT_SQL = (SQL_DIR / "queries" / "afschrift" / "export_for_user.sql").read_text(encoding="utf-8")
_DATE_BOUNDS_SQL = (SQL_DIR / "queries" / "afschrift" / "date_bounds_for_user.sql").read_text(encoding="utf-8")
_LIST_REKENINGEN_SQL = (SQL_DIR / "queries" / "rekeningen" / "list_for_user.sql").read_text(encoding="utf-8")
_LIST_CATEGORIES_SQL = (SQL_DIR / "queries" / "categorieen" / "list_for_user.sql").read_text(encoding="utf-8")

_DEFAULT_GRAPH_LINES = {"inkomsten", "uitgaven", "verschil"}
# The uncategorized bucket (Afschrift_cat_ID IS NULL) is its own
# selectable pseudo-category everywhere on this page.
_NONE_CAT_KEY = "none"


def _cat_key(cat_id) -> str:
    return _NONE_CAT_KEY if cat_id is None else str(cat_id)


def _default_month_range(today: date) -> tuple[date, date]:
    """Last 6 months (incl. the current one) — a single month default
    would make the linegraph a single dot, which defeats its purpose."""
    return add_months(today.replace(day=1), -5), today.replace(day=1)


def _resolve_month_range(today: date, start_month: Optional[str], end_month: Optional[str]) -> tuple[date, date]:
    """Shared by home() and export_csv(): turns the raw start_month/
    end_month query params into an ordered (start, end) pair of
    first-of-month dates, falling back to the default 6-month window for
    a missing/invalid value on either side."""
    default_start, default_end = _default_month_range(today)
    range_start = parse_month(start_month, default_start)
    range_end = parse_month(end_month, default_end)
    if range_end < range_start:
        range_start, range_end = range_end, range_start
    return range_start, range_end


def _resolve_selected_ids(rekeningen, categorieen, rekening_ids, cat_ids, filtered: Optional[str]) -> tuple[set, set]:
    """Shared by home() and export_csv(): turns the raw rekening_ids/
    cat_ids query params into concrete selected-ID sets, defaulting to
    "everything" only on a fresh, unfiltered request — see the "hidden
    filtered=1 marker" note on home() below."""
    all_rekening_ids = {str(r["ID"]) for r in rekeningen}
    all_cat_ids = {_NONE_CAT_KEY} | {str(c["ID"]) for c in categorieen}
    is_filtered = filtered is not None
    selected_rekening_ids = set(rekening_ids) if is_filtered else set(all_rekening_ids)
    selected_cat_ids = set(cat_ids) if is_filtered else set(all_cat_ids)
    return selected_rekening_ids, selected_cat_ids


def _export_url(range_start: date, range_end: date, selected_rekening_ids, selected_cat_ids) -> str:
    """Builds the "Exporteren naar CSV" link's URL from the current
    request's already-resolved period/selection, so the export always
    matches exactly what's shown on the page it's linked from — never a
    separately-chosen export filter."""
    params = [
        ("start_month", f"{range_start.year:04d}-{range_start.month:02d}"),
        ("end_month", f"{range_end.year:04d}-{range_end.month:02d}"),
        ("filtered", "1"),
    ]
    params += [("rekening_ids", v) for v in sorted(selected_rekening_ids)]
    params += [("cat_ids", v) for v in sorted(selected_cat_ids)]
    return "/export?" + urlencode(params)


def _build_presets(today: date, data_bounds: tuple[Optional[str], Optional[str]]) -> list[dict]:
    this_month = today.replace(day=1)
    last6_start, last6_end = _default_month_range(today)
    year_start, year_end = today.replace(month=1, day=1), today.replace(month=12, day=1)

    min_datum, max_datum = data_bounds
    if min_datum and max_datum:
        alles_start = date.fromisoformat(min_datum).replace(day=1)
        alles_end = date.fromisoformat(max_datum).replace(day=1)
    else:
        alles_start = alles_end = this_month

    def key(d: date) -> str:
        return f"{d.year:04d}-{d.month:02d}"

    return [
        {"label": "Deze maand", "start": key(this_month), "end": key(this_month)},
        {"label": "Laatste 6 maanden", "start": key(last6_start), "end": key(last6_end)},
        {"label": "Dit jaar", "start": key(year_start), "end": key(year_end)},
        {"label": "Alles", "start": key(alles_start), "end": key(alles_end)},
    ]


@router.get("/")
def home(
    request: Request,
    start_month: Optional[str] = None,
    end_month: Optional[str] = None,
    rekening_ids: List[str] = Query(default_factory=list),
    cat_ids: List[str] = Query(default_factory=list),
    graph_lines: List[str] = Query(default_factory=list),
    filtered: Optional[str] = None,
):
    user = require_login(request)
    if isinstance(user, RedirectResponse):
        return user

    conn = get_connection()
    try:
        rekeningen = conn.execute(_LIST_REKENINGEN_SQL, {"user_id": user["id"]}).fetchall()
        categorieen = conn.execute(_LIST_CATEGORIES_SQL, {"user_id": user["id"]}).fetchall()
        bounds = conn.execute(_DATE_BOUNDS_SQL, {"user_id": user["id"]}).fetchone()

        today = date.today()
        range_start, range_end = _resolve_month_range(today, start_month, end_month)

        range_params = {
            "user_id": user["id"],
            "start": range_start.isoformat(),
            "end": month_end(range_end).isoformat(),
        }
        rows = conn.execute(_MONTHLY_TOTALS_SQL, range_params).fetchall()
        statement_rows = conn.execute(_LIST_AFSCHRIFT_SQL, range_params).fetchall()
    finally:
        conn.close()

    # Distinguishes "form actually submitted" (even with everything
    # unchecked — that's a legitimate all-zero view) from "fresh page
    # load, no filter chosen yet" (defaults to everything selected).
    selected_rekening_ids, selected_cat_ids = _resolve_selected_ids(
        rekeningen, categorieen, rekening_ids, cat_ids, filtered
    )
    selected_graph_lines = set(graph_lines) if filtered is not None else set(_DEFAULT_GRAPH_LINES)

    filtered_rows = [
        r for r in rows
        if str(r["rekening_id"]) in selected_rekening_ids and _cat_key(r["cat_id"]) in selected_cat_ids
    ]
    filtered_statements = [
        r for r in statement_rows
        if str(r["rekening_id"]) in selected_rekening_ids and _cat_key(r["cat_id"]) in selected_cat_ids
    ]

    totaal_inkomsten = sum(r["totaal_bij"] for r in filtered_rows)
    totaal_uitgaven = sum(r["totaal_af"] for r in filtered_rows)

    per_cat: dict[str, dict] = {}
    for r in filtered_rows:
        key = _cat_key(r["cat_id"])
        entry = per_cat.setdefault(
            key, {"key": key, "category": r["category"], "totaal_bij": 0.0, "totaal_af": 0.0, "statements": []}
        )
        entry["totaal_bij"] += r["totaal_bij"]
        entry["totaal_af"] += r["totaal_af"]
    # Statements are gathered from a separate, unaggregated query
    # (list_for_user.sql) — same date-range/Rekening/category filtering
    # as the totals above, so each category's expanded list on the
    # dashboard always matches exactly what its totals were summed from.
    for r in filtered_statements:
        key = _cat_key(r["cat_id"])
        entry = per_cat.setdefault(
            key, {"key": key, "category": r["category"], "totaal_bij": 0.0, "totaal_af": 0.0, "statements": []}
        )
        entry["statements"].append(r)
    categorie_rows = sorted(per_cat.values(), key=lambda e: (-e["totaal_af"], -e["totaal_bij"]))

    months = month_range(range_start, range_end)
    monthly_values: dict[tuple, float] = {}
    for r in filtered_rows:
        m = r["month"]
        cat_line_key = f"cat:{_cat_key(r['cat_id'])}"
        monthly_values[(m, "inkomsten")] = monthly_values.get((m, "inkomsten"), 0.0) + r["totaal_bij"]
        monthly_values[(m, "uitgaven")] = monthly_values.get((m, "uitgaven"), 0.0) + r["totaal_af"]
        monthly_values[(m, cat_line_key)] = monthly_values.get((m, cat_line_key), 0.0) + (r["totaal_bij"] - r["totaal_af"])
    for m in months:
        monthly_values[(m, "verschil")] = monthly_values.get((m, "inkomsten"), 0.0) - monthly_values.get((m, "uitgaven"), 0.0)

    # Only categories still in-scope (selected_cat_ids) can be graphed —
    # keeps "what's plotted" a subset of "what's counted", never a
    # category the totals above have already excluded.
    graph_line_options = [{"key": k, "label": v["label"]} for k, v in AGGREGATE_STYLES.items()]
    for c in categorieen:
        if str(c["ID"]) in selected_cat_ids:
            graph_line_options.append({"key": f"cat:{c['ID']}", "label": c["Name"]})
    if _NONE_CAT_KEY in selected_cat_ids:
        graph_line_options.append({"key": "cat:none", "label": "Zonder categorie"})

    line_defs = []
    for key in AGGREGATE_STYLES:
        if key in selected_graph_lines:
            line_defs.append({"key": key, **AGGREGATE_STYLES[key]})
    for c in categorieen:
        line_key = f"cat:{c['ID']}"
        if line_key in selected_graph_lines and str(c["ID"]) in selected_cat_ids:
            line_defs.append({"key": line_key, **category_style(c["ID"], c["Name"])})
    if "cat:none" in selected_graph_lines and _NONE_CAT_KEY in selected_cat_ids:
        line_defs.append({"key": "cat:none", **category_style(None, "Zonder categorie")})

    series = build_series(months, line_defs, monthly_values)
    chart = build_chart(months, series)

    return templates.TemplateResponse(
        request, "index.html",
        {
            "rekeningen": rekeningen,
            "categorieen": categorieen,
            "categorie_rows": categorie_rows,
            "totaal_inkomsten": totaal_inkomsten,
            "totaal_uitgaven": totaal_uitgaven,
            "verschil": totaal_inkomsten - totaal_uitgaven,
            "start_month": f"{range_start.year:04d}-{range_start.month:02d}",
            "end_month": f"{range_end.year:04d}-{range_end.month:02d}",
            "selected_rekening_ids": selected_rekening_ids,
            "selected_cat_ids": selected_cat_ids,
            "selected_graph_lines": selected_graph_lines,
            "graph_line_options": graph_line_options,
            "chart": chart,
            "months_json": json.dumps(months),
            "presets": _build_presets(today, (bounds["min_datum"], bounds["max_datum"]) if bounds else (None, None)),
            "export_url": _export_url(range_start, range_end, selected_rekening_ids, selected_cat_ids),
        },
    )


_EXPORT_HEADER = [
    "Datum", "Naam", "Rekening", "Tegenrekening", "Code", "Af_bij", "Bedrag_eur",
    "Mutatiesoort", "Mededeling", "Saldo_na_mutatie", "Tag", "Categorie",
]


@router.get("/export")
def export_csv(
    request: Request,
    start_month: Optional[str] = None,
    end_month: Optional[str] = None,
    rekening_ids: List[str] = Query(default_factory=list),
    cat_ids: List[str] = Query(default_factory=list),
    filtered: Optional[str] = None,
):
    """Downloads exactly the current dashboard selection (Rekeningen,
    categorieën, period — same query params as home(), built into the
    "Exporteren naar CSV" link by _export_url) as a standalone CSV. Every
    foreign key is resolved to its name in SQL itself
    (sql/queries/afschrift/export_for_user.sql) rather than left as an
    ID, since the file is meant to be read outside the app. Hit directly
    without params (rather than via that link), it falls back to the
    same "everything selected, last 6 months" default as a fresh
    dashboard load.

    ';'-delimited with Dutch-formatted (comma-decimal) amounts, the
    standard Dutch/Excel-NL CSV convention — paired on purpose, since a
    Dutch spreadsheet's locale reads ',' as the decimal separator and
    therefore expects ';' as the field delimiter, not ','.
    """
    user = require_login(request)
    if isinstance(user, RedirectResponse):
        return user

    conn = get_connection()
    try:
        rekeningen = conn.execute(_LIST_REKENINGEN_SQL, {"user_id": user["id"]}).fetchall()
        categorieen = conn.execute(_LIST_CATEGORIES_SQL, {"user_id": user["id"]}).fetchall()

        range_start, range_end = _resolve_month_range(date.today(), start_month, end_month)
        selected_rekening_ids, selected_cat_ids = _resolve_selected_ids(
            rekeningen, categorieen, rekening_ids, cat_ids, filtered
        )

        rows = conn.execute(
            _EXPORT_AFSCHRIFT_SQL,
            {"user_id": user["id"], "start": range_start.isoformat(), "end": month_end(range_end).isoformat()},
        ).fetchall()
    finally:
        conn.close()

    export_rows = [
        r for r in rows
        if str(r["rekening_id"]) in selected_rekening_ids and _cat_key(r["cat_id"]) in selected_cat_ids
    ]

    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow(_EXPORT_HEADER)
    for r in export_rows:
        writer.writerow([
            r["Datum"], r["Naam"], r["rekening_name"], r["Tegenrekening"], r["Code"], r["Af_bij"],
            format_amount_nl(r["Bedrag_eur"]), r["mutatiesoort_name"], r["Mededeling"],
            format_amount_nl(r["Saldo_na_mutatie"]), r["Tag"], r["category"],
        ])

    start_key = f"{range_start.year:04d}-{range_start.month:02d}"
    end_key = f"{range_end.year:04d}-{range_end.month:02d}"
    filename = f"afschrift_{start_key}_tot_{end_key}.csv"
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
