"""Raw-upload pipeline: parse a bank file, insert it into temp_afschrift2,
gate it per account with the balance-chain + dedup checks in sql/upload/,
and commit/rollback atomically. See docs/ARCHITECTURE.md.

The account (Rekening) in the file must already be registered and linked
to the uploading user (see the Accounts screen) — unlike the categorization
side of the pipeline, an unknown or not-yours account is rejected here
outright, not held for later linking.

A single uploaded file can in principle reference more than one account
(ING NL exports normally cover just one). Each account's batch is its own
independent transaction — one account failing its checks does not affect
another account's rows in the same file.

All SQL lives under sql/ as tracked files (see sql/README.md) — this
module only reads and executes them, it never assembles SQL strings.
"""
import sqlite3
from dataclasses import dataclass
from typing import Optional

from app.config import SQL_DIR
from app.db import get_connection
from app.importers.registry import get_importer
from app.logging_config import get_app_logger, get_audit_logger

log = get_app_logger()
audit = get_audit_logger()

_FIND_REKENING_SQL = (SQL_DIR / "queries" / "rekeningen" / "find_by_name.sql").read_text(encoding="utf-8")
_INSERT_BATCH_SQL = (SQL_DIR / "upload" / "insert_batch.sql").read_text(encoding="utf-8")
_CHECK_BALANCE_CHAIN_SQL = (SQL_DIR / "upload" / "check_balance_chain.sql").read_text(encoding="utf-8")
_CHECK_DEDUP_SQL = (SQL_DIR / "upload" / "check_dedup.sql").read_text(encoding="utf-8")


@dataclass
class AccountUploadResult:
    rekening: str
    accepted: bool
    row_count: int
    reason: Optional[str] = None


def process_upload(file_bytes: bytes, format_id: str, user_id: int) -> list[AccountUploadResult]:
    """Parse the uploaded file and attempt to land each account's rows in
    temp_afschrift2, independently, for the given (logged-in) user."""
    importer = get_importer(format_id)
    rows = importer.parse(file_bytes)

    conn = get_connection()
    try:
        return [
            _process_account_batch(conn, rekening_text, account_rows, user_id)
            for rekening_text, account_rows in _group_by_rekening(rows).items()
        ]
    finally:
        conn.close()


def _group_by_rekening(rows: list[dict]) -> dict:
    groups: dict = {}
    for row in rows:
        groups.setdefault(row["Rekening"], []).append(row)
    return groups


def _process_account_batch(
    conn: sqlite3.Connection, rekening_text: str, account_rows: list[dict], user_id: int
) -> AccountUploadResult:
    row_count = len(account_rows)
    rekening = conn.execute(_FIND_REKENING_SQL, {"name": rekening_text}).fetchone()

    if rekening is None:
        reason = (
            f"Rekening '{rekening_text}' is nog niet geregistreerd. "
            "Koppel deze op de Rekeningen-pagina voordat je hiervoor een afschrift uploadt."
        )
        log.warning("Upload rejected for %s: unregistered account", rekening_text)
        audit.info("Upload REJECTED for %s: unregistered account (%d rows attempted)", rekening_text, row_count)
        return AccountUploadResult(rekening_text, accepted=False, row_count=row_count, reason=reason)

    if rekening["user_ID"] != user_id:
        reason = f"Rekening '{rekening_text}' is niet aan jouw gebruiker gekoppeld."
        log.warning("Upload rejected for %s: belongs to a different user", rekening_text)
        audit.info("Upload REJECTED for %s: belongs to a different user (%d rows attempted)", rekening_text, row_count)
        return AccountUploadResult(rekening_text, accepted=False, row_count=row_count, reason=reason)

    rekening_id = rekening["ID"]
    params = {"rekening_text": rekening_text, "rekening_id": rekening_id}

    try:
        conn.executemany(_INSERT_BATCH_SQL, account_rows)

        chain_breaks = conn.execute(_CHECK_BALANCE_CHAIN_SQL, params).fetchall()
        if chain_breaks:
            conn.rollback()
            first = chain_breaks[0]
            reason = (
                f"Saldoketen doorbroken bij {first['Datum']} ({first['Naam']}): "
                f"het verwachte saldo komt niet overeen met Saldo_na_mutatie={first['Saldo_na_mutatie']}. "
                "Dit bestand sluit mogelijk niet direct aan op het laatst bekende saldo, "
                "of er ontbreekt een rij / staat een rij niet in de juiste volgorde."
            )
            log.warning("Upload rejected for %s: %s", rekening_text, reason)
            audit.info(
                "Upload REJECTED for %s: balance chain broken (%d rows attempted)",
                rekening_text, row_count,
            )
            return AccountUploadResult(rekening_text, accepted=False, row_count=row_count, reason=reason)

        dupes = conn.execute(_CHECK_DEDUP_SQL, params).fetchall()
        if dupes:
            conn.rollback()
            reason = (
                f"{len(dupes)} dubbele rij(en) gevonden (bijv. {dupes[0]['Datum']}, "
                f"{dupes[0]['Naam']}) — dit bestand is mogelijk al eerder geïmporteerd."
            )
            log.warning("Upload rejected for %s: %s", rekening_text, reason)
            audit.info(
                "Upload REJECTED for %s: %d duplicate rows (%d rows attempted)",
                rekening_text, len(dupes), row_count,
            )
            return AccountUploadResult(rekening_text, accepted=False, row_count=row_count, reason=reason)

        conn.commit()
        log.info("Upload accepted for %s: %d rows", rekening_text, row_count)
        audit.info("Upload ACCEPTED for %s: %d rows inserted into temp_afschrift2", rekening_text, row_count)
        return AccountUploadResult(rekening_text, accepted=True, row_count=row_count)

    except Exception:
        conn.rollback()
        log.exception("Upload failed unexpectedly for %s", rekening_text)
        raise
