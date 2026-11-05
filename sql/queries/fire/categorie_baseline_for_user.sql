-- Pensioenplanner: net total per (categorie, subcategorie) combination
-- over a chosen history window — the baseline a fire_post's jaarbedrag is
-- suggested from (netto_totaal / venster_maanden * 12, computed in Python
-- from :start/:end — see app/routes/pensioenplanner.py's
-- _baseline_venster/_annualized_bedrag). The denominator is the window's
-- total elapsed calendar months, NOT how many of those months happen to
-- contain a transaction for this one category — a cost that recurs less
-- than monthly (e.g. a twice-a-year road tax payment) would otherwise get
-- divided by its own occurrence count and badly overstated.
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
--
-- Only counts Rekeningen the user has included via
-- fire_rekening_selectie (sql/queries/fire/sync_rekening_selectie.sql) —
-- a static join on that table, not a dynamic IN-list (see
-- app/dashboard_chart.py's module docstring for why the app never builds
-- one of those), so a household with several linked accounts can exclude
-- one from the baseline (e.g. a private account kept out of a shared
-- projection) without any per-request filtering in Python.
-- Params: :user_id, :start, :end

SELECT
    a.Afschrift_cat_ID AS cat_id,
    c.Name AS category,
    c.Type AS cat_type,
    a.Afschrift_subcat_ID AS subcat_id,
    sc.Name AS subcategorie,
    COALESCE(SUM(CASE WHEN a.Af_bij = 'Bij' THEN a.Bedrag_eur ELSE -a.Bedrag_eur END), 0) AS netto_totaal
FROM afschrift a
JOIN Rekening r ON r.ID = a.Rekening_ID
JOIN fire_rekening_selectie frs ON frs.Rekening_ID = r.ID AND frs.user_ID = r.user_ID
JOIN afschrift_categorien c ON c.ID = a.Afschrift_cat_ID
LEFT JOIN afschrift_subcategorien sc ON sc.ID = a.Afschrift_subcat_ID
WHERE r.user_ID = :user_id
  AND frs.actief = 1
  AND a.Datum BETWEEN :start AND :end
GROUP BY a.Afschrift_cat_ID, a.Afschrift_subcat_ID
ORDER BY c.Name, sc.Name;
