"""Registry of available bank importers.

Adding support for a new bank/export format: implement a new BaseImporter
subclass (see ing_nl.py for reference) and register an instance here — the
upload form's dropdown and the upload handler both read from this list,
nothing else needs to change.
"""
from app.importers.ing_nl import IngNlImporter

IMPORTERS = {
    importer.format_id: importer
    for importer in [
        IngNlImporter(),
    ]
}


def get_importer(format_id: str):
    try:
        return IMPORTERS[format_id]
    except KeyError:
        raise ValueError(f"Unknown import format: {format_id!r}")
