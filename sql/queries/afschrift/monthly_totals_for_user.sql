-- Dashboard: for one user's afschrift rows within a date range, sums
-- income (Bij) and expenditure (Af) per month, per Rekening, per
-- category. One query serves the headline totals, the per-category
-- table, AND the linegraph's monthly series — app/routes/dashboard.py
-- filters/sums this fixed, small result set (a handful of rekeningen x
-- categorieen x months) in Python according to which Rekeningen/
-- categorieen the user has checked, rather than a dynamic SQL IN-list
-- (this project keeps all SQL as static tracked files — see
-- sql/queries/README.md). See app/dashboard_chart.py for that reshaping.
--
-- Reads only the permanent ledger (afschrift), never temp_afschrift —
-- pending/unresolved rows haven't been migrated yet (sql/migration/) and
-- don't count towards real totals.
--
-- :start/:end are inclusive ISO dates ('YYYY-MM-DD') spanning full
-- calendar months (the 1st of the start month through the last day of
-- the end month) — afschrift.Datum is stored in that format so a plain
-- text BETWEEN sorts/filters correctly, and strftime('%Y-%m', ...) on an
-- ISO date needs no other conversion.
--
-- A row with no category (Afschrift_cat_ID NULL) gets cat_id NULL and
-- category 'Zonder categorie' — the app treats that as its own
-- selectable pseudo-category (id "none") so uncategorized spending isn't
-- silently included or excluded from the totals.
--
-- Params: :user_id, :start, :end

SELECT
    strftime('%Y-%m', a.Datum) AS month,
    a.Rekening_ID AS rekening_id,
    r.name AS rekening_name,
    c.ID AS cat_id,
    COALESCE(c.Name, 'Zonder categorie') AS category,
    COALESCE(SUM(CASE WHEN a.Af_bij = 'Bij' THEN a.Bedrag_eur ELSE 0 END), 0) AS totaal_bij,
    COALESCE(SUM(CASE WHEN a.Af_bij = 'Af' THEN a.Bedrag_eur ELSE 0 END), 0) AS totaal_af
FROM afschrift a
JOIN Rekening r ON r.ID = a.Rekening_ID
LEFT JOIN afschrift_categorien c ON c.ID = a.Afschrift_cat_ID
WHERE r.user_ID = :user_id
  AND a.Datum BETWEEN :start AND :end
GROUP BY month, a.Rekening_ID, c.ID
ORDER BY month;
