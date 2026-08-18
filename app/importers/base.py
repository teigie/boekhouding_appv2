"""Shared interface every bank-specific importer implements.

Adding support for a new bank/export format means adding a new class here,
not changing the upload endpoint or anything downstream — parsing is fully
isolated from the rest of the pipeline.
"""
from abc import ABC, abstractmethod


class BaseImporter(ABC):
    """Turns a raw uploaded file into rows shaped like temp_afschrift2."""

    #: Machine-readable identifier used to select this importer (e.g. in the
    #: upload form's format dropdown).
    format_id: str
    #: Human-readable label shown to the user.
    display_name: str

    @abstractmethod
    def parse(self, file_bytes: bytes) -> list[dict]:
        """Parse raw file bytes into a list of row dicts, in chronological
        order — oldest transaction first, newest last. Downstream logic
        (app/upload.py, sql/upload/check_balance_chain.sql) assumes the
        returned order *is* chronological ascending and uses it as-is to
        decide insertion order, so it is preserved from here on and must
        not be reordered again later (see docs/ARCHITECTURE.md).

        This is chronological order, not necessarily the source file's own
        row order: some export formats (e.g. ING NL) list the newest
        transaction first and the oldest last, so implementations must
        reverse the rows themselves here if the source's native order
        isn't already oldest-first. Getting this wrong doesn't silently
        corrupt data — the balance-chain check downstream will reject the
        whole batch — but it's still this method's job to get right.

        Each dict must have exactly these keys, matching temp_afschrift2's
        columns:
            Datum, Naam, Rekening, Tegenrekening, Code, Af_bij,
            Bedrag_eur, Mutatiesoort, Mededeling, Saldo_na_mutatie, Tag

        Datum stays as the source's raw 8-character "YYYYMMDD" string —
        that's what temp_afschrift2.Datum (varchar(8)) expects. The
        human-readable "YYYY-MM-DD" form belongs to temp_afschrift/
        afschrift (char(10)) and is produced later, during categorization —
        don't reformat it here. Bedrag_eur and Saldo_na_mutatie should be
        Python floats (or Decimal), regardless of the source file's own
        formatting (e.g. European "1.234,56" style).
        """
        raise NotImplementedError
