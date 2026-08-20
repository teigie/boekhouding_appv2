"""Shared Jinja2Templates instance, so every router points at the same
template directory without each re-constructing its own."""
from fastapi.templating import Jinja2Templates

from app.config import BASE_DIR
from app.formatting import (
    format_amount_nl,
    format_amount_nl_whole,
    format_date_eu,
    format_datetime_eu,
    format_month_nl,
)
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
