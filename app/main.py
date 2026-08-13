"""FastAPI application entry point.

Wires up logging, the session/login system, static files, and the app's
routers. See docs/ARCHITECTURE.md for the intended pipeline.
"""
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import BASE_DIR
from app.db import init_db
from app.logging_config import get_app_logger, setup_logging
from app.routes import accounts, auth, dashboard, upload
from app.session import get_or_create_session_secret

setup_logging()
log = get_app_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Starting up")
    init_db()
    yield
    log.info("Shutting down")


app = FastAPI(title="Boekhouding", lifespan=lifespan)

app.add_middleware(SessionMiddleware, secret_key=get_or_create_session_secret())

app.mount("/static", StaticFiles(directory=BASE_DIR / "app" / "static"), name="static")

app.include_router(auth.router)
app.include_router(accounts.router)
app.include_router(dashboard.router)
app.include_router(upload.router)


@app.middleware("http")
async def log_requests(request: Request, call_next):
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
