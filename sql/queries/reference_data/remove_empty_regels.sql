-- Cleanup sweep: a rule with zero column-conditions left (after
-- remove_empty_regel_kolommen.sql removed its last one) matches nothing
-- (see match_custom_rules.sql's EXISTS guard) and has nothing left to
-- show on the profile page, so it's removed too rather than left as a
-- dangling empty rule card. Run right after remove_empty_regel_kolommen.sql,
-- same transaction.
--
-- Params: :user_id

DELETE FROM afschrift_cat_regels
WHERE user_ID = :user_id
  AND ID NOT IN (SELECT DISTINCT regel_ID FROM afschrift_cat_regel_kolommen);
