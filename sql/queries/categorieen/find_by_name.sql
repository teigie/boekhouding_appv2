-- Look up one of a user's own categories by name, case-insensitively.
-- Used by /review's "nieuwe categorie" flow to reuse an existing category
-- instead of creating a near-duplicate from a typo'd name that already
-- exists, and by /categories when adding a category or a suggestion chip.
-- Params: :user_id, :name

SELECT ID, Name FROM afschrift_categorien WHERE user_ID = :user_id AND Name = :name COLLATE NOCASE;
