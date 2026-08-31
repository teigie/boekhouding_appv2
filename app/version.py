"""Version tracking and update checking, driven entirely by
CHANGELOG.md's `## [x.y.z] - YYYY-MM-DD — Title` headings — there is
deliberately no separate VERSION file, so the changelog can never drift
out of sync with "what version is this checkout".

The whole feature is best-effort by design: this app has no update
server of its own, it just asks git whether the clone it's running from
is behind its own remote. Anything that can go wrong (no network, `git`
missing, this isn't actually a git checkout, a merge conflict) is
treated as "can't tell, so don't bother the user" rather than an error —
checking for updates must never get in the way of using the app.

The overall flow (see docs/ARCHITECTURE.md for the full design):
- `refresh_update_check()` runs once at startup (app/main.py's lifespan,
  as a background task so a slow/offline `git fetch` never delays the
  server coming up) and caches the result in this module.
- `get_cached_update_info()` is registered as a Jinja global
  (app/templating.py) so base.html can render the update banner on every
  page without every route handler having to thread it through its own
  template context.
- `apply_update()` is what the banner's "Nu bijwerken" button triggers
  (`POST /update/apply`, app/routes/update.py) — pulls, reinstalls
  dependencies if requirements.txt changed, and restarts the server.
"""
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from typing import List, Optional

from fastapi import FastAPI

from app.config import BASE_DIR
from app.logging_config import get_app_logger, get_audit_logger

log = get_app_logger()
audit = get_audit_logger()

_CHANGELOG_PATH = BASE_DIR / "CHANGELOG.md"
_VERSION_HEADING = re.compile(r"^## \[(\d+\.\d+\.\d+)\] - (\d{4}-\d{2}-\d{2}) — (.+)$", re.MULTILINE)
_REMOTE = "origin"
_BRANCH = "main"


@dataclass
class ChangelogEntry:
    version: str
    date: str
    title: str
    body: str


@dataclass
class UpdateInfo:
    current_version: str
    latest_version: str
    missed_entries: List[ChangelogEntry]  # newest first, at least one


def _version_tuple(v: str) -> tuple:
    return tuple(int(p) for p in v.split("."))


def parse_changelog(text: str) -> List[ChangelogEntry]:
    """Every `## [x.y.z] - date — title` section in a CHANGELOG.md's raw
    text, in whichever order they appear in the file (this project keeps
    them newest-first — see CHANGELOG.md's own intro paragraph). Anything
    before the first heading (the file's intro text) is ignored."""
    matches = list(_VERSION_HEADING.finditer(text))
    entries = []
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        entries.append(
            ChangelogEntry(version=m.group(1), date=m.group(2), title=m.group(3), body=text[start:end].strip("\n"))
        )
    return entries


def current_version() -> Optional[str]:
    """This checkout's own version — the topmost (newest) entry in the
    local CHANGELOG.md. None if the file is missing or has no version
    heading yet, so a malformed/absent changelog degrades to "no version
    info" instead of crashing anything that calls this."""
    if not _CHANGELOG_PATH.exists():
        return None
    entries = parse_changelog(_CHANGELOG_PATH.read_text(encoding="utf-8"))
    return entries[0].version if entries else None


def _run_git(*args: str, timeout: float = 10.0) -> Optional[str]:
    """Runs a git command in BASE_DIR. Returns stdout on success, None on
    ANY failure — not a git repo, git not on PATH, no network, timeout,
    non-zero exit. Every caller treats "couldn't check" identically to
    "nothing new", per this module's docstring."""
    try:
        result = subprocess.run(
            ["git", *args], cwd=BASE_DIR, capture_output=True, text=True, timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        log.info("Update check skipped (git %s failed to run: %s)", args[0] if args else "?", exc)
        return None
    if result.returncode != 0:
        log.info("Update check skipped (git %s exited %d: %s)", args, result.returncode, result.stderr.strip())
        return None
    return result.stdout


def check_for_update(remote: str = _REMOTE, branch: str = _BRANCH) -> Optional[UpdateInfo]:
    """Best-effort: `git fetch` then compares this checkout's CHANGELOG.md
    against the fetched remote branch's CHANGELOG.md, without touching the
    working tree at all (`git show <ref>:CHANGELOG.md` reads a blob from
    the fetched history, it doesn't check anything out) — actually
    applying an update is a separate, explicit step (apply_update below).
    Returns None if there's nothing newer, or if the check itself
    couldn't run for any reason.
    """
    if _run_git("fetch", remote, branch) is None:
        return None

    local_version = current_version()
    if local_version is None:
        return None

    remote_text = _run_git("show", f"{remote}/{branch}:CHANGELOG.md")
    if remote_text is None:
        return None
    remote_entries = parse_changelog(remote_text)
    if not remote_entries:
        return None
    remote_version = remote_entries[0].version

    if _version_tuple(remote_version) <= _version_tuple(local_version):
        return None

    missed = [e for e in remote_entries if _version_tuple(e.version) > _version_tuple(local_version)]
    return UpdateInfo(current_version=local_version, latest_version=remote_version, missed_entries=missed)


# Cached at startup (see refresh_update_check) and read on every page
# render via the Jinja global registered in app/templating.py — a module-
# level cache rather than app.state so templates.py's global function
# doesn't need a request/app reference to read it.
_cached_update_info: Optional[UpdateInfo] = None


def get_cached_update_info() -> Optional[UpdateInfo]:
    return _cached_update_info


def refresh_update_check() -> None:
    """Runs check_for_update() and stores the result for
    get_cached_update_info() to serve. Called once at startup
    (app/main.py's lifespan, as a fire-and-forget background task) —
    never re-checked while the server keeps running, since a restart
    (the launcher scripts, or this very update mechanism) is the natural
    point to check again."""
    global _cached_update_info
    _cached_update_info = check_for_update()
    if _cached_update_info:
        log.info(
            "Update available: %s -> %s (%d entr%s missed)",
            _cached_update_info.current_version,
            _cached_update_info.latest_version,
            len(_cached_update_info.missed_entries),
            "y" if len(_cached_update_info.missed_entries) == 1 else "ies",
        )


class UpdateApplyError(Exception):
    """Raised when `git pull` itself fails (merge conflict, local edits
    in the way, lost connectivity between the check and the click, etc.)
    — nothing was restarted, the app keeps running exactly as it was."""


def apply_update(app: FastAPI) -> None:
    """Pulls the latest commit(s) from origin/main, reinstalls
    dependencies if requirements.txt changed, and restarts the server —
    triggered by the update banner's "Nu bijwerken" button
    (POST /update/apply, app/routes/update.py). Fast-forward only: if the
    local checkout has diverged (shouldn't happen for an end user who
    never edits the code, but would for a developer with uncommitted/
    unpushed work), this refuses rather than risking a merge.
    """
    before = _run_git("rev-parse", "HEAD")

    result = subprocess.run(
        ["git", "pull", "--ff-only", _REMOTE, _BRANCH], cwd=BASE_DIR, capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        raise UpdateApplyError(result.stderr.strip() or result.stdout.strip() or "git pull failed")

    after = _run_git("rev-parse", "HEAD")
    audit.info("Update pulled: %s -> %s", before, after)

    if before and after and before != after:
        changed = subprocess.run(
            ["git", "diff", "--name-only", before, after], cwd=BASE_DIR, capture_output=True, text=True, timeout=10,
        )
        if changed.returncode == 0 and "requirements.txt" in changed.stdout.split():
            log.info("requirements.txt changed by the update — running pip install")
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], cwd=BASE_DIR, timeout=180,
            )

    global _cached_update_info
    _cached_update_info = None

    server = getattr(app.state, "uvicorn_server", None)
    if server is None:
        # Plain `python run.py` (reload=True): the .py files git pull just
        # rewrote are enough on their own to make uvicorn's file watcher
        # restart the reloaded subprocess — nothing further to do here.
        log.info("Update applied in --reload mode; the file watcher will restart the app on its own.")
        return

    # Launcher mode (BOEKHOUDING_RELOAD=0, start_app.sh/.bat/): once
    # this server exits, nothing brings it back — the launcher script only
    # starts it once, at the initial double-click. So the replacement
    # process has to be spawned here, before asking this one to stop, or
    # the user is left with no server at all.
    env = os.environ.copy()
    popen_kwargs = {}
    if os.name == "nt":
        popen_kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        popen_kwargs["start_new_session"] = True
    subprocess.Popen([sys.executable, "run.py"], cwd=BASE_DIR, env=env, **popen_kwargs)
    audit.info("Spawned replacement server process after update")
    server.should_exit = True
