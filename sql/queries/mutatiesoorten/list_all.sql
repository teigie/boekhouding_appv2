-- Every known Mutatiesoort raw-text variant (see sql/seed_data.sql's
-- mutatiesoort_mapping) — i.e. the strings that can actually appear in an
-- uploaded bank export, and so the only values a categorization rule's
-- Mutatiesoort condition (LIKE-matched, see
-- sql/categorization/match_custom_rules.sql) can ever match against.
-- Deliberately not mutatiesoort.Name: that table's canonical names can
-- combine multiple raw variants (e.g. "iDEAL | Wero"), which never
-- literally appears in an upload and so would never match anything.

SELECT Name FROM mutatiesoort_mapping ORDER BY Name;
