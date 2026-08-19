"""Backs the update banner shown on every page (base.html, via the
"update_info" Jinja global — app/templating.py) when app/version.py's
startup check found the clone is behind origin/main. This module only
owns the one write action, applying it — the check itself, and the
banner markup, live elsewhere (see app/version.py's module docstring for
the full picture).
"""
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from app.logging_config import get_app_logger
from app.session import require_login
from app.templating import templates
from app.version import UpdateApplyError, apply_update

log = get_app_logger()
router = APIRouter()


@router.post("/update/apply")
def update_apply(request: Request):
    """Pulls + restarts (app/version.py::apply_update). On success,
    renders a standalone "bezig met bijwerken" page whose own script
    polls the server and reloads once it's back — deliberately not
    base.html-based, since by the time this response is sent the server
    may already be mid-restart (launcher mode: the replacement process is
    already starting; reload mode: uvicorn's file watcher may fire any
    moment) and a normal page's nav/banner would just be confusing here.
    On failure (git pull itself refused — a merge conflict, local edits,
    lost connectivity since the check ran), nothing was touched; renders
    a small error page with the reason instead of guessing which page to
    re-render, since the banner can be triggered from anywhere.
    """
    user = require_login(request)
    if isinstance(user, RedirectResponse):
        return user

    try:
        apply_update(request.app)
    except UpdateApplyError as exc:
        log.warning("Update failed for user %s: %s", user["id"], exc)
        return templates.TemplateResponse(request, "update_failed.html", {"error": str(exc)}, status_code=500)

    return templates.TemplateResponse(request, "update_pending.html", {})
