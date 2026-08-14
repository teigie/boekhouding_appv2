"""Categorization pipeline: resolves an account's entire pending
temp_afschrift2 backlog into temp_afschrift rows with real foreign keys
and a `processed` status. See docs/ARCHITECTURE.md.

Rekening_ID/Mutatiesoort_ID resolution is independent of `processed` —
both are expected to always resolve (the account was already validated at
upload time; mutatiesoort_mapping is structural reference data).
`processed` reflects only the combined category-match outcome, from three
signals: Naam keywords, Mededeling keywords, and Tegenrekening resolving
to another account of the same user ("Interne overboeking") — see
sql/categorization/README.md for the current (provisional) combination
strategy.

Must always run against an account's FULL current temp_afschrift2 backlog
in one atomic transaction, never a partial subset — see
docs/ARCHITECTURE.md for why row order across the pipeline's tables
depends on this.

All SQL lives under sql/ as tracked files (see sql/README.md) — this
module only reads and executes them, it never assembles SQL strings.
"""
import sqlite3
from dataclasses import dataclass
from typing import Optional

from app.config import SQL_DIR
from app.db import get_connection
from app.logging_config import get_app_logger, get_audit_logger

log = get_app_logger()
audit = get_audit_logger()

_FIND_REKENING_SQL = (SQL_DIR / "queries" / "rekeningen" / "find_by_name.sql").read_text(encoding="utf-8")
_CATEGORIZE_BATCH_SQL = (SQL_DIR / "categorization" / "categorize_batch.sql").read_text(encoding="utf-8")
_CLEAR_TEMP_AFSCHRIFT2_SQL = (SQL_DIR / "categorization" / "clear_temp_afschrift2.sql").read_text(encoding="utf-8")


@dataclass
class CategorizationResult:
    rekening: str
    row_count: int
    resolved: int    # processed = 1
    unresolved: int  # processed = 0
    ambiguous: int   # processed = 2


def categorize_pending(rekening_text: str) -> Optional[CategorizationResult]:
    """Categorize one account's entire current temp_afschrift2 backlog in
    one atomic run. Returns None if there's nothing pending for that
    account."""
    conn = get_connection()
    try:
        return _categorize_account(conn, rekening_text)
    finally:
        conn.close()


def _categorize_account(conn: sqlite3.Connection, rekening_text: str) -> Optional[CategorizationResult]:
    rekening = conn.execute(_FIND_REKENING_SQL, {"name": rekening_text}).fetchone()
    if rekening is None:
        # Shouldn't happen in practice: rows only ever reach temp_afschrift2
        # for accounts already validated (registered + linked) at upload time.
        log.error("Categorization skipped for %s: account not found", rekening_text)
        return None

    params = {
        "rekening_text": rekening_text,
        "rekening_id": rekening["ID"],
        "user_id": rekening["user_ID"],
    }

    try:
        returned = conn.execute(_CATEGORIZE_BATCH_SQL, params).fetchall()
        row_count = len(returned)
        if row_count == 0:
            conn.rollback()
            return None

        counts = {0: 0, 1: 0, 2: 0}
        for row in returned:
            counts[row["processed"]] += 1

        conn.execute(_CLEAR_TEMP_AFSCHRIFT2_SQL, params)
        conn.commit()

        result = CategorizationResult(
            rekening_text, row_count,
            resolved=counts[1], unresolved=counts[0], ambiguous=counts[2],
        )
        log.info(
            "Categorized %s: %d rows (%d resolved, %d unresolved, %d ambiguous)",
            rekening_text, row_count, result.resolved, result.unresolved, result.ambiguous,
        )
        audit.info(
            "Categorization for %s: %d resolved, %d unresolved, %d ambiguous (%d rows total)",
            rekening_text, result.resolved, result.unresolved, result.ambiguous, row_count,
        )
        return result

    except Exception:
        conn.rollback()
        log.exception("Categorization failed unexpectedly for %s", rekening_text)
        raise
