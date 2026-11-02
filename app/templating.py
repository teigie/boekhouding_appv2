"""Shared Jinja2Templates instance, so every router points at the same
template directory without each re-constructing its own."""
from fastapi.templating import Jinja2Templates

from app.config import BASE_DIR

_STATIC_DIR = BASE_DIR / "app" / "static"


def static_url(path: str) -> str:
    """"js/dashboard.js" -> "/static/js/dashboard.js?v=<mtime>" — the
    mtime-based query string changes the moment the file is edited, so
    a normal reload always picks up the new version instead of the
    browser serving a stale cached copy of a .js/.css file it has no
    other reason to re-fetch (StaticFiles sets no Cache-Control, but
    browsers still apply heuristic caching off Last-Modified)."""
    try:
        version = int((_STATIC_DIR / path).stat().st_mtime)
    except OSError:
        version = 0
    return f"/static/{path}?v={version}"
from app.formatting import (
    format_amount_nl,
    format_amount_nl_whole,
    format_date_eu,
    format_datetime_eu,
    format_month_nl,
)
from app.session import current_user
from app.version import get_cached_update_info

templates = Jinja2Templates(directory=BASE_DIR / "app" / "templates")
templates.env.filters["eu_datetime"] = format_datetime_eu
templates.env.filters["eu_date"] = format_date_eu
templates.env.filters["maand_nl"] = format_month_nl
templates.env.filters["bedrag_nl"] = format_amount_nl
templates.env.filters["bedrag_nl_whole"] = format_amount_nl_whole
# Callable rather than a plain value: the startup update check
# (app/version.py::refresh_update_check) runs in the background and
# fills this in after the server's already serving requests, so
# base.html's `update_info()` call must re-read the cache on every
# render, not capture whatever it was when this module first imported.
templates.env.globals["update_info"] = get_cached_update_info
# Templates (base.html's nav, mainly) must check this rather than reading
# request.session.get("user_id") directly — that raw dict can still hold
# a previous process's login (see app/session.py's _BOOT_ID) even when
# current_user() correctly reports logged-out, which would otherwise
# show a stale "logged in as ..." header on the very /login page that
# boot-id check just redirected to.
templates.env.globals["current_user"] = current_user
templates.env.globals["static_url"] = static_url
