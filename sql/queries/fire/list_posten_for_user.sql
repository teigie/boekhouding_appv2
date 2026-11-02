-- Every pensioenplanner-post for one user (actief or not — the caller
-- filters/displays the actief flag itself rather than this query hiding
-- inactive posts, see app/fire_projection.py). Category/subcategory/
-- persoon names resolved here so the caller never needs a second lookup.
-- Params: :user_id

SELECT
    p.ID,
    p.omschrijving,
    p.Afschrift_cat_ID AS afschrift_cat_id,
    c.Name AS category,
    p.Afschrift_subcat_ID AS afschrift_subcat_id,
    sc.Name AS subcategorie,
    p.persoon_ID AS persoon_id,
    per.naam AS persoon_naam,
    p.type,
    p.jaarbedrag,
    p.groei_pct,
    p.start_jaar,
    p.stop_jaar,
    p.eenmalig,
    p.actief
FROM fire_posten p
LEFT JOIN afschrift_categorien c ON c.ID = p.Afschrift_cat_ID
LEFT JOIN afschrift_subcategorien sc ON sc.ID = p.Afschrift_subcat_ID
LEFT JOIN fire_personen per ON per.ID = p.persoon_ID
WHERE p.user_ID = :user_id
ORDER BY p.type, c.Name, sc.Name, p.omschrijving;
