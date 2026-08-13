"""HTTP layer for uploads — thin wrapper around app/upload.py's pipeline.
Parsing/validation/insertion logic lives there; this file only handles the
request/response and the form."""
from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import RedirectResponse

from app.importers.registry import IMPORTERS
from app.logging_config import get_app_logger
from app.session import require_login
from app.templating import templates
from app.upload import process_upload

log = get_app_logger()
router = APIRouter()


@router.get("/upload")
def upload_page(request: Request):
    user = require_login(request)
    if isinstance(user, RedirectResponse):
        return user
    return templates.TemplateResponse(request, "upload.html", {"importers": IMPORTERS.values()})


@router.post("/upload")
async def upload_submit(request: Request, format_id: str = Form(...), file: UploadFile = File(...)):
    user = require_login(request)
    if isinstance(user, RedirectResponse):
        return user

    file_bytes = await file.read()
    try:
        results = process_upload(file_bytes, format_id, user["id"])
    except ValueError as exc:
        # Parsing error (unreadable/wrong-format file) — not a per-account
        # accept/reject outcome, so it's shown separately.
        log.warning("Upload parse error for user %s: %s", user["id"], exc)
        return templates.TemplateResponse(
            request, "upload.html",
            {"importers": IMPORTERS.values(), "parse_error": str(exc)},
            status_code=400,
        )

    return templates.TemplateResponse(
        request, "upload.html", {"importers": IMPORTERS.values(), "results": results}
    )
