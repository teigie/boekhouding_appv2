"""Entry point: starts the local development server.

Usage:
    python run.py

Two modes, both on 127.0.0.1:8000:

- Default (BOEKHOUDING_RELOAD unset or "1"): today's dev behavior,
  unchanged — `uvicorn.run(..., reload=True)`, auto-restarts on code
  changes. Idle-shutdown (see app/idle_shutdown.py) is inert in this mode
  regardless of BOEKHOUDING_IDLE_TIMEOUT_MINUTES, since --reload runs the
  app in a supervised subprocess this script has no direct handle to.
- BOEKHOUDING_RELOAD=0 (what start_app.sh/.bat/.ps1 use): a single
  uvicorn.Server built here directly, stashed on app.state.uvicorn_server
  so the idle-shutdown background task can flip `should_exit` on it and
  have the app close itself down after N idle minutes.
"""
import asyncio
import os

import uvicorn

RELOAD = os.environ.get("BOEKHOUDING_RELOAD", "1") != "0"
PORT = int(os.environ.get("BOEKHOUDING_PORT", "8000"))

if __name__ == "__main__":
    if RELOAD:
        uvicorn.run("app.main:app", host="127.0.0.1", port=PORT, reload=True)
    else:
        from app.main import app

        config = uvicorn.Config(app, host="127.0.0.1", port=PORT)
        server = uvicorn.Server(config)
        app.state.uvicorn_server = server
        asyncio.run(server.serve())
