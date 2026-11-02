-- Pensioenplanner: annualizable net total per (categorie, subcategorie)
-- combination over a chosen history window — the baseline a new
-- fire_post's jaarbedrag is suggested from (netto_totaal / aantal_maanden
-- * 12, computed in Python — see app/routes/pensioenplanner.py).
--
-- Net per combination (Bij minus Af), same principle as
-- sql/queries/afschrift/monthly_totals_for_user.sql — NEVER assume a
-- category's Type tells you the direction of every row in it. A category
-- can legitimately contain rows in both directions (e.g. an expense paid
-- on someone else's behalf, booked under the same category as the
-- reimbursement that later comes back in, so the two net to zero) —
-- collapsing that to a one-directional SUM would silently overstate the
-- baseline.
--
-- Only rows with a real category count (Afschrift_cat_ID IS NOT NULL) —
-- "Zonder categorie" isn't a projectable line.
-- :start/:end are inclusive ISO dates, same convention as
-- monthly_totals_for_user.sql.
-- Params: :user_id, :start, :end

SELECT
    a.Afschrift_cat_ID AS cat_id,
    c.Name AS category,
    c.Type AS cat_type,
    a.Afschrift_subcat_ID AS subcat_id,
    sc.Name AS subcategorie,
    COALESCE(SUM(CASE WHEN a.Af_bij = 'Bij' THEN a.Bedrag_eur ELSE -a.Bedrag_eur END), 0) AS netto_totaal,
    COUNT(DISTINCT strftime('%Y-%m', a.Datum)) AS aantal_maanden
FROM afschrift a
JOIN Rekening r ON r.ID = a.Rekening_ID
JOIN afschrift_categorien c ON c.ID = a.Afschrift_cat_ID
LEFT JOIN afschrift_subcategorien sc ON sc.ID = a.Afschrift_subcat_ID
WHERE r.user_ID = :user_id
  AND a.Datum BETWEEN :start AND :end
GROUP BY a.Afschrift_cat_ID, a.Afschrift_subcat_ID
ORDER BY c.Name, sc.Name;
