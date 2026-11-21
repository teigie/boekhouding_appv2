"""Entry point: starts the local server.

Usage:
    python run.py

Two modes, both on 127.0.0.1:8000:

- Default (BOEKHOUDING_RELOAD unset or "1"): today's dev behavior,
  unchanged — `uvicorn.run(..., reload=True)`, auto-restarts on code
  changes. Idle-shutdown (see app/idle_shutdown.py) is inert in this mode
  regardless of BOEKHOUDING_IDLE_TIMEOUT_MINUTES, since --reload runs the
  app in a supervised subprocess this script has no direct handle to.
- BOEKHOUDING_RELOAD=0 (what start_app.sh/.bat use): launcher mode. This
  process is a tiny *supervisor* that runs the actual server as a child
  process (same script, BOEKHOUDING_SERVER_CHILD=1) and waits for it:
  - child exits with RESTART_EXIT_CODE ("Nu bijwerken" pulled new code,
    see app/version.py's apply_update): start a fresh child, which loads
    the freshly pulled code;
  - any other exit (idle-shutdown, crash, Ctrl+C): the supervisor exits
    too.
  The child builds a single uvicorn.Server, stashed on
  app.state.uvicorn_server so idle-shutdown and the updater can flip
  `should_exit` on it.

Why a supervisor instead of the old server spawning its own replacement:
on Windows a detached replacement spawned from the dying pythonw.exe
never came up (port still held by the old server, no std handles, and
possibly killed along with its parent's process tree). Here the old
child has fully exited — port released — before the next one starts, and
the supervisor never goes away in between.

Keep this file's supervisor part small and stable: after an update, the
*already running* supervisor is still the old code (only the child is
restarted), so changes here only take effect on the next manual start.
"""
import asyncio
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import uvicorn

RELOAD = os.environ.get("BOEKHOUDING_RELOAD", "1") != "0"
PORT = int(os.environ.get("BOEKHOUDING_PORT", "8000"))
HOST = "127.0.0.1"
RESTART_EXIT_CODE = 3
_CHILD_ENV = "BOEKHOUDING_SERVER_CHILD"
_PORT_WAIT_SECONDS = 20
_BASE_DIR = Path(__file__).resolve().parent


def _ensure_std_streams() -> None:
    """pythonw.exe without usable std handles has sys.stdout/sys.stderr =
    None — uvicorn's log formatter then crashes on sys.stdout.isatty()
    before the server is up. Point them at the same files start_app.bat
    redirects to (or devnull if even that fails)."""
    log_dir = _BASE_DIR / "logs"
    for name, filename in (("stdout", "launcher-stdout.log"), ("stderr", "launcher-stderr.log")):
        if getattr(sys, name) is not None:
            continue
        try:
            log_dir.mkdir(exist_ok=True)
            stream = open(log_dir / filename, "a", encoding="utf-8", buffering=1)
        except OSError:
            stream = open(os.devnull, "w", encoding="utf-8")
        setattr(sys, name, stream)


def _wait_for_free_port() -> None:
    """Belt and braces: the previous server should already be gone, but
    if anything still holds the port, wait for it rather than failing to
    bind immediately (Windows has no SO_REUSEADDR on asyncio's listener).
    start_app.bat already checks nothing is serving before it launches,
    so in normal starts this returns at once."""
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


def _serve() -> int:
    """The actual server (launcher mode child). Returns the exit code."""
    _ensure_std_streams()
    _wait_for_free_port()
    from app.main import app

    config = uvicorn.Config(app, host=HOST, port=PORT)
    server = uvicorn.Server(config)
    app.state.uvicorn_server = server
    asyncio.run(server.serve())
    return RESTART_EXIT_CODE if getattr(app.state, "restart_requested", False) else 0


def _supervise() -> int:
    """Launcher mode parent: (re)starts the server child until it exits
    for any reason other than a requested restart."""
    _ensure_std_streams()
    env = os.environ.copy()
    env[_CHILD_ENV] = "1"
    # Hand our (redirected) std streams to the child explicitly, so it
    # gets valid handles even under pythonw.exe.
    std = {}
    for name in ("stdout", "stderr"):
        stream = getattr(sys, name)
        try:
            stream.flush()
            stream.fileno()
            std[name] = stream
        except (AttributeError, OSError, ValueError):
            pass
    while True:
        try:
            rc = subprocess.call([sys.executable, str(Path(__file__).resolve())], cwd=_BASE_DIR, env=env, **std)
        except KeyboardInterrupt:
            return 0
        if rc != RESTART_EXIT_CODE:
            return rc
        print("Server vraagt om herstart na update — opnieuw starten...", file=sys.stderr, flush=True)


if __name__ == "__main__":
    if RELOAD:
        uvicorn.run("app.main:app", host=HOST, port=PORT, reload=True)
    elif os.environ.get(_CHILD_ENV) == "1":
        sys.exit(_serve())
    else:
        sys.exit(_supervise())
