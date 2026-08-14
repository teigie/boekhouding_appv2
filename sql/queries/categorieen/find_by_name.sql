-- Look up a category by name, case-insensitively. Used by the /review
-- page's "nieuwe categorie" flow to reuse an existing category instead of
-- creating a near-duplicate from a typo'd name that already exists.
-- Params: :name

SELECT ID, Name FROM afschrift_categorien WHERE Name = :name COLLATE NOCASE;
