"""FastAPI application entry point.

Wires up logging, the session/login system, static files, and the app's
routers. See docs/ARCHITECTURE.md for the intended pipeline.
"""
import asyncio
import contextlib
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import BASE_DIR
from app.db import init_db
from app.idle_shutdown import record_activity, watch_idle
from app.logging_config import get_app_logger, setup_logging
from app.routes import accounts, auth, categories, dashboard, review, update, upload, user
from app.session import get_or_create_session_secret
from app.version import refresh_update_check

setup_logging()
log = get_app_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Starting up")
    init_db()
    idle_task = asyncio.create_task(watch_idle(app))
    # Runs in a thread (it shells out to git, which blocks) and is fully
    # fire-and-forget — a slow or offline check must never delay the
    # server actually coming up. Result lands in app.version's module-
    # level cache, read by the update banner on every page render (see
    # app/templating.py's "update_info" Jinja global).
    update_check_task = asyncio.create_task(asyncio.to_thread(refresh_update_check))
    yield
    idle_task.cancel()
    update_check_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await idle_task
    with contextlib.suppress(asyncio.CancelledError):
        await update_check_task
    log.info("Shutting down")


app = FastAPI(title="Boekhouding", lifespan=lifespan)

app.add_middleware(SessionMiddleware, secret_key=get_or_create_session_secret())

app.mount("/static", StaticFiles(directory=BASE_DIR / "app" / "static"), name="static")

app.include_router(auth.router)
app.include_router(accounts.router)
app.include_router(categories.router)
app.include_router(dashboard.router)
app.include_router(upload.router)
app.include_router(review.router)
app.include_router(update.router)
app.include_router(user.router)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    record_activity(request)
    start = time.monotonic()
    response = await call_next(request)
    duration_ms = (time.monotonic() - start) * 1000
    log.info(
        "%s %s -> %s (%.1fms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response
