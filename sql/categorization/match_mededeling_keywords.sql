-- "Difficult" categorization: category keyword/phrase matches found in
-- Mededeling (the free-text transaction description), for one account's
-- pending temp_afschrift2 backlog. Same shape as match_naam_keywords.sql,
-- against afschrift_cat_mededeling_keywords instead.
--
-- Standalone/reusable (e.g. to preview matches); categorize_batch.sql
-- embeds the same join itself rather than including this file, since
-- SQLite has no cross-file inclusion.
--
-- Params:
--   :rekening_text — raw account text as it appears in temp_afschrift2.Rekening

SELECT DISTINCT t.ID AS temp_id, k.cat_ID
FROM temp_afschrift2 t
JOIN afschrift_cat_mededeling_keywords k
    ON t.Mededeling LIKE '%' || k.keyword || '%'
WHERE t.Rekening = :rekening_text;
