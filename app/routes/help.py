"""Static "hoe werkt de app"-uitlegpagina (de "i"-knop in de navbalk,
tussen de gebruikersnaam-link en "Uitloggen" — zie app/templates/base.html).
Puur statische content, dus geen database-query's nodig."""
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from app.session import require_login
from app.templating import templates

router = APIRouter()


@router.get("/uitleg")
def uitleg_page(request: Request):
    user = require_login(request)
    if isinstance(user, RedirectResponse):
        return user
    return templates.TemplateResponse(request, "uitleg.html", {})
