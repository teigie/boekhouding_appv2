-- Every individual afschrift row for a user's own Rekeningen within a
-- date range, with every foreign key resolved to its human-readable name
-- rather than left as an ID — feeds the dashboard's CSV export
-- (app/routes/dashboard.py::export_csv). Unlike list_for_user.sql (which
-- only carries the columns the "Per categorie" detail view needs to
-- display), this selects every afschrift column, since an exported CSV
-- is meant to stand on its own outside the app, not just supplement a
-- total already shown on screen.
--
-- rekening_id/cat_id are still included alongside their resolved names
-- so the caller can apply the same Rekening/categorie selection filtering
-- (in Python, see sql/queries/README.md) as the rest of the dashboard —
-- an export always matches exactly what's currently selected, never the
-- user's full ledger regardless of filters.
--
-- Same user/date-range scoping as monthly_totals_for_user.sql /
-- list_for_user.sql. Mutatiesoort is joined directly (not via
-- mutatiesoort_mapping, which only maps a bank's raw import label to a
-- Mutatiesoort_ID) since afschrift already stores the resolved ID.
--
-- Params: :user_id, :start, :end

SELECT
    a.Datum,
    a.Naam,
    a.Rekening_ID AS rekening_id,
    r.name AS rekening_name,
    a.Tegenrekening,
    a.Code,
    a.Af_bij,
    a.Bedrag_eur,
    m.Name AS mutatiesoort_name,
    a.Mededeling,
    a.Saldo_na_mutatie,
    a.Tag,
    a.Afschrift_cat_ID AS cat_id,
    COALESCE(c.Name, 'Zonder categorie') AS category,
    a.Afschrift_subcat_ID AS subcat_id,
    COALESCE(sc.Name, 'Zonder subcategorie') AS subcategorie
FROM afschrift a
JOIN Rekening r ON r.ID = a.Rekening_ID
JOIN mutatiesoort m ON m.ID = a.Mutatiesoort_ID
LEFT JOIN afschrift_categorien c ON c.ID = a.Afschrift_cat_ID
LEFT JOIN afschrift_subcategorien sc ON sc.ID = a.Afschrift_subcat_ID
WHERE r.user_ID = :user_id
  AND a.Datum BETWEEN :start AND :end
ORDER BY a.Datum, a.ID;
