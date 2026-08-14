# Categorization queries

Resolves accepted `temp_afschrift2` rows (rows that already passed the
upload-gate checks in `sql/upload/`) into `temp_afschrift` rows with real
foreign keys and a `processed` status.

`Rekening_ID`/`Mutatiesoort_ID` resolution is independent of `processed` —
both are expected to always resolve (the account was already validated at
upload time; `mutatiesoort_mapping` is structural reference data — an
unmatched Mutatiesoort fails the `NOT NULL` constraint rather than being
treated as "unresolved"). See docs/ARCHITECTURE.md.

`processed` reflects only the category-match outcome, which happens in two
steps:

- **Simple categorization** — `Naam` (counterparty/merchant name) checked
  against `afschrift_cat_keywords` (short substrings, e.g. "Lidl" ->
  Levensmiddelen). Already has example data — see
  `sql/optional/example_keywords.sql`.
- **Difficult categorization** — `Mededeling` (free-text transaction
  description) checked against `afschrift_cat_mededeling_keywords`
  (longer phrases/sentences, not just single words) — no data yet, an
  empty table, since this is new.

Current combination strategy (**not final, expected to change**): both
fields are always checked for every row, and the categories matched from
each are unioned into one set per row before deciding `processed`:

- `0` — no category matched (neither field) — needs a manual category.
- `1` — exactly one category matched — eligible for migration.
- `2` — more than one category matched — ambiguous, needs a manual pick.

Files:

- `match_naam_keywords.sql` / `match_mededeling_keywords.sql` — one
  set-based query per field, per account, returning (temp_afschrift2.ID,
  cat_ID) pairs for every match. Standalone/reusable (e.g. a future
  "preview matches" view); `categorize_batch.sql` embeds the same joins
  itself rather than including these files, since SQLite has no
  cross-file inclusion — some duplication, same pattern already used
  between `sql/upload/check_balance_chain.sql` and `check_dedup.sql`.
- `categorize_batch.sql` — the actual pipeline step: combines both match
  sets, resolves `Mutatiesoort_ID` (`Rekening_ID` is passed in already
  resolved by the caller), computes `processed`, and inserts the result
  into `temp_afschrift` in one `INSERT ... SELECT`, preserving
  `temp_afschrift2`'s row order. Also reformats `Datum` from
  `temp_afschrift2`'s raw `YYYYMMDD` to `temp_afschrift`'s `YYYY-MM-DD` —
  see docs/ARCHITECTURE.md for why the DB stores ISO dates even though the
  UI displays European (`DD-MM-YYYY`) ones. Returns `processed` for every
  inserted row (`RETURNING`), so the caller can tally
  resolved/unresolved/ambiguous counts without a second query.
- `clear_temp_afschrift2.sql` — deletes the account's now-categorized
  backlog. Run immediately after `categorize_batch.sql`, in the same
  transaction.

Categorization must always drain an account's **entire** current
`temp_afschrift2` backlog in one atomic run, never a partial subset — the
upload-gate balance-chain check in `sql/upload/` relies on that invariant
to reconstruct a valid ordering across tables.

See docs/ARCHITECTURE.md for the full pipeline.
