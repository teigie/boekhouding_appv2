-- Mandatory reference data, run once against a fresh database, right after
-- schema.sql (see app/db.py::init_db). This covers structural data every
-- installation needs: the bank's mutation-type vocabulary. It does NOT
-- include actual categories or their keywords (e.g. "Esso" -> Auto) —
-- those are per-user, built via /categories (suggestion chips there come
-- from the fixed app/category_suggestions.py list, not a seeded table).
--
-- Uses INSERT OR IGNORE so this file stays safe to re-run or extend later.

insert or ignore into mutatiesoort (name)
values ("iDEAL | Wero"),("Betaalautomaat"),("Online bankieren"),("Overschrijving"),
("Incasso"),("Verzamelbetaling"),("Diversen"),("Geldautomaat");

insert or ignore into mutatiesoort_mapping (mutatiesoort_ID, name)
values (1, "iDEAL | Wero"),(1, "iDEAL"), (1, "Wero"), (2, "Betaalautomaat"),
(3, "Online bankieren"),(4, "Overschrijving"),(5, "Incasso"),(6, "Verzamelbetaling"),
(7, "Diversen"),(8, "Geldautomaat");
