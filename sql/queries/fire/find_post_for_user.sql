-- Ownership check before acting on a post from a URL/form, same pattern
-- as sql/queries/categorieen/find_by_id_for_user.sql.
-- Params: :id, :user_id

SELECT
    ID,
    omschrijving,
    Afschrift_cat_ID AS afschrift_cat_id,
    Afschrift_subcat_ID AS afschrift_subcat_id,
    persoon_ID AS persoon_id,
    type,
    jaarbedrag,
    groei_pct,
    start_jaar,
    stop_jaar,
    eenmalig,
    actief
FROM fire_posten
WHERE ID = :id AND user_ID = :user_id;
