-- Delete an entire rule, scoped to its owning user. Cascades its
-- column-conditions and their keywords (ON DELETE CASCADE, see
-- sql/schema.sql). If :id isn't :user_id's, this simply matches zero
-- rows rather than erroring.
--
-- Params: :id, :user_id

DELETE FROM afschrift_cat_regels WHERE ID = :id AND user_ID = :user_id;
