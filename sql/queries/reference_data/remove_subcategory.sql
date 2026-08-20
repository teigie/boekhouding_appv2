-- Remove a subcategory the user owns. Any rule that assigned it has its
-- subcat_ID cascaded to NULL (ON DELETE SET NULL) — the rule itself and
-- its category assignment are unaffected. Afschrift_subcat_ID on
-- temp_afschrift/afschrift is NOT cascaded — a subcategory referenced by
-- actual ledger history must block deletion instead, so the caller MUST
-- check sql/queries/subcategorieen/count_usage_for_user.sql == 0 first
-- (this statement still fails safely on the FK if that check is ever
-- skipped).
-- Params: :subcat_id, :user_id

delete from afschrift_subcategorien where ID = :subcat_id and user_ID = :user_id;
