-- Remove a category the user owns. Its keywords (afschrift_cat_keywords /
-- afschrift_cat_mededeling_keywords) cascade with it via cat_ID's ON
-- DELETE CASCADE. Afschrift_cat_ID on temp_afschrift/afschrift is NOT
-- cascaded — a category referenced by actual ledger history must block
-- deletion instead, so the caller MUST check
-- sql/queries/categorieen/count_usage_for_user.sql == 0 first (this
-- statement still fails safely on the FK if that check is ever skipped).
-- Params: :cat_id, :user_id

delete from afschrift_categorien where ID = :cat_id and user_ID = :user_id;
