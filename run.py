"""Entry point: starts the local development server.

Usage:
    python run.py

Two modes, both on 127.0.0.1:8000:

- Default (BOEKHOUDING_RELOAD unset or "1"): today's dev behavior,
  unchanged — `uvicorn.run(..., reload=True)`, auto-restarts on code
  changes. Idle-shutdown (see app/idle_shutdown.py) is inert in this mode
  regardless of BOEKHOUDING_IDLE_TIMEOUT_MINUTES, since --reload runs the
  app in a supervised subprocess this script has no direct handle to.
- BOEKHOUDING_RELOAD=0 (what start_app.sh/.bat use): a single
  uvicorn.Server built here directly, stashed on app.state.uvicorn_server
  so the idle-shutdown background task can flip `should_exit` on it and
  have the app close itself down after N idle minutes.
"""
import asyncio
import os
import socket
import sys
import time
from pathlib import Path

import uvicorn

RELOAD = os.environ.get("BOEKHOUDING_RELOAD", "1") != "0"
PORT = int(os.environ.get("BOEKHOUDING_PORT", "8000"))
HOST = "127.0.0.1"
_PORT_WAIT_SECONDS = 20


def _ensure_std_streams() -> None:
    """pythonw.exe started without inherited std handles (the self-update
    spawns its replacement server detached, see app/version.py's
    apply_update) has sys.stdout/sys.stderr = None — uvicorn's log
    formatter then crashes on sys.stdout.isatty() before the server is
    up. Point them at the same files start_app.bat redirects to."""
    log_dir = Path(__file__).resolve().parent / "logs"
    if sys.stdout is None or sys.stderr is None:
        log_dir.mkdir(exist_ok=True)
    if sys.stdout is None:
        sys.stdout = open(log_dir / "launcher-stdout.log", "a", encoding="utf-8", buffering=1)
    if sys.stderr is None:
        sys.stderr = open(log_dir / "launcher-stderr.log", "a", encoding="utf-8", buffering=1)


def _wait_for_free_port() -> None:
    """After "Nu bijwerken" the replacement process starts while the old
    server is still shutting down and holding the port; binding right
    away fails (Windows has no SO_REUSEADDR on asyncio's listener) and
    the new server exits — leaving no server at all. Wait for the port
    to be released first. start_app.bat already checks nothing is
    serving before it launches, so in normal starts this returns at once.
    """
    deadline = time.monotonic() + _PORT_WAIT_SECONDS
    while True:
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if os.name != "nt":
            # Mirrors asyncio's own listener on POSIX, so lingering
            # TIME_WAIT connections don't count as "in use".
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind((HOST, PORT))
            return
        except OSError:
            if time.monotonic() >= deadline:
                return  # let uvicorn try anyway and report the real error
            time.sleep(0.5)
        finally:
            probe.close()


if __name__ == "__main__":
    if RELOAD:
        uvicorn.run("app.main:app", host=HOST, port=PORT, reload=True)
    else:
        _ensure_std_streams()
        _wait_for_free_port()
        from app.main import app

        config = uvicorn.Config(app, host=HOST, port=PORT)
        server = uvicorn.Server(config)
        app.state.uvicorn_server = server
        asyncio.run(server.serve())
