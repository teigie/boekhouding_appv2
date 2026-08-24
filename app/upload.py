"""Raw-upload pipeline: parse a bank file, insert it into temp_afschrift2,
gate it per account, and commit/rollback atomically. See docs/ARCHITECTURE.md.

Two kinds of gate, both all-or-nothing per account:

- Pre-insert FK checks — Rekening and Mutatiesoort must both already
  resolve (Rekening to an account registered *and* linked to the uploading
  user; Mutatiesoort against the structural mutatiesoort_mapping
  reference data). Nothing is inserted if either fails — these aren't
  temp_afschrift2 problems, they're "this batch doesn't belong here /
  isn't recognized yet" problems.
- Post-insert continuity checks (date-order + balance-chain + batch-
  totals + dedup, sql/upload/) — run after inserting the batch, inside
  the same transaction; roll back the insert if any fails. These
  inherently need the new rows already present, since they check the
  batch against the account's existing history.

Once a batch clears both and commits, that account's full temp_afschrift2
backlog is immediately categorized (app/categorization.py) so it lands
fully resolved-or-flagged in temp_afschrift, ready for manual review.
Categorization can't fail under normal operation here — Mutatiesoort/
Rekening are already guaranteed to resolve by the pre-insert checks above,
and every row otherwise gets `processed` 0, 1, or 2.

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

from app.categorization import CategorizationResult, categorize_pending
from app.config import SQL_DIR
from app.db import get_connection
from app.formatting import format_amount_nl
from app.importers.registry import get_importer
from app.logging_config import get_app_logger, get_audit_logger

log = get_app_logger()
audit = get_audit_logger()

_FIND_REKENING_SQL = (SQL_DIR / "queries" / "rekeningen" / "find_by_name.sql").read_text(encoding="utf-8")
_FIND_MUTATIESOORT_SQL = (SQL_DIR / "queries" / "mutatiesoorten" / "find_by_name.sql").read_text(encoding="utf-8")
_INSERT_BATCH_SQL = (SQL_DIR / "upload" / "insert_batch.sql").read_text(encoding="utf-8")
_CHECK_DATE_ORDER_SQL = (SQL_DIR / "upload" / "check_date_order.sql").read_text(encoding="utf-8")
_CHECK_BALANCE_CHAIN_SQL = (SQL_DIR / "upload" / "check_balance_chain.sql").read_text(encoding="utf-8")
_CHECK_BATCH_TOTALS_SQL = (SQL_DIR / "upload" / "check_batch_totals.sql").read_text(encoding="utf-8")
_CHECK_DEDUP_SQL = (SQL_DIR / "upload" / "check_dedup.sql").read_text(encoding="utf-8")


@dataclass
class AccountUploadResult:
    rekening: str
    accepted: bool
    row_count: int
    reason: Optional[str] = None
    categorization: Optional[CategorizationResult] = None


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

    unmapped_mutatiesoorten = sorted({
        row["Mutatiesoort"] for row in account_rows
        if conn.execute(_FIND_MUTATIESOORT_SQL, {"name": row["Mutatiesoort"]}).fetchone() is None
    })
    if unmapped_mutatiesoorten:
        reason = (
            f"Onbekende mutatiesoort(en): {', '.join(unmapped_mutatiesoorten)}. "
            "Voeg deze toe aan de mutatiesoort-mapping voordat je dit bestand opnieuw uploadt."
        )
        log.warning("Upload rejected for %s: %s", rekening_text, reason)
        audit.info(
            "Upload REJECTED for %s: unmapped mutatiesoort(en) %s (%d rows attempted)",
            rekening_text, unmapped_mutatiesoorten, row_count,
        )
        return AccountUploadResult(rekening_text, accepted=False, row_count=row_count, reason=reason)

    rekening_id = rekening["ID"]
    params = {"rekening_text": rekening_text, "rekening_id": rekening_id}

    try:
        conn.executemany(_INSERT_BATCH_SQL, account_rows)

        date_breaks = conn.execute(_CHECK_DATE_ORDER_SQL, params).fetchall()
        if date_breaks:
            conn.rollback()
            first = date_breaks[0]
            reason = (
                f"Datums lopen niet consistent op: {first['Naam']} staat op {first['Datum']}, "
                f"vóór {first['prev_datum']} van de vorige rij. Dit bestand staat mogelijk niet in de "
                "juiste volgorde, of er ontbreekt een rij."
            )
            log.warning("Upload rejected for %s: %s", rekening_text, reason)
            audit.info(
                "Upload REJECTED for %s: date order broken (%d rows attempted)",
                rekening_text, row_count,
            )
            return AccountUploadResult(rekening_text, accepted=False, row_count=row_count, reason=reason)

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

        totals_mismatch = conn.execute(_CHECK_BATCH_TOTALS_SQL, params).fetchone()
        if totals_mismatch is not None:
            conn.rollback()
            reason = (
                f"Eindsaldo (€ {format_amount_nl(totals_mismatch['end_balance'])}) min beginsaldo "
                f"(€ {format_amount_nl(totals_mismatch['initial_balance'])}) = "
                f"€ {format_amount_nl(totals_mismatch['actual_diff'])}, maar de som van bij/af in dit "
                f"bestand komt uit op € {format_amount_nl(totals_mismatch['expected_diff'])}. "
                "Dit bestand klopt niet in totaal — mogelijk ontbreekt een rij of staat er een "
                "verkeerd bedrag in."
            )
            log.warning("Upload rejected for %s: %s", rekening_text, reason)
            audit.info(
                "Upload REJECTED for %s: batch totals mismatch (actual=%s, expected=%s, %d rows attempted)",
                rekening_text, totals_mismatch["actual_diff"], totals_mismatch["expected_diff"], row_count,
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

        categorization_result = categorize_pending(rekening_text)
        return AccountUploadResult(
            rekening_text, accepted=True, row_count=row_count, categorization=categorization_result
        )

    except Exception:
        conn.rollback()
        log.exception("Upload failed unexpectedly for %s", rekening_text)
        raise
