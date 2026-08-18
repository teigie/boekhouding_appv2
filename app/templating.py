"""Shared Jinja2Templates instance, so every router points at the same
template directory without each re-constructing its own."""
from fastapi.templating import Jinja2Templates

from app.config import BASE_DIR
from app.formatting import format_date_eu, format_datetime_eu, format_month_nl

templates = Jinja2Templates(directory=BASE_DIR / "app" / "templates")
templates.env.filters["eu_datetime"] = format_datetime_eu
templates.env.filters["eu_date"] = format_date_eu
templates.env.filters["maand_nl"] = format_month_nl
