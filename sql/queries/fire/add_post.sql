-- Adds one pensioenplanner-post — used both for a manually-added post
-- (afschrift_cat_id/afschrift_subcat_id NULL) and for an auto-suggested
-- one from sql/queries/fire/categorie_baseline_for_user.sql, and by the
-- "dupliceer post" action (which copies an existing row's values
-- wholesale). See sql/schema.sql::fire_posten for what each column means.
-- Params: :user_id, :omschrijving, :afschrift_cat_id, :afschrift_subcat_id,
--         :persoon_id, :type, :jaarbedrag, :groei_pct, :start_jaar,
--         :stop_jaar, :eenmalig, :actief

INSERT INTO fire_posten (
    user_ID, omschrijving, Afschrift_cat_ID, Afschrift_subcat_ID, persoon_ID,
    type, jaarbedrag, groei_pct, start_jaar, stop_jaar, eenmalig, actief, updated_at
) VALUES (
    :user_id, :omschrijving, :afschrift_cat_id, :afschrift_subcat_id, :persoon_id,
    :type, :jaarbedrag, :groei_pct, :start_jaar, :stop_jaar, :eenmalig, :actief, datetime('now')
);
