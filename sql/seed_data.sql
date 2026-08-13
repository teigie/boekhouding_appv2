-- Mandatory reference data, run once against a fresh database, right after
-- schema.sql (see app/db.py::init_db). This covers structural data every
-- installation needs: spending categories and the bank's mutation-type
-- vocabulary. It does NOT include category keywords (e.g. "Esso" -> Auto) —
-- those are personal to whoever uses the app, see sql/optional/.
--
-- Uses INSERT OR IGNORE so this file stays safe to re-run or extend later.

insert or ignore into afschrift_categorien (Name)
values ("Auto"),("OV"),("Abonnementen"),("Wonen"),("Inboedel"),
("Levensmiddelen"),("Zorgkosten"),("Hobbies"),("Kleding"),
("Huisdieren"),("Interne overboeking"),("Vakantie"),("Uitjes/uit eten"),("Overig");

insert or ignore into mutatiesoort (name)
values ("iDEAL | Wero"),("Betaalautomaat"),("Online bankieren"),("Overschrijving"),
("Incasso"),("Verzamelbetaling"),("Diversen"),("Geldautomaat");

insert or ignore into mutatiesoort_mapping (mutatiesoort_ID, name)
values (1, "iDEAL | Wero"),(1, "iDEAL"), (1, "Wero"), (2, "Betaalautomaat"),
(3, "Online bankieren"),(4, "Overschrijving"),(5, "Incasso"),(6, "Verzamelbetaling"),
(7, "Diversen"),(8, "Geldautomaat");
