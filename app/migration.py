"""Fase 4: migrates one account's fully-resolved temp_afschrift backlog
into the permanent afschrift ledger, in one atomic transaction. See
docs/ARCHITECTURE.md and sql/migration/README.md.

All-or-nothing per account: refuses to run (raises NotFullyResolvedError,
nothing touched) unless *every* temp_afschrift row for that Rekening_ID —
including rows left over from an earlier upload, not just the most recent
one — has processed = 1. This follows directly from afschrift.Saldo_na_mutatie
being a running balance: skipping an unresolved row and inserting it later,
out of order, would corrupt every balance after it. Other accounts are
unaffected by one account still having unresolved rows.

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

_COUNT_UNRESOLVED_SQL = (SQL_DIR / "migration" / "count_unresolved.sql").read_text(encoding="utf-8")
_INSERT_INTO_AFSCHRIFT_SQL = (SQL_DIR / "migration" / "insert_into_afschrift.sql").read_text(encoding="utf-8")
_DELETE_FROM_TEMP_AFSCHRIFT_SQL = (SQL_DIR / "migration" / "delete_from_temp_afschrift.sql").read_text(encoding="utf-8")


class NotFullyResolvedError(Exception):
    """Raised when migrate_account is asked to migrate an account that
    still has unresolved (0) or ambiguous (2) rows. Nothing is changed."""


@dataclass
class MigrationResult:
    rekening_id: int
    row_count: int


def migrate_account(rekening_id: int, user_id: int) -> Optional[MigrationResult]:
    """Migrate one account's entire resolved temp_afschrift backlog into
    afschrift. Returns None if there's nothing pending for that account.
    Raises NotFullyResolvedError (without changing anything) if any row
    for this account isn't processed = 1 yet. Both the guard and the
    insert/delete are additionally scoped to :user_id, so a stale/guessed
    rekening_id can never touch another user's rows — same defense in
    depth as sql/queries/temp_afschrift/set_category.sql."""
    conn = get_connection()
    try:
        return _migrate(conn, rekening_id, user_id)
    finally:
        conn.close()


def _migrate(conn: sqlite3.Connection, rekening_id: int, user_id: int) -> Optional[MigrationResult]:
    params = {"rekening_id": rekening_id, "user_id": user_id}

    unresolved = conn.execute(_COUNT_UNRESOLVED_SQL, params).fetchone()["unresolved"]
    if unresolved:
        raise NotFullyResolvedError(
            f"Rekening {rekening_id} has {unresolved} unresolved/ambiguous row(s) — migration refused"
        )

    try:
        cursor = conn.execute(_INSERT_INTO_AFSCHRIFT_SQL, params)
        row_count = cursor.rowcount
        if row_count <= 0:
            conn.rollback()
            return None

        conn.execute(_DELETE_FROM_TEMP_AFSCHRIFT_SQL, params)
        conn.commit()

        log.info("Migrated %d row(s) for Rekening %s into afschrift", row_count, rekening_id)
        audit.info(
            "Migration: %d row(s) moved from temp_afschrift into afschrift for Rekening %s (user %s)",
            row_count, rekening_id, user_id,
        )
        return MigrationResult(rekening_id, row_count)

    except Exception:
        conn.rollback()
        log.exception("Migration failed unexpectedly for Rekening %s", rekening_id)
        raise
