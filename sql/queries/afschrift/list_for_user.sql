-- Every individual afschrift row (not aggregated) for a user's own
-- Rekeningen within a date range — feeds the dashboard's "Per categorie"
-- table, where each category can be expanded to show exactly which
-- statements its totals were summed from
-- (app/routes/dashboard.py::home). Same user/date-range scoping as
-- monthly_totals_for_user.sql, kept as its own query since that one is
-- already GROUP BY'd down to month/rekening/category sums and can't be
-- un-aggregated back into individual rows without changing its shape
-- (and therefore the headline totals'/linegraph's behavior).
--
-- :start/:end are the same inclusive ISO-date calendar-month bounds as
-- monthly_totals_for_user.sql.
--
-- Params: :user_id, :start, :end

SELECT
    a.ID,
    a.Datum,
    a.Naam,
    a.Rekening_ID AS rekening_id,
    r.name AS rekening_name,
    a.Tegenrekening,
    a.Af_bij,
    a.Bedrag_eur,
    a.Mededeling,
    a.Afschrift_cat_ID AS cat_id,
    COALESCE(c.Name, 'Zonder categorie') AS category,
    a.Afschrift_subcat_ID AS subcat_id,
    COALESCE(sc.Name, 'Zonder subcategorie') AS subcategorie
FROM afschrift a
JOIN Rekening r ON r.ID = a.Rekening_ID
LEFT JOIN afschrift_categorien c ON c.ID = a.Afschrift_cat_ID
LEFT JOIN afschrift_subcategorien sc ON sc.ID = a.Afschrift_subcat_ID
WHERE r.user_ID = :user_id
  AND a.Datum BETWEEN :start AND :end
ORDER BY a.Datum DESC, a.ID DESC;
