# Enrichment queries (not yet implemented)

This folder will hold the SQL that resolves accepted `temp_afschrift2`
rows (rows that already passed the upload-gate checks in `sql/upload/`)
into `temp_afschrift` rows with real foreign keys and a `processed`
status. Planned files:

- `resolve_rekening.sql` — match `temp_afschrift2.Rekening` (text) to
  `Rekening.name` → `Rekening_ID`. Rows with no match stay unresolved
  (`processed = 0`) until the user links/creates the account.
- `resolve_mutatiesoort.sql` — match `temp_afschrift2.Mutatiesoort` (text)
  via `mutatiesoort_mapping.Name` → `mutatiesoort_ID`.
- `match_category_keywords.sql` — scan `Naam`/`Mededeling` for
  `afschrift_cat_keywords.keyword` substrings. Exactly one match →
  `processed = 1`. Zero matches → `processed = 0` (needs a manual category).
  More than one match → `processed = 2` (ambiguous, needs manual pick).
- Date reformatting: `Datum` goes from `temp_afschrift2`'s raw
  `YYYYMMDD` to `temp_afschrift`'s `YYYY-MM-DD` here — see
  docs/ARCHITECTURE.md for why the DB stores ISO dates even though the UI
  displays European (`DD-MM-YYYY`) ones.

Enrichment must always drain an account's **entire** current
`temp_afschrift2` backlog in one atomic run, never a partial subset — the
upload-gate balance-chain check in `sql/upload/` relies on that invariant
to reconstruct a valid ordering across tables.

See docs/ARCHITECTURE.md for the full pipeline and the meaning of each
`processed` value.
