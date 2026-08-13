-- OPTIONAL starter data — NOT run automatically by app/db.py::init_db.
--
-- This is one person's example of afschrift_cat_keywords: substrings of a
-- transaction's Naam/Mededeling that auto-assign a category during
-- enrichment (e.g. "Esso" -> Auto). These are inherently personal — your
-- supermarket, gym, or streaming services won't match someone else's list.
--
-- Kept here as a reference/starting point for a new installation. Load it
-- manually if it's a useful starting point (e.g. `sqlite3 data/boekhouding.db
-- < sql/optional/example_keywords.sql`), edit it to match your own spending,
-- or skip it entirely and build your own list from scratch via the templates
-- in sql/queries/reference_data/.
--
-- Depends on the category IDs inserted by sql/seed_data.sql (1=Auto, 2=OV,
-- 3=Abonnementen, 6=Levensmiddelen, 8=Hobbies, 9=Kleding, 13=Uitjes/uit eten).

insert or ignore into afschrift_cat_keywords (keyword, cat_ID)
values ("Tango", 1),("Esso", 1), ("Shell", 1), ("NS", 2), ("Lebara", 3), ("Netflix", 3),
("SSHN", 4), ("ALDI", 6), ("Lidl", 6), ("ALBERT HEIJN",6), ("Jumbo", 6),("AH", 6),
("Het Spelhuis", 8), ("The sting", 9),("Scapino", 9), ("MCDonalds", 13);
