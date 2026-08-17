-- "Difficult" categorization: category keyword/phrase matches found in
-- Mededeling (the free-text transaction description), for one account's
-- pending temp_afschrift2 backlog, against the categorizing user's OWN
-- keywords only. Same shape as match_naam_keywords.sql, against
-- afschrift_cat_mededeling_keywords instead.
--
-- Each keyword's naam_keyword is an OPTIONAL paired condition: when set,
-- Naam must ALSO contain it for the row to count as a match, not just
-- Mededeling (see sql/schema.sql's comment on the table for why). When
-- naam_keyword is NULL, Mededeling alone is enough, same as before.
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
JOIN afschrift_cat_mededeling_keywords k
    ON t.Mededeling LIKE '%' || k.keyword || '%'
   AND (k.naam_keyword IS NULL OR t.Naam LIKE '%' || k.naam_keyword || '%')
   AND k.user_ID = :user_id
WHERE t.Rekening = :rekening_text;
