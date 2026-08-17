-- Dashboard totals: for one user's afschrift rows within a date range,
-- sums income (Bij) and expenditure (Af) per category. Reads only the
-- permanent ledger (afschrift), never temp_afschrift — pending/unresolved
-- rows haven't been migrated yet and don't count towards real totals.
--
-- Afschrift_cat_ID should always be set by the time a row reaches
-- afschrift (migration only accepts processed = 1 rows, which always
-- carry a category — see sql/migration/README.md), but the LEFT JOIN +
-- COALESCE is defensive rather than assumed.
--
-- :start/:end are inclusive ISO dates ('YYYY-MM-DD'); afschrift.Datum is
-- stored in that format so a plain text BETWEEN sorts/filters correctly
-- (see docs/ARCHITECTURE.md's "Datums" table) — no date()/strftime()
-- conversion needed.
--
-- The caller (app/routes/dashboard.py) sums totaal_bij/totaal_af across
-- every returned row to get the overall income/expenditure/difference
-- headline figures — one query serves both the per-category breakdown
-- and the page totals.
--
-- Params: :user_id, :start, :end

SELECT
    c.ID AS cat_id,
    COALESCE(c.Name, 'Zonder categorie') AS category,
    COALESCE(SUM(CASE WHEN a.Af_bij = 'Bij' THEN a.Bedrag_eur ELSE 0 END), 0) AS totaal_bij,
    COALESCE(SUM(CASE WHEN a.Af_bij = 'Af' THEN a.Bedrag_eur ELSE 0 END), 0) AS totaal_af
FROM afschrift a
JOIN Rekening r ON r.ID = a.Rekening_ID
LEFT JOIN afschrift_categorien c ON c.ID = a.Afschrift_cat_ID
WHERE r.user_ID = :user_id
  AND a.Datum BETWEEN :start AND :end
GROUP BY c.ID, category
ORDER BY totaal_af DESC, totaal_bij DESC;
