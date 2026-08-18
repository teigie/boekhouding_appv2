"""Auto-shutdown after N minutes without any HTTP request.

Why idle time rather than "browser tab closed": this is a traditional
server-rendered app (full page loads via Jinja2), not a single-page app —
every internal link click triggers the same `beforeunload`/`pagehide`
events a real tab close would. There is no reliable way for the browser to
tell the server "the user is gone" versus "the user clicked a link", so
tracking real request activity is the only robust signal available.

Only takes effect when `run.py` starts uvicorn as a single process (no
--reload) and stashes the `uvicorn.Server` on `app.state.uvicorn_server` —
see `run.py`. In reload mode (plain `python run.py` during development)
`app.state.uvicorn_server` is never set, so this silently does nothing,
leaving today's dev workflow unchanged.
"""
import asyncio
import time

from fastapi import FastAPI, Request

from app.config import IDLE_TIMEOUT_SECONDS
from app.logging_config import get_app_logger

log = get_app_logger()

_CHECK_INTERVAL_SECONDS = 15


def record_activity(request: Request) -> None:
    """Called once per request (see the log_requests middleware in
    app/main.py) to reset the idle clock."""
    request.app.state.last_activity_monotonic = time.monotonic()


async def watch_idle(app: FastAPI) -> None:
    """Background task: sleeps, checks, and once nothing has hit the
    server for IDLE_TIMEOUT_SECONDS, asks uvicorn to shut down."""
    if IDLE_TIMEOUT_SECONDS <= 0:
        return
    server = getattr(app.state, "uvicorn_server", None)
    if server is None:
        log.info(
            "BOEKHOUDING_IDLE_TIMEOUT_MINUTES is ingesteld maar wordt genegeerd "
            "— alleen actief zonder --reload (zie run.py)."
        )
        return

    log.info("Idle-shutdown actief: %.0f minuten zonder verkeer sluit de server af.", IDLE_TIMEOUT_SECONDS / 60)
    app.state.last_activity_monotonic = time.monotonic()

    while not server.should_exit:
        await asyncio.sleep(_CHECK_INTERVAL_SECONDS)
        idle_for = time.monotonic() - app.state.last_activity_monotonic
        if idle_for >= IDLE_TIMEOUT_SECONDS:
            log.info(
                "Geen verkeer in %.0f minuten — server wordt afgesloten.",
                idle_for / 60,
            )
            server.should_exit = True
            return
