-- Lists every temp_afschrift row (any `processed` value) across every
-- account belonging to the given user — the /review page's overview.
-- Read-only: this doesn't resolve anything, just surfaces what's there.
--
-- Mutatiesoort_ID is joined against `mutatiesoort` (the canonical
-- vocabulary), not `mutatiesoort_mapping` (which maps raw import text
-- variants to it and isn't 1:1 with a display name). Afschrift_cat_ID is
-- LEFT JOINed since it's NULL whenever `processed` is 0 or 2.
--
-- Params:
--   :user_id

SELECT
    t.ID,
    t.Datum,
    t.Naam,
    r.ID AS Rekening_ID,
    r.name AS Rekening,
    t.Mededeling,
    t.Bedrag_eur,
    t.Af_bij,
    m.Name AS Mutatiesoort,
    c.Name AS Categorie,
    t.processed
FROM temp_afschrift t
JOIN Rekening r ON r.ID = t.Rekening_ID
JOIN mutatiesoort m ON m.ID = t.Mutatiesoort_ID
LEFT JOIN afschrift_categorien c ON c.ID = t.Afschrift_cat_ID
WHERE r.user_ID = :user_id
ORDER BY r.name, t.ID;
