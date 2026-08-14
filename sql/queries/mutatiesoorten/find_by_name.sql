-- Resolve a mutatiesoort's raw text (as it appears in an uploaded file) to
-- its mutatiesoort_ID, if it's a known mutatiesoort. mutatiesoort_mapping
-- is structural reference data (see sql/seed_data.sql) — every text a bank
-- export can produce is expected to already be in there.
-- Params: :name

SELECT mutatiesoort_ID FROM mutatiesoort_mapping WHERE Name = :name;
