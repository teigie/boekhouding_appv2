-- Look up one subcategory by ID, but only if it belongs to the given
-- category AND user — used to validate a raw submitted subcat_id
-- actually belongs to the category it's being attached to (a rule's own
-- category, or a temp_afschrift row's resolved category), rather than
-- trusting a guessed/stale ID from another of the user's categories.
-- Mirrors sql/queries/subcategorieen/find_by_id_for_user.sql, narrowed to
-- one category.
-- Params: :id, :cat_id, :user_id

SELECT ID, Name FROM afschrift_subcategorien WHERE ID = :id AND cat_ID = :cat_id AND user_ID = :user_id;
