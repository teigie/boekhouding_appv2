-- Creates or replaces a user's one pensioenplanner-settings row.
-- user_ID is itself the primary key (one row per user, see
-- sql/schema.sql), so a plain upsert on it covers both "first save" and
-- every save after.
-- Params: :user_id, :start_jaar, :eind_jaar, :historie_maanden,
--         :algemeen_groei_pct, :saldo_spaargeld, :rendement_spaargeld_pct,
--         :saldo_beleggingen, :rendement_beleggingen_pct

INSERT INTO fire_instellingen (
    user_ID, start_jaar, eind_jaar, historie_maanden, algemeen_groei_pct,
    saldo_spaargeld, rendement_spaargeld_pct, saldo_beleggingen, rendement_beleggingen_pct,
    updated_at
) VALUES (
    :user_id, :start_jaar, :eind_jaar, :historie_maanden, :algemeen_groei_pct,
    :saldo_spaargeld, :rendement_spaargeld_pct, :saldo_beleggingen, :rendement_beleggingen_pct,
    datetime('now')
)
ON CONFLICT(user_ID) DO UPDATE SET
    start_jaar = excluded.start_jaar,
    eind_jaar = excluded.eind_jaar,
    historie_maanden = excluded.historie_maanden,
    algemeen_groei_pct = excluded.algemeen_groei_pct,
    saldo_spaargeld = excluded.saldo_spaargeld,
    rendement_spaargeld_pct = excluded.rendement_spaargeld_pct,
    saldo_beleggingen = excluded.saldo_beleggingen,
    rendement_beleggingen_pct = excluded.rendement_beleggingen_pct,
    updated_at = excluded.updated_at;
