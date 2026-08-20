-- Look up one of a user's own subcategories by name, case-insensitively —
-- reuses an existing subcategory instead of creating a near-duplicate
-- from a typo'd name that already exists. Used by the "nieuwe
-- subcategorie…" inline-create option on /categories' rule form and on
-- /review, mirroring sql/queries/categorieen/find_by_name.sql.
-- Params: :user_id, :name

SELECT ID, Name FROM afschrift_subcategorien WHERE user_ID = :user_id AND Name = :name COLLATE NOCASE;
