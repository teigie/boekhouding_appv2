-- "Simple" categorization: category keyword matches found in Naam (the
-- counterparty/merchant name), for one account's pending temp_afschrift2
-- backlog, against the categorizing user's OWN keywords only. Returns one
-- row per (temp_afschrift2.ID, cat_ID) match — a row can match more than
-- one category if more than one keyword hits.
--
-- Standalone/reusable (e.g. to preview matches); categorize_batch.sql
-- embeds the same join itself rather than including this file, since
-- SQLite has no cross-file inclusion.
--
-- Params:
--   :rekening_text — raw account text as it appears in temp_afschrift2.Rekening
--   :user_id       — owning user of :rekening_text — scopes which
--                     keywords can match, since keywords are per-user

SELECT DISTINCT t.ID AS temp_id, k.cat_ID
FROM temp_afschrift2 t
JOIN afschrift_cat_keywords k
    ON t.Naam LIKE '%' || k.keyword || '%'
   AND k.user_ID = :user_id
WHERE t.Rekening = :rekening_text;
