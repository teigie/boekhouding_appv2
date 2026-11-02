"""Pensioenplanner: a year-by-year projection of savings/investments,
replacing a personal spreadsheet the user maintained by hand
(`eerder_stoppen_template.ods`) to estimate whether/when they could stop
working and live off savings + pension. See docs/ARCHITECTURE.md for the
full design (data model, why the time axis is calendar year rather than
age, how auto-suggested baselines are computed).

Three screens:
- GET/POST /pensioenplanner/instellingen — settings (horizon, growth,
  the two wealth "pots") + personen + posten management. The first visit
  ever (no fire_instellingen row yet) seeds sensible defaults and
  auto-populates posten from grootboek history, same as an explicit
  "ververs voorstellen".
- GET /pensioenplanner — the projection itself: linegraph + year table +
  headline outcome.
- GET /pensioenplanner/export — the year table as CSV.

Everything here is scoped to the logged-in user's own data (per-user,
same as every other screen — see docs/ARCHITECTURE.md), and every route
re-verifies ownership of any ID coming from a URL/form before acting on
it, the same way app/routes/categories.py does for categorieën.
"""
import csv
import io
from datetime import date
from typing import Optional

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse, Response

from app.config import SQL_DIR
from app.dashboard_chart import add_months, build_chart, build_series
from app.db import get_connection
from app.fire_projection import build_projection
from app.formatting import format_amount_nl, parse_amount_nl
from app.logging_config import get_app_logger, get_audit_logger
from app.session import require_login
from app.templating import templates

log = get_app_logger()
audit = get_audit_logger()

router = APIRouter()

_GET_INSTELLINGEN_SQL = (SQL_DIR / "queries" / "fire" / "get_instellingen_for_user.sql").read_text(encoding="utf-8")
_UPSERT_INSTELLINGEN_SQL = (SQL_DIR / "queries" / "fire" / "upsert_instellingen.sql").read_text(encoding="utf-8")
_LIST_PERSONEN_SQL = (SQL_DIR / "queries" / "fire" / "list_personen_for_user.sql").read_text(encoding="utf-8")
_ADD_PERSOON_SQL = (SQL_DIR / "queries" / "fire" / "add_persoon.sql").read_text(encoding="utf-8")
_REMOVE_PERSOON_SQL = (SQL_DIR / "queries" / "fire" / "remove_persoon.sql").read_text(encoding="utf-8")
_LIST_POSTEN_SQL = (SQL_DIR / "queries" / "fire" / "list_posten_for_user.sql").read_text(encoding="utf-8")
_FIND_POST_SQL = (SQL_DIR / "queries" / "fire" / "find_post_for_user.sql").read_text(encoding="utf-8")
_ADD_POST_SQL = (SQL_DIR / "queries" / "fire" / "add_post.sql").read_text(encoding="utf-8")
_UPDATE_POST_SQL = (SQL_DIR / "queries" / "fire" / "update_post.sql").read_text(encoding="utf-8")
_DELETE_POST_SQL = (SQL_DIR / "queries" / "fire" / "delete_post.sql").read_text(encoding="utf-8")
_BASELINE_SQL = (SQL_DIR / "queries" / "fire" / "categorie_baseline_for_user.sql").read_text(encoding="utf-8")

_INSTELLINGEN_URL = "/pensioenplanner/instellingen"

# Sensible starting point for a brand-new instellingen row — conservative
# but not zero, so a first-time visitor's projection isn't a flat line
# before they've tuned anything. Dutch savings/investment ballpark
# figures, not a recommendation.
_DEFAULT_HISTORIE_MAANDEN = 24
_DEFAULT_ALGEMEEN_GROEI_PCT = 2.0
_DEFAULT_RENDEMENT_SPAARGELD_PCT = 1.0
_DEFAULT_RENDEMENT_BELEGGINGEN_PCT = 5.0
_DEFAULT_HORIZON_JAREN = 40


def _parse_optional_int(raw) -> Optional[int]:
    if raw is None:
        return None
    raw = str(raw).strip()
    return int(raw) if raw else None


def _parse_optional_float(raw) -> Optional[float]:
    if raw is None:
        return None
    raw = str(raw).strip()
    return float(raw) if raw else None


def _parse_amount_nl_or(raw, fallback: float) -> float:
    """Dutch-formatted euro input (jaarbedrag) -> float, falling back
    silently on a blank or unparseable value — used by the posten table's
    batch-save, where a mistyped amount shouldn't abort/discard the whole
    table's other edits (there's no per-row error display there, unlike
    the instellingen form's _parse_required_amount_nl below)."""
    raw = (raw or "").strip()
    if not raw:
        return fallback
    try:
        return parse_amount_nl(raw)
    except ValueError:
        return fallback


_AMOUNT_ERROR = "'{raw}' bij {veld} is geen geldig bedrag — gebruik ',' voor decimalen en '.' voor duizendtallen, bijv. '1.234,56'."


def _parse_required_amount_nl(raw: str, veld: str) -> float:
    """Dutch-formatted euro input -> float, raising a ready-to-show Dutch
    ValueError on anything invalid — for the instellingen form's saldo
    fields, which (unlike a posten-table row) get an actual validation
    error + re-rendered form on a bad value."""
    try:
        return parse_amount_nl(raw)
    except ValueError:
        raise ValueError(_AMOUNT_ERROR.format(raw=raw, veld=veld))


def _group_posten(posten) -> tuple[list[dict], list]:
    """Splits the flat posten list into collapsible per-hoofdcategorie
    groups (for posts linked to an existing categorie — see
    sql/schema.sql::fire_posten) plus a flat list of free-standing posts
    (afschrift_cat_id NULL, e.g. a manually-added AOW/pensioen post) that
    have no category to group under. list_posten_for_user.sql already
    orders rows by (type, categorie, subcategorie, omschrijving), so
    simply grouping by first-seen cat_id preserves that order — Inkomsten
    categorieën before Uitgaven ones, alphabetically within each.

    Each group also carries `totaal_jaarbedrag` (sum of its ACTIEVE
    posts' jaarbedrag only) and `type`, both for the collapsed header
    row — every post under one category shares that category's type, so
    there's never a sign ambiguity within a group."""
    groepen: dict = {}
    volgorde: list = []
    losse_posten = []
    for post in posten:
        cat_id = post["afschrift_cat_id"]
        if cat_id is None:
            losse_posten.append(post)
            continue
        if cat_id not in groepen:
            groepen[cat_id] = {"cat_id": cat_id, "category": post["category"], "type": post["type"], "posten": []}
            volgorde.append(cat_id)
        groepen[cat_id]["posten"].append(post)

    result = [groepen[cid] for cid in volgorde]
    for groep in result:
        groep["totaal_jaarbedrag"] = sum(p["jaarbedrag"] for p in groep["posten"] if p["actief"])
    return result, losse_posten


def _resolve_jaar(direct_jaar, leeftijd, persoon_id: Optional[int], personen_by_id: dict) -> Optional[int]:
    """A post's start/stop year can be entered either as a plain calendar
    year or, more conveniently, as an age tied to one of the household's
    tracked personen ("vanaf leeftijd 67 van Reinald") — the latter always
    wins when both are given, and is resolved here, once, into the plain
    calendar year app/fire_projection.py actually runs on."""
    age = _parse_optional_int(leeftijd)
    if age is not None and persoon_id is not None and persoon_id in personen_by_id:
        return personen_by_id[persoon_id]["geboortejaar"] + age
    return _parse_optional_int(direct_jaar)


def _default_instellingen_params(user_id: int, today: date) -> dict:
    return {
        "user_id": user_id,
        "start_jaar": today.year,
        "eind_jaar": today.year + _DEFAULT_HORIZON_JAREN,
        "historie_maanden": _DEFAULT_HISTORIE_MAANDEN,
        "algemeen_groei_pct": _DEFAULT_ALGEMEEN_GROEI_PCT,
        "saldo_spaargeld": 0.0,
        "rendement_spaargeld_pct": _DEFAULT_RENDEMENT_SPAARGELD_PCT,
        "saldo_beleggingen": 0.0,
        "rendement_beleggingen_pct": _DEFAULT_RENDEMENT_BELEGGINGEN_PCT,
    }


def _instellingen_display(instellingen) -> dict:
    """The settings form's two euro fields (saldo_spaargeld/
    saldo_beleggingen) are plain Dutch-formatted text inputs, not native
    number inputs (see pensioenplanner_instellingen.html) — this
    pre-formats a freshly-loaded fire_instellingen row for display.
    NEVER used on a validation-error re-render: there, the raw string the
    user actually typed (possibly invalid) is shown as-is instead, via
    the `submitted` dict built in save_instellingen below, so a typo is
    never silently reformatted or lost."""
    return {
        "start_jaar": instellingen["start_jaar"],
        "eind_jaar": instellingen["eind_jaar"],
        "historie_maanden": instellingen["historie_maanden"],
        "algemeen_groei_pct": instellingen["algemeen_groei_pct"],
        "saldo_spaargeld": format_amount_nl(instellingen["saldo_spaargeld"]),
        "rendement_spaargeld_pct": instellingen["rendement_spaargeld_pct"],
        "saldo_beleggingen": format_amount_nl(instellingen["saldo_beleggingen"]),
        "rendement_beleggingen_pct": instellingen["rendement_beleggingen_pct"],
    }


def _annualized_bedrag(netto_totaal: float, aantal_maanden: int) -> float:
    """fire_posten.jaarbedrag is always a positive magnitude — same
    convention as afschrift.Bedrag_eur, where the sign lives in a
    separate direction field (there Af_bij, here a post's type) rather
    than in the amount itself. categorie_baseline_for_user.sql's
    netto_totaal is signed (Bij minus Af) so it nets a category's mixed-
    direction rows correctly (see its own docstring), but an Uitgaven
    category's net is normally negative — abs() here turns that into the
    magnitude a jaarbedrag is supposed to be; app/fire_projection.py is
    what actually applies the direction, via the post's type."""
    if not aantal_maanden:
        return 0.0
    return abs(netto_totaal / aantal_maanden * 12)


def _sync_voorgestelde_posten(conn, user_id: int, instellingen) -> int:
    """Adds a fire_post for every (categorie, subcategorie) combination
    with historical activity in the configured history window that
    doesn't already have one (regardless of that existing post's actief
    state or how its amount has since been edited) — never touches an
    existing post. Returns how many posts were added."""
    existing = conn.execute(_LIST_POSTEN_SQL, {"user_id": user_id}).fetchall()
    existing_keys = {(r["afschrift_cat_id"], r["afschrift_subcat_id"]) for r in existing}

    end = date.today()
    start = add_months(end.replace(day=1), -instellingen["historie_maanden"])
    baseline_rows = conn.execute(
        _BASELINE_SQL, {"user_id": user_id, "start": start.isoformat(), "end": end.isoformat()}
    ).fetchall()

    added = 0
    for row in baseline_rows:
        key = (row["cat_id"], row["subcat_id"])
        if key in existing_keys:
            continue
        omschrijving = row["category"] if row["subcategorie"] is None else f"{row['category']} > {row['subcategorie']}"
        conn.execute(
            _ADD_POST_SQL,
            {
                "user_id": user_id,
                "omschrijving": omschrijving,
                "afschrift_cat_id": row["cat_id"],
                "afschrift_subcat_id": row["subcat_id"],
                "persoon_id": None,
                "type": row["cat_type"],
                "jaarbedrag": round(_annualized_bedrag(row["netto_totaal"], row["aantal_maanden"]), 2),
                "groei_pct": None,
                "start_jaar": None,
                "stop_jaar": None,
                "eenmalig": 0,
                "actief": 1,
            },
        )
        added += 1
    return added


@router.get("/pensioenplanner/instellingen")
def instellingen_page(request: Request):
    user = require_login(request)
    if isinstance(user, RedirectResponse):
        return user

    conn = get_connection()
    try:
        instellingen = conn.execute(_GET_INSTELLINGEN_SQL, {"user_id": user["id"]}).fetchone()
        if instellingen is None:
            # First-ever visit: seed defaults, then auto-populate posten
            # from grootboek history exactly once — an explicit "ververs
            # voorstellen" covers every visit after this.
            conn.execute(_UPSERT_INSTELLINGEN_SQL, _default_instellingen_params(user["id"], date.today()))
            instellingen = conn.execute(_GET_INSTELLINGEN_SQL, {"user_id": user["id"]}).fetchone()
            added = _sync_voorgestelde_posten(conn, user["id"], instellingen)
            conn.commit()
            log.info("Pensioenplanner: default instellingen + %d post(en) aangemaakt voor gebruiker %s", added, user["id"])

        personen = conn.execute(_LIST_PERSONEN_SQL, {"user_id": user["id"]}).fetchall()
        posten = conn.execute(_LIST_POSTEN_SQL, {"user_id": user["id"]}).fetchall()
    finally:
        conn.close()

    groepen, losse_posten = _group_posten(posten)
    return templates.TemplateResponse(
        request, "pensioenplanner_instellingen.html",
        {
            "user": user, "instellingen": _instellingen_display(instellingen), "personen": personen,
            "groepen": groepen, "losse_posten": losse_posten,
        },
    )


@router.post("/pensioenplanner/instellingen")
def save_instellingen(
    request: Request,
    start_jaar: int = Form(...),
    eind_jaar: int = Form(...),
    historie_maanden: int = Form(...),
    algemeen_groei_pct: float = Form(...),
    saldo_spaargeld: str = Form(...),
    rendement_spaargeld_pct: float = Form(...),
    saldo_beleggingen: str = Form(...),
    rendement_beleggingen_pct: float = Form(...),
):
    user = require_login(request)
    if isinstance(user, RedirectResponse):
        return user

    error = None
    parsed_spaargeld = parsed_beleggingen = None
    try:
        parsed_spaargeld = _parse_required_amount_nl(saldo_spaargeld, "saldo spaargeld")
        parsed_beleggingen = _parse_required_amount_nl(saldo_beleggingen, "saldo beleggingen")
    except ValueError as exc:
        error = str(exc)
    if error is None and eind_jaar <= start_jaar:
        error = "Eindjaar moet na het startjaar liggen."
    elif error is None and historie_maanden <= 0:
        error = "Historieperiode moet minstens 1 maand zijn."

    # Redisplay on error always shows exactly what was typed (Dutch text,
    # possibly invalid) for the two euro fields — never silently
    # reformats or discards it. See _instellingen_display's docstring.
    submitted = {
        "start_jaar": start_jaar, "eind_jaar": eind_jaar, "historie_maanden": historie_maanden,
        "algemeen_groei_pct": algemeen_groei_pct, "saldo_spaargeld": saldo_spaargeld,
        "rendement_spaargeld_pct": rendement_spaargeld_pct, "saldo_beleggingen": saldo_beleggingen,
        "rendement_beleggingen_pct": rendement_beleggingen_pct,
    }

    conn = get_connection()
    try:
        if error is None:
            conn.execute(_UPSERT_INSTELLINGEN_SQL, {
                "user_id": user["id"], "start_jaar": start_jaar, "eind_jaar": eind_jaar,
                "historie_maanden": historie_maanden, "algemeen_groei_pct": algemeen_groei_pct,
                "saldo_spaargeld": parsed_spaargeld, "rendement_spaargeld_pct": rendement_spaargeld_pct,
                "saldo_beleggingen": parsed_beleggingen, "rendement_beleggingen_pct": rendement_beleggingen_pct,
            })
            conn.commit()
        else:
            personen = conn.execute(_LIST_PERSONEN_SQL, {"user_id": user["id"]}).fetchall()
            posten = conn.execute(_LIST_POSTEN_SQL, {"user_id": user["id"]}).fetchall()
    finally:
        conn.close()

    if error:
        log.warning("Failed to save pensioenplanner instellingen for user %s: %s", user["id"], error)
        groepen, losse_posten = _group_posten(posten)
        return templates.TemplateResponse(
            request, "pensioenplanner_instellingen.html",
            {
                "user": user, "instellingen": submitted, "personen": personen,
                "groepen": groepen, "losse_posten": losse_posten, "error": error,
            },
            status_code=400,
        )
    audit.info("Pensioenplanner-instellingen opgeslagen door gebruiker %s", user["id"])
    return RedirectResponse(_INSTELLINGEN_URL, status_code=303)


@router.post("/pensioenplanner/personen")
def add_persoon(request: Request, naam: str = Form(...), geboortejaar: int = Form(...)):
    user = require_login(request)
    if isinstance(user, RedirectResponse):
        return user

    naam = naam.strip()
    conn = get_connection()
    try:
        if naam:
            conn.execute(_ADD_PERSOON_SQL, {"user_id": user["id"], "naam": naam, "geboortejaar": geboortejaar})
            conn.commit()
    finally:
        conn.close()
    audit.info("Persoon '%s' toegevoegd aan pensioenplanner door gebruiker %s", naam, user["id"])
    return RedirectResponse(_INSTELLINGEN_URL, status_code=303)


@router.post("/pensioenplanner/personen/{persoon_id}/delete")
def delete_persoon(request: Request, persoon_id: int):
    user = require_login(request)
    if isinstance(user, RedirectResponse):
        return user

    conn = get_connection()
    try:
        conn.execute(_REMOVE_PERSOON_SQL, {"id": persoon_id, "user_id": user["id"]})
        conn.commit()
    finally:
        conn.close()
    audit.info("Persoon %s verwijderd uit pensioenplanner door gebruiker %s", persoon_id, user["id"])
    return RedirectResponse(_INSTELLINGEN_URL, status_code=303)


@router.post("/pensioenplanner/posten")
def add_post(
    request: Request,
    omschrijving: str = Form(...),
    post_type: str = Form(...),
    jaarbedrag: str = Form("0"),
):
    """Adds a manual, free-standing post (afschrift_cat_id/
    afschrift_subcat_id NULL) — for income/expenses that don't exist in
    transaction history yet, like AOW or pension. Everything else
    (persoon, groei%, start/stop, eenmalig) is left at its default and
    edited afterward via the posten table's batch-save."""
    user = require_login(request)
    if isinstance(user, RedirectResponse):
        return user

    omschrijving = omschrijving.strip()
    error = None
    if not omschrijving:
        error = "Een omschrijving is verplicht."
    elif post_type not in ("Inkomsten", "Uitgaven"):
        error = "Type moet 'Inkomsten' of 'Uitgaven' zijn."

    conn = get_connection()
    try:
        if error is None:
            conn.execute(_ADD_POST_SQL, {
                "user_id": user["id"], "omschrijving": omschrijving, "afschrift_cat_id": None,
                "afschrift_subcat_id": None, "persoon_id": None, "type": post_type,
                "jaarbedrag": _parse_amount_nl_or(jaarbedrag, 0.0),
                "groei_pct": None, "start_jaar": None, "stop_jaar": None, "eenmalig": 0, "actief": 1,
            })
            conn.commit()
        else:
            instellingen = conn.execute(_GET_INSTELLINGEN_SQL, {"user_id": user["id"]}).fetchone()
            personen = conn.execute(_LIST_PERSONEN_SQL, {"user_id": user["id"]}).fetchall()
            posten = conn.execute(_LIST_POSTEN_SQL, {"user_id": user["id"]}).fetchall()
    finally:
        conn.close()

    if error:
        log.warning("Failed to add fire_post for user %s: %s", user["id"], error)
        groepen, losse_posten = _group_posten(posten)
        return templates.TemplateResponse(
            request, "pensioenplanner_instellingen.html",
            {
                "user": user, "instellingen": _instellingen_display(instellingen), "personen": personen,
                "groepen": groepen, "losse_posten": losse_posten, "error": error,
            },
            status_code=400,
        )
    audit.info("Post '%s' toegevoegd aan pensioenplanner door gebruiker %s", omschrijving, user["id"])
    return RedirectResponse(_INSTELLINGEN_URL, status_code=303)


@router.post("/pensioenplanner/posten/save")
async def save_posten(request: Request):
    """Saves every post's editable fields from the instellingen page's
    posten table in one submit — same batch-save-a-whole-table pattern as
    /review/{rekening_id}/save: one `<form>` around the whole table, each
    row's inputs suffixed with that post's ID. "Actief" checkboxes all
    share one name (actief_ids, value=post ID) rather than being
    individually named — a plain multi-value checkbox group, same
    convention as the dashboard's rekening_ids/cat_ids, so the "Alles
    selecteren/deselecteren" buttons (toc_toggle.js) work on it for free."""
    user = require_login(request)
    if isinstance(user, RedirectResponse):
        return user

    form = await request.form()
    actief_ids = set(form.getlist("actief_ids"))
    conn = get_connection()
    try:
        posten = conn.execute(_LIST_POSTEN_SQL, {"user_id": user["id"]}).fetchall()
        personen_by_id = {p["ID"]: p for p in conn.execute(_LIST_PERSONEN_SQL, {"user_id": user["id"]}).fetchall()}

        saved = 0
        for post in posten:
            pid = post["ID"]
            if f"omschrijving_{pid}" not in form:
                continue
            persoon_id = _parse_optional_int(form.get(f"persoon_id_{pid}", ""))
            start_jaar = _resolve_jaar(
                form.get(f"start_jaar_{pid}", ""), form.get(f"start_leeftijd_{pid}", ""), persoon_id, personen_by_id
            )
            stop_jaar = _resolve_jaar(
                form.get(f"stop_jaar_{pid}", ""), form.get(f"stop_leeftijd_{pid}", ""), persoon_id, personen_by_id
            )
            omschrijving = form.get(f"omschrijving_{pid}", "").strip() or post["omschrijving"]
            conn.execute(_UPDATE_POST_SQL, {
                "id": pid,
                "user_id": user["id"],
                "omschrijving": omschrijving,
                "persoon_id": persoon_id,
                "jaarbedrag": _parse_amount_nl_or(form.get(f"jaarbedrag_{pid}", ""), post["jaarbedrag"]),
                "groei_pct": _parse_optional_float(form.get(f"groei_pct_{pid}", "")),
                "start_jaar": start_jaar,
                "stop_jaar": stop_jaar,
                "eenmalig": 1 if form.get(f"eenmalig_{pid}") else 0,
                "actief": 1 if str(pid) in actief_ids else 0,
            })
            saved += 1
        conn.commit()
    finally:
        conn.close()
    audit.info("Pensioenplanner: %d post(en) opgeslagen door gebruiker %s", saved, user["id"])
    return RedirectResponse(_INSTELLINGEN_URL, status_code=303)


@router.post("/pensioenplanner/posten/{post_id}/duplicate")
def duplicate_post(request: Request, post_id: int):
    """Splits a combined historical post (e.g. one "Loon" category
    covering two people's salaries, which the app has no way to separate
    on its own — see docs/ARCHITECTURE.md) into independently editable
    copies: duplicate, then hand-adjust each copy's bedrag/persoon/stop_jaar."""
    user = require_login(request)
    if isinstance(user, RedirectResponse):
        return user

    conn = get_connection()
    try:
        post = conn.execute(_FIND_POST_SQL, {"id": post_id, "user_id": user["id"]}).fetchone()
        if post is None:
            return RedirectResponse(_INSTELLINGEN_URL, status_code=303)
        conn.execute(_ADD_POST_SQL, {
            "user_id": user["id"],
            "omschrijving": f"{post['omschrijving']} (kopie)",
            "afschrift_cat_id": post["afschrift_cat_id"],
            "afschrift_subcat_id": post["afschrift_subcat_id"],
            "persoon_id": post["persoon_id"],
            "type": post["type"],
            "jaarbedrag": post["jaarbedrag"],
            "groei_pct": post["groei_pct"],
            "start_jaar": post["start_jaar"],
            "stop_jaar": post["stop_jaar"],
            "eenmalig": post["eenmalig"],
            "actief": post["actief"],
        })
        conn.commit()
    finally:
        conn.close()
    audit.info("Post %s gedupliceerd in pensioenplanner door gebruiker %s", post_id, user["id"])
    return RedirectResponse(_INSTELLINGEN_URL, status_code=303)


@router.post("/pensioenplanner/posten/{post_id}/delete")
def delete_post(request: Request, post_id: int):
    user = require_login(request)
    if isinstance(user, RedirectResponse):
        return user

    conn = get_connection()
    try:
        conn.execute(_DELETE_POST_SQL, {"id": post_id, "user_id": user["id"]})
        conn.commit()
    finally:
        conn.close()
    audit.info("Post %s verwijderd uit pensioenplanner door gebruiker %s", post_id, user["id"])
    return RedirectResponse(_INSTELLINGEN_URL, status_code=303)


@router.post("/pensioenplanner/posten/ververs")
def ververs_posten(request: Request):
    """Manual re-run of the same auto-population that happens on first
    visit (see instellingen_page above) — for when new categories have
    since gotten historical activity. Never touches an existing post."""
    user = require_login(request)
    if isinstance(user, RedirectResponse):
        return user

    conn = get_connection()
    try:
        instellingen = conn.execute(_GET_INSTELLINGEN_SQL, {"user_id": user["id"]}).fetchone()
        added = 0
        if instellingen is not None:
            added = _sync_voorgestelde_posten(conn, user["id"], instellingen)
            conn.commit()
    finally:
        conn.close()
    audit.info("Pensioenplanner: %d voorgestelde post(en) ververst voor gebruiker %s", added, user["id"])
    return RedirectResponse(_INSTELLINGEN_URL, status_code=303)


def _projection_chart(projectie: dict):
    """Reuses app/dashboard_chart.py's generic x-category/series scaler
    for a yearly (rather than monthly) linegraph — build_chart/
    build_series don't care what the x-axis labels actually mean, only
    that there's one value per label per line."""
    jaren = [str(j["jaar"]) for j in projectie["jaren"]]
    line_defs = [
        {"key": "spaargeld", "label": "Spaargeld", "color_var": "--series-inkomsten", "dash": "none"},
        {"key": "beleggingen", "label": "Beleggingen", "color_var": "--series-cat-0", "dash": "8,4"},
        {"key": "totaal", "label": "Totaal vermogen", "color_var": "--series-verschil", "dash": "2,3"},
    ]
    monthly_values = {}
    for j in projectie["jaren"]:
        key = str(j["jaar"])
        monthly_values[(key, "spaargeld")] = j["saldo_spaargeld"]
        monthly_values[(key, "beleggingen")] = j["saldo_beleggingen"]
        monthly_values[(key, "totaal")] = j["totaal"]
    series = build_series(jaren, line_defs, monthly_values)
    return build_chart(jaren, series)


@router.get("/pensioenplanner")
def pensioenplanner_page(request: Request):
    user = require_login(request)
    if isinstance(user, RedirectResponse):
        return user

    conn = get_connection()
    try:
        instellingen = conn.execute(_GET_INSTELLINGEN_SQL, {"user_id": user["id"]}).fetchone()
        if instellingen is None:
            return RedirectResponse(_INSTELLINGEN_URL, status_code=303)
        personen = conn.execute(_LIST_PERSONEN_SQL, {"user_id": user["id"]}).fetchall()
        posten = conn.execute(_LIST_POSTEN_SQL, {"user_id": user["id"]}).fetchall()
    finally:
        conn.close()

    projectie = build_projection(instellingen, posten, personen)
    chart = _projection_chart(projectie) if projectie["jaren"] else None

    return templates.TemplateResponse(
        request, "pensioenplanner.html",
        {
            "user": user, "instellingen": instellingen, "personen": personen,
            "projectie": projectie, "chart": chart, "export_url": "/pensioenplanner/export",
        },
    )


@router.get("/pensioenplanner/export")
def export_csv(request: Request):
    user = require_login(request)
    if isinstance(user, RedirectResponse):
        return user

    conn = get_connection()
    try:
        instellingen = conn.execute(_GET_INSTELLINGEN_SQL, {"user_id": user["id"]}).fetchone()
        if instellingen is None:
            return RedirectResponse(_INSTELLINGEN_URL, status_code=303)
        personen = conn.execute(_LIST_PERSONEN_SQL, {"user_id": user["id"]}).fetchall()
        posten = conn.execute(_LIST_POSTEN_SQL, {"user_id": user["id"]}).fetchall()
    finally:
        conn.close()

    projectie = build_projection(instellingen, posten, personen)

    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow(
        ["Jaar"] + [f"Leeftijd {p['naam']}" for p in personen]
        + ["Inkomsten", "Uitgaven", "Netto", "Spaargeld", "Beleggingen", "Totaal vermogen"]
    )
    for j in projectie["jaren"]:
        writer.writerow(
            [j["jaar"]] + [j["leeftijden"][p["ID"]] for p in personen] + [
                format_amount_nl(j["inkomsten"]), format_amount_nl(j["uitgaven"]), format_amount_nl(j["netto"]),
                format_amount_nl(j["saldo_spaargeld"]), format_amount_nl(j["saldo_beleggingen"]),
                format_amount_nl(j["totaal"]),
            ]
        )

    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="pensioenplanner.csv"'},
    )
