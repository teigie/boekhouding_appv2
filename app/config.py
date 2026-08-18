"""Central paths, resolved relative to this file rather than hardcoded, so
the project runs the same regardless of where it's cloned to or which
machine it's on.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SQL_DIR = BASE_DIR / "sql"
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "boekhouding.db"
LOG_DIR = BASE_DIR / "logs"
# Generated locally on first run, gitignored — signs the login session
# cookie so it can't be casually edited in the browser (e.g. changing
# user_id). There's no password behind this login (see docs/ARCHITECTURE.md
# — you just pick who you are), so this isn't securing a secret, only
# making the "who am I" cookie tamper-evident and keeping people logged in
# across server restarts.
SESSION_SECRET_PATH = DATA_DIR / ".session_secret"

DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

# Auto-afsluiten na inactiviteit — voor de "snelkoppeling"-manier van
# starten (start_app.sh/.bat), niet voor `python run.py` tijdens
# ontwikkelen: dat blijft ongewijzigd draaien met reload=True. Zie
# app/idle_shutdown.py. 0 (de default) = uitgeschakeld.
IDLE_TIMEOUT_MINUTES = float(os.environ.get("BOEKHOUDING_IDLE_TIMEOUT_MINUTES", "0"))
IDLE_TIMEOUT_SECONDS = IDLE_TIMEOUT_MINUTES * 60
