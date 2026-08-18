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
_RECATEGORIZE_SQL = (SQL_DIR / "categorization" / "recategorize_temp_afschrift.sql").read_text(encoding="utf-8")


@dataclass
class CategorizationResult:
    rekening: str
    row_count: int
    resolved: int    # processed = 1
    unresolved: int  # processed = 0
    ambiguous: int   # processed = 2


@dataclass
class RecategorizeResult:
    # All of these count only rows whose outcome actually changed — a row
    # left exactly as it was (including an already-resolved row that's
    # still uniquely resolved) isn't included. "ambiguous" in particular
    # means *newly* ambiguous: a rule now conflicts with a row that was
    # previously resolved to exactly one category (or was unresolved).
    row_count: int   # rows whose processed/category actually changed
    resolved: int    # of those, now processed = 1
    unresolved: int  # of those, now processed = 0
    ambiguous: int   # of those, now processed = 2


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


def recategorize_pending(user_id: int) -> Optional[RecategorizeResult]:
    """Re-run rule-based categorization against ALL of this user's current
    temp_afschrift rows, across all of their accounts at once — including
    already-resolved ones. Meant to be triggered on demand — e.g. after
    the user adds/edits a rule — so:

    - previously unresolved/ambiguous rows get a fresh chance, and
    - previously-resolved rows get re-checked too, in case a newly added
      rule now ALSO matches them, which is surfaced as a new conflict
      (processed = 2) rather than silently left as the earlier answer.

    Never demotes an already-resolved row back to unresolved just because
    zero rules currently match it (the normal case for anything picked by
    hand on /review — there's no flag distinguishing a manual pick from
    an automatic one) and never silently swaps its category for a
    different single match — a resolved row is only ever *promoted* to
    ambiguous, never otherwise changed. Rows already migrated to
    afschrift aren't touched (they're not in this table anymore). Returns
    None if nothing changed."""
    conn = get_connection()
    try:
        return _recategorize(conn, user_id)
    finally:
        conn.close()


def _recategorize(conn: sqlite3.Connection, user_id: int) -> Optional[RecategorizeResult]:
    try:
        returned = conn.execute(_RECATEGORIZE_SQL, {"user_id": user_id}).fetchall()
        row_count = len(returned)
        if row_count == 0:
            conn.rollback()
            return None

        counts = {0: 0, 1: 0, 2: 0}
        for row in returned:
            counts[row["processed"]] += 1

        conn.commit()
        result = RecategorizeResult(
            row_count, resolved=counts[1], unresolved=counts[0], ambiguous=counts[2],
        )
        log.info(
            "Recategorized user %d: %d row(s) changed (%d resolved, %d unresolved, %d ambiguous)",
            user_id, row_count, result.resolved, result.unresolved, result.ambiguous,
        )
        audit.info(
            "Recategorization for user %d: %d row(s) changed — %d resolved, %d unresolved, %d ambiguous",
            user_id, row_count, result.resolved, result.unresolved, result.ambiguous,
        )
        return result

    except Exception:
        conn.rollback()
        log.exception("Recategorization failed unexpectedly for user %d", user_id)
        raise
