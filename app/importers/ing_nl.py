"""ING NL CSV export importer.

Matches ING's "Alle transacties" export: semicolon-delimited,
double-quoted fields, comma as decimal separator (dot as thousands
separator), dates as an 8-digit "YYYYMMDD" string. Header:

"Datum";"Naam / Omschrijving";"Rekening";"Tegenrekening";"Code";"Af Bij";
"Bedrag (EUR)";"Mutatiesoort";"Mededelingen";"Saldo na mutatie";"Tag"

ING's own row order is newest-first — the top data row (right after the
header) is the most recent transaction, the bottom row the oldest. That's
the reverse of what BaseImporter.parse() must return (chronological
ascending, see app/importers/base.py), so parse() reverses the rows
before returning them.
"""
import csv
import io

from app.importers.base import BaseImporter

_COLUMN_MAP = {
    "Datum": "Datum",
    "Naam / Omschrijving": "Naam",
    "Rekening": "Rekening",
    "Tegenrekening": "Tegenrekening",
    "Code": "Code",
    "Af Bij": "Af_bij",
    "Bedrag (EUR)": "Bedrag_eur",
    "Mutatiesoort": "Mutatiesoort",
    "Mededelingen": "Mededeling",
    "Saldo na mutatie": "Saldo_na_mutatie",
    "Tag": "Tag",
}

# Columns holding a European-formatted amount ("1.234,56") that needs
# converting to a plain float.
_AMOUNT_COLUMNS = {"Bedrag_eur", "Saldo_na_mutatie"}

# Optional columns where an empty string means "not provided" — stored as
# NULL rather than "", matching the schema (these columns allow NULL).
_OPTIONAL_COLUMNS = {"Tegenrekening", "Mededeling", "Tag"}


def _decode(file_bytes: bytes) -> str:
    """ING exports are typically UTF-8 (optionally with a BOM) or Windows
    codepage 1252. Try both rather than assume, so accented characters in
    Naam/Mededelingen don't get mangled."""
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return file_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    return file_bytes.decode("utf-8", errors="replace")


def _parse_amount(raw: str) -> float:
    """European-format amount ("1.234,56" or "4,00") -> float."""
    return float(raw.replace(".", "").replace(",", "."))


class IngNlImporter(BaseImporter):
    format_id = "ing_nl"
    display_name = "ING NL (CSV export)"

    def parse(self, file_bytes: bytes) -> list[dict]:
        text = _decode(file_bytes)
        reader = csv.DictReader(io.StringIO(text), delimiter=";", quotechar='"')

        missing = set(_COLUMN_MAP) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(
                "Dit bestand lijkt geen ING NL-export te zijn — ontbrekende kolommen: "
                f"{sorted(missing)}"
            )

        rows = []
        for line_no, raw_row in enumerate(reader, start=2):  # header is line 1
            try:
                row = {
                    dest: raw_row[source]
                    for source, dest in _COLUMN_MAP.items()
                }
                for col in _AMOUNT_COLUMNS:
                    row[col] = _parse_amount(row[col])
                for col in _OPTIONAL_COLUMNS:
                    if row[col] == "":
                        row[col] = None
            except (KeyError, ValueError) as exc:
                raise ValueError(f"Kon regel {line_no} niet verwerken: {exc}") from exc
            rows.append(row)
        # ING lists newest-first; flip to chronological ascending (oldest
        # first) as required by BaseImporter.parse()'s contract.
        rows.reverse()
        return rows
