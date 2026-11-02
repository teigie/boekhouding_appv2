-- Updates the editable fields of one pensioenplanner-post — never its
-- category/subcategory/type linkage, which is fixed at creation (see
-- add_post.sql); "dupliceer post" is how you get an independently
-- editable copy under a different category pairing or split amount.
-- Params: :id, :user_id, :omschrijving, :persoon_id, :jaarbedrag,
--         :groei_pct, :start_jaar, :stop_jaar, :eenmalig, :actief

UPDATE fire_posten SET
    omschrijving = :omschrijving,
    persoon_ID = :persoon_id,
    jaarbedrag = :jaarbedrag,
    groei_pct = :groei_pct,
    start_jaar = :start_jaar,
    stop_jaar = :stop_jaar,
    eenmalig = :eenmalig,
    actief = :actief,
    updated_at = datetime('now')
WHERE ID = :id AND user_ID = :user_id;
