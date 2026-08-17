-- Cleanup sweep: a column-condition is only meaningful with at least one
-- keyword (see sql/schema.sql's comment on afschrift_cat_regel_kolommen —
-- "no value = no check" only holds if an empty group never lingers as a
-- row with zero keywords, which would otherwise be indistinguishable
-- from "not checked" everywhere except here). Run right after deleting a
-- keyword (remove_regel_keyword.sql), in the same transaction.
--
-- Scoped to :user_id purely so one request's cleanup can't scan/affect
-- another user's rows; harmless either way since the condition itself
-- (zero remaining keywords) can't be true for a row that still has any.
--
-- Params: :user_id

DELETE FROM afschrift_cat_regel_kolommen
WHERE user_ID = :user_id
  AND ID NOT IN (SELECT DISTINCT regel_kolom_ID FROM afschrift_cat_regel_keywords);
