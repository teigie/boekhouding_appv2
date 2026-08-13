"""SQLite connection handling + one-time schema/seed initialization.

All actual SQL lives under sql/ as tracked .sql files (see sql/README.md).
This module only knows how to open a connection and run a .sql file's
contents — it never builds queries as Python strings.
"""
import sqlite3
from pathlib import Path

from app.config import DB_PATH, SQL_DIR
from app.logging_config import get_app_logger

log = get_app_logger()


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def run_sql_file(conn: sqlite3.Connection, path: Path) -> None:
    """Execute every statement in a .sql file against an open connection."""
    sql = path.read_text(encoding="utf-8")
    conn.executescript(sql)


def init_db() -> None:
    """Create the database from schema.sql + seed_data.sql if it doesn't
    exist yet. Safe to call on every app startup — a no-op once the
    database file is already present.
    """
    is_new = not DB_PATH.exists()
    if not is_new:
        log.info("Database already exists at %s, skipping initialization", DB_PATH)
        return

    log.info("No database found at %s — creating one from schema.sql + seed_data.sql", DB_PATH)
    conn = get_connection()
    try:
        run_sql_file(conn, SQL_DIR / "schema.sql")
        run_sql_file(conn, SQL_DIR / "seed_data.sql")
        conn.commit()
        log.info("Database created and seeded successfully")
    except Exception:
        log.exception("Database initialization failed")
        raise
    finally:
        conn.close()
