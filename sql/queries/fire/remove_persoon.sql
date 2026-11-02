-- Scoped to :user_id so a persoon can only ever be removed by its own
-- owner. Any fire_posten.persoon_ID referencing it is set NULL, not
-- cascaded (see sql/schema.sql) — the post itself survives, just loses
-- the label.
-- Params: :id, :user_id

DELETE FROM fire_personen WHERE ID = :id AND user_ID = :user_id;
