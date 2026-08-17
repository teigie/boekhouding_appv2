-- Mandatory reference data, run once against a fresh database, right after
-- schema.sql (see app/db.py::init_db). This covers structural data every
-- installation needs: category suggestions and the bank's mutation-type
-- vocabulary. It does NOT include actual categories or their keywords
-- (e.g. "Esso" -> Auto) — those are per-user, built via /categories.
--
-- Uses INSERT OR IGNORE so this file stays safe to re-run or extend later.

-- Not real categories — a fixed, global list of names offered as
-- one-click suggestions on /categories. Every new user starts with an
-- empty afschrift_categorien; this just saves retyping the common ones.
insert or ignore into afschrift_categorie_suggesties (Name)
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
